/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Metadata validation API service

import { getConfig } from "./config";
import {
  ValidationJobResponse,
  ValidationStatusResponse,
  SchemaListResponse,
  SchemaInfo,
  ParsedSchemaData,
  SchemaOption,
  ValidationJobStatus,
  CombinedResults,
  SchemaAlignmentResults,
  SchemaAlignmentChangeDetail,
  SchemaAlignmentResultsSummary,
  ValidationResults,
  SchemaAlignmentChange,
  SchemaAlignmentChangeType,
  TransformationSummary,
} from "./types";
import { handleApiError } from "./error-handling";

// Note: API responses are already in camelCase format, no conversion needed

/**
 * Create a new validation job with file upload
 * Maps to POST /api/v1/metadata/validate
 */
export async function createValidationJob(
  file: File,
  coreSchemaId: string,
  programSchemaId: string,
  token?: string
): Promise<ValidationJobResponse> {
  try {
    const config = getConfig();

    // Validate required parameters
    if (!file) {
      return {
        success: false,
        error: "File is required for validation job creation",
      };
    }

    if (!coreSchemaId || !programSchemaId) {
      return {
        success: false,
        error: "Both core schema ID and program schema ID are required",
      };
    }

    // Create FormData for file upload with schema IDs
    const formData = new FormData();
    formData.append('file', file);
    formData.append('core_schema_id', coreSchemaId);
    formData.append('program_schema_id', programSchemaId);

    console.log('Creating validation job with FormData:', {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      coreSchemaId,
      programSchemaId
    });

    // Set up headers with authentication if token is provided
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    // Note: Don't set Content-Type for FormData, let browser set it with boundary

    console.log('Making POST request to:', `${config.API_URI}/api/v1/metadata/validate`);
    console.log('Request headers:', headers);

    const response = await fetch(`${config.API_URI}/api/v1/metadata/validate`, {
      method: "POST",
      headers,
      body: formData,
      credentials: 'include',
    });

    console.log('API response status:', response.status, response.statusText);

    // Handle HTTP errors
    if (!response.ok) {
      const errorMessage = await handleApiError(response);
      console.error('API error response:', {
        status: response.status,
        statusText: response.statusText,
        error: errorMessage
      });
      return {
        success: false,
        error: errorMessage,
      };
    }

    // Parse the response - API returns camelCase directly
    const data = await response.json();
    console.log('API response data:', data);

    // Validate response structure
    if (!data.jobId) {
      console.error("Invalid validation job response: missing jobId", data);
      return {
        success: false,
        error: "Invalid response from validation service: missing job ID",
      };
    }

    console.log('Validation job created successfully:', {
      jobId: data.jobId,
      coreSchemaId,
      programSchemaId
    });

    return {
      success: true,
      jobId: data.jobId,
    };
  } catch (error) {
    console.error("Error creating validation job:", error);

    // Provide more specific error messages based on error type
    let errorMessage = "Failed to create validation job. Please try again later.";

    if (error instanceof TypeError && error.message.includes('fetch')) {
      errorMessage = "Network error: Unable to connect to validation service.";
    } else if (error instanceof SyntaxError) {
      errorMessage = "Invalid response format from validation service.";
    }

    return {
      success: false,
      error: errorMessage,
    };
  }
}

/**
 * Update an existing validation job with a new file
 * Maps to POST /api/v1/metadata/validate/{metadata_id}
 */
export async function updateValidationJob(
  metadataId: string,
  file: File,
  token?: string
): Promise<ValidationJobResponse> {
  try {
    const config = getConfig();

    // Validate required parameters
    if (!metadataId) {
      return {
        success: false,
        error: "Metadata ID is required for job update",
      };
    }

    if (!file) {
      return {
        success: false,
        error: "File is required for validation job update",
      };
    }

    // Create FormData for file upload
    const formData = new FormData();
    formData.append('file', file);

    console.log('Updating validation job with FormData:', {
      metadataId,
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type
    });

    // Set up headers with authentication if token is provided
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    // Note: Don't set Content-Type for FormData, let browser set it with boundary

    console.log('Making POST request to:', `${config.API_URI}/api/v1/metadata/validate/${metadataId}`);
    console.log('Request headers:', headers);

    const response = await fetch(`${config.API_URI}/api/v1/metadata/validate/${metadataId}`, {
      method: "POST",
      headers,
      body: formData,
      credentials: 'include',
    });

    console.log('API response status:', response.status, response.statusText);

    // Handle HTTP errors
    if (!response.ok) {
      const errorMessage = await handleApiError(response);
      console.error('API error response:', {
        status: response.status,
        statusText: response.statusText,
        error: errorMessage
      });
      return {
        success: false,
        error: errorMessage,
      };
    }

    // Parse the response - API returns camelCase directly
    const data = await response.json();
    console.log('API response data:', data);

    // Validate response structure
    if (!data.jobId) {
      console.error("Invalid validation job update response: missing jobId", data);
      return {
        success: false,
        error: "Invalid response from validation service: missing job ID",
      };
    }

    console.log('Validation job updated successfully:', {
      jobId: data.jobId,
      metadataId
    });

    return {
      success: true,
      jobId: data.jobId,
    };
  } catch (error) {
    console.error("Error updating validation job:", error);

    // Provide more specific error messages based on error type
    let errorMessage = "Failed to update validation job. Please try again later.";

    if (error instanceof TypeError && error.message.includes('fetch')) {
      errorMessage = "Network error: Unable to connect to validation service.";
    } else if (error instanceof SyntaxError) {
      errorMessage = "Invalid response format from validation service.";
    }

    return {
      success: false,
      error: errorMessage,
    };
  }
}

/**
 * Get validation job status and results with schema alignment support
 * Maps to GET /api/v1/metadata/validate/{metadata_id}
 */
export async function getValidationStatus(
  metadataId: string,
  token?: string
): Promise<ValidationStatusResponse> {
  try {
    const config = getConfig();

    // Validate required parameters
    if (!metadataId) {
      return {
        success: false,
        error: "Metadata ID is required for status retrieval",
      };
    }

    // Set up headers with authentication if token is provided
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    console.log('Getting validation status for job:', metadataId);
    console.log('Making GET request to:', `${config.API_URI}/api/v1/metadata/validate/${metadataId}`);

    const response = await fetch(`${config.API_URI}/api/v1/metadata/validate/${metadataId}`, {
      method: "GET",
      headers,
      credentials: 'include',
    });

    console.log('Status API response:', response.status, response.statusText);

    // Handle HTTP errors
    if (!response.ok) {
      const errorMessage = await handleApiError(response);
      console.error('Status API error:', {
        status: response.status,
        statusText: response.statusText,
        error: errorMessage
      });
      return {
        success: false,
        error: errorMessage,
      };
    }

    // Parse the response - API returns camelCase directly
    const data = await response.json();
    console.log('Status API response data:', data);

    // Validate response structure
    if (!data.jobId || !data.userId || !data.status) {
      console.error("Invalid validation status response: missing required fields", {
        hasJobId: !!data.jobId,
        hasUserId: !!data.userId,
        hasStatus: !!data.status,
        data
      });
      return {
        success: false,
        error: "Invalid response from validation service: missing required fields",
      };
    }

    // Process and validate CombinedResults structure if present
    let processedResults = null;
    if (data.latestResults) {
      try {
        processedResults = processCombinedResults(data.latestResults);
        console.log('Processed combined results:', {
          hasValidationResults: !!processedResults.validationResults,
          hasSchemaAlignmentResults: !!processedResults.schemaAlignmentResults,
          hasChangeTracking: !!processedResults.changeTracking,
          validationErrorCount: processedResults.validationResults?.validationResults?.length || 0,
          schemaAlignmentChangesCount: processedResults.schemaAlignmentResults?.schemaAlignmentResults?.length || 0,
          changeTrackingCount: processedResults.changeTracking?.changes?.length || 0
        });
      } catch (error) {
        console.warn('Error processing combined results, using raw data:', error);
        processedResults = data.latestResults;
      }
    }

    console.log('Validation status retrieved successfully:', {
      jobId: data.jobId,
      status: data.status,
      hasResults: !!processedResults,
      hasValidationResults: !!processedResults?.validationResults,
      hasSchemaAlignmentResults: !!processedResults?.schemaAlignmentResults,
      hasChangeTracking: !!processedResults?.changeTracking,
      validationErrorCount: processedResults?.validationResults?.validationResults?.length || 0,
      schemaAlignmentChangesCount: processedResults?.schemaAlignmentResults?.schemaAlignmentResults?.length || 0,
      changeTrackingCount: processedResults?.changeTracking?.changes?.length || 0
    });

    return {
      success: true,
      jobId: data.jobId,
      userId: data.userId,
      coreSchemaId: data.coreSchemaId,
      programSchemaId: data.programSchemaId,
      status: data.status as ValidationJobStatus,
      createdAt: data.createdAt,
      completedAt: data.completedAt,
      currentVersion: data.currentVersion,
      latestResults: processedResults,
    };
  } catch (error) {
    console.error("Error getting validation status:", error);

    // Provide more specific error messages based on error type
    let errorMessage = "Failed to get validation status. Please try again later.";

    if (error instanceof TypeError && error.message.includes('fetch')) {
      errorMessage = "Network error: Unable to connect to validation service.";
    } else if (error instanceof SyntaxError) {
      errorMessage = "Invalid response format from validation service.";
    }

    return {
      success: false,
      error: errorMessage,
    };
  }
}

/**
 * Get available schemas for validation
 * Maps to GET /api/v1/metadata/schema
 */
export async function getAvailableSchemas(
  token?: string
): Promise<SchemaListResponse> {
  try {
    const config = getConfig();

    // Set up headers with authentication if token is provided
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${config.API_URI}/api/v1/metadata/schema`, {
      method: "GET",
      headers,
    });

    // Handle HTTP errors
    if (!response.ok) {
      const errorMessage = await handleApiError(response);
      return {
        success: false,
        error: errorMessage,
      };
    }

    // Parse the response - API returns List[SchemaInfo] directly (already camelCase)
    const schemas = await response.json();

    // Validate response structure
    if (!Array.isArray(schemas)) {
      console.error("Invalid schema response format: expected array, got:", typeof schemas);
      return {
        success: false,
        error: "Invalid response format from schema API",
      };
    }

    // Validate each schema has required fields
    for (const schema of schemas) {
      if (!schema.coreSchemaId || !schema.name || !Array.isArray(schema.programSchemas)) {
        console.error("Invalid schema structure:", schema);
        return {
          success: false,
          error: "Invalid schema data structure from API",
        };
      }
    }

    return {
      success: true,
      schemas: schemas as SchemaInfo[],
    };
  } catch (error) {
    console.error("Error getting available schemas:", error);

    // Provide more specific error messages based on error type
    let errorMessage = "Failed to get available schemas. Please try again later.";

    if (error instanceof TypeError && error.message.includes('fetch')) {
      errorMessage = "Network error: Unable to connect to schema service.";
    } else if (error instanceof SyntaxError) {
      errorMessage = "Invalid response format from schema service.";
    }

    return {
      success: false,
      error: errorMessage,
    };
  }
}

/**
 * Submit metadata for validation with CSV data
 * This is a convenience method that creates a CSV file from data and submits it
 */
export async function submitMetadataValidation(
  csvData: string[][],
  coreSchemaId: string,
  programSchemaId: string,
  token?: string
): Promise<ValidationJobResponse> {
  try {
    // Convert CSV data to CSV string
    const csvContent = csvData.map(row =>
      row.map(cell => {
        // Escape cells that contain commas, quotes, or newlines
        if (cell.includes(',') || cell.includes('"') || cell.includes('\n')) {
          return `"${cell.replace(/"/g, '""')}"`;
        }
        return cell;
      }).join(',')
    ).join('\n');

    // Create a File object from the CSV content
    const csvFile = new File([csvContent], 'metadata.csv', { type: 'text/csv' });

    // Use the existing createValidationJob method
    return await createValidationJob(csvFile, coreSchemaId, programSchemaId, token);
  } catch (error) {
    console.error("Error submitting metadata validation:", error);
    return {
      success: false,
      error: "Failed to submit metadata for validation. Please try again later.",
    };
  }
}

/**
 * Check if an error is a network-related error that should be retried
 */
function isRetryableError(error: unknown): boolean {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true; // Network error
  }

  if (error instanceof Error) {
    const message = error.message.toLowerCase();
    return message.includes('network') ||
           message.includes('timeout') ||
           message.includes('connection') ||
           message.includes('fetch');
  }

  return false;
}

/**
 * Retry wrapper for API calls with exponential backoff
 */
async function withRetry<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      console.log(`[Retry ${attempt}/${maxRetries}] Attempting operation...`);
      const result = await operation();
      if (attempt > 0) {
        console.log(`[Retry ${attempt}/${maxRetries}] Operation succeeded after retry`);
      }
      return result;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      console.log(`[Retry ${attempt}/${maxRetries}] Operation failed:`, lastError.message);

      // Don't retry on the last attempt
      if (attempt === maxRetries) {
        console.log(`[Retry ${attempt}/${maxRetries}] Max retries exceeded, giving up`);
        break;
      }

      // Don't retry on client errors (4xx), only on server errors (5xx) and network errors
      if (error instanceof Response && error.status >= 400 && error.status < 500) {
        console.log(`[Retry ${attempt}/${maxRetries}] Client error (${error.status}), not retrying`);
        break;
      }

      // Only retry on network errors and server errors
      if (!isRetryableError(error) && !(error instanceof Response && error.status >= 500)) {
        console.log(`[Retry ${attempt}/${maxRetries}] Non-retryable error, not retrying`);
        break;
      }

      // Calculate delay with exponential backoff
      const delay = baseDelay * Math.pow(2, attempt);
      console.log(`[Retry ${attempt}/${maxRetries}] Retrying in ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError!;
}

/**
 * Create a new validation job with retry logic
 */
export async function createValidationJobWithRetry(
  file: File,
  coreSchemaId: string,
  programSchemaId: string,
  token?: string
): Promise<ValidationJobResponse> {
  return withRetry(
    () => createValidationJob(file, coreSchemaId, programSchemaId, token),
    3,
    1000
  );
}

/**
 * Update validation job with retry logic
 */
export async function updateValidationJobWithRetry(
  metadataId: string,
  file: File,
  token?: string
): Promise<ValidationJobResponse> {
  return withRetry(
    () => updateValidationJob(metadataId, file, token),
    3,
    1000
  );
}

/**
 * Get validation status with retry logic
 */
export async function getValidationStatusWithRetry(
  metadataId: string,
  token?: string
): Promise<ValidationStatusResponse> {
  return withRetry(
    () => getValidationStatus(metadataId, token),
    3,
    1000
  );
}

/**
 * Submit metadata validation with retry logic
 */
export async function submitMetadataValidationWithRetry(
  csvData: string[][],
  coreSchemaId: string,
  programSchemaId: string,
  token?: string
): Promise<ValidationJobResponse> {
  return withRetry(
    () => submitMetadataValidation(csvData, coreSchemaId, programSchemaId, token),
    3,
    1000
  );
}

/**
 * Parse schema API response into UI-friendly format
 * Extracts core schemas and program schemas for dropdown selection
 */
export function parseSchemaResponse(schemas: SchemaInfo[]): ParsedSchemaData {
  try {
    // Extract unique core schemas
    const coreSchemaMap = new Map<string, SchemaOption>();
    const allProgramSchemas: SchemaOption[] = [];

    schemas.forEach(schema => {
      // Add core schema if not already present
      if (!coreSchemaMap.has(schema.coreSchemaId)) {
        coreSchemaMap.set(schema.coreSchemaId, {
          id: schema.coreSchemaId,
          name: schema.name,
          description: `Core schema: ${schema.name}`,
        });
      }

      // Add all program schemas from this core schema
      schema.programSchemas.forEach(program => {
        allProgramSchemas.push({
          id: program.programSchemaId,
          name: program.programName,
          description: `Program: ${program.programName}`,
        });
      });
    });

    return {
      coreSchemas: Array.from(coreSchemaMap.values()),
      programSchemas: allProgramSchemas,
      rawSchemas: schemas,
    };
  } catch (error) {
    console.error("Error parsing schema response:", error);
    return {
      coreSchemas: [],
      programSchemas: [],
      rawSchemas: schemas,
    };
  }
}

/**
 * Get available schemas with parsed data for UI consumption
 * Combines schema fetching with parsing for convenience
 */
export async function getAvailableSchemasForUI(
  token?: string
): Promise<{
  success: boolean;
  data?: ParsedSchemaData;
  error?: string;
}> {
  try {
    const response = await getAvailableSchemas(token);

    if (!response.success) {
      return {
        success: false,
        error: response.error,
      };
    }

    if (!response.schemas || response.schemas.length === 0) {
      return {
        success: false,
        error: "No schemas available for validation",
      };
    }

    const parsedData = parseSchemaResponse(response.schemas);

    if (parsedData.coreSchemas.length === 0) {
      return {
        success: false,
        error: "No valid core schemas found",
      };
    }

    if (parsedData.programSchemas.length === 0) {
      return {
        success: false,
        error: "No valid program schemas found",
      };
    }

    return {
      success: true,
      data: parsedData,
    };
  } catch (error) {
    console.error("Error getting schemas for UI:", error);
    return {
      success: false,
      error: "Failed to process schema data for UI",
    };
  }
}

/**
 * Validate schema selection parameters
 * Ensures both core and program schema IDs are provided and valid
 */
export function validateSchemaSelection(
  coreSchemaId: string,
  programSchemaId: string,
  availableSchemas?: ParsedSchemaData
): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Check required fields
  if (!coreSchemaId || coreSchemaId.trim() === '') {
    errors.push("Core schema ID is required");
  }

  if (!programSchemaId || programSchemaId.trim() === '') {
    errors.push("Program schema ID is required");
  }

  // Validate against available schemas if provided
  if (availableSchemas) {
    const coreSchemaExists = availableSchemas.coreSchemas.some(
      schema => schema.id === coreSchemaId
    );
    if (!coreSchemaExists && coreSchemaId) {
      errors.push(`Core schema ID "${coreSchemaId}" is not available`);
    }

    const programSchemaExists = availableSchemas.programSchemas.some(
      schema => schema.id === programSchemaId
    );
    if (!programSchemaExists && programSchemaId) {
      errors.push(`Program schema ID "${programSchemaId}" is not available`);
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Poll validation status until completion with configurable intervals
 * Maps to repeated GET /api/v1/metadata/validate/{metadata_id} calls
 */
export async function pollValidationStatus(
  metadataId: string,
  onStatusUpdate?: (status: ValidationJobStatus, response: ValidationStatusResponse) => void,
  token?: string,
  options?: {
    pollInterval?: number;
    maxAttempts?: number;
    timeoutMs?: number;
  }
): Promise<ValidationStatusResponse> {
  const POLL_INTERVAL = options?.pollInterval || 2000; // 2 seconds default
  const MAX_POLL_ATTEMPTS = options?.maxAttempts || 150; // 5 minutes max (150 * 2s = 300s)
  const TIMEOUT_MS = options?.timeoutMs || 300000; // 5 minutes timeout

  let attempts = 0;
  const startTime = Date.now();

  console.log(`Starting validation polling for job: ${metadataId}`, {
    pollInterval: POLL_INTERVAL,
    maxAttempts: MAX_POLL_ATTEMPTS,
    timeoutMs: TIMEOUT_MS
  });

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        attempts++;
        const elapsedTime = Date.now() - startTime;

        console.log(`[Poll ${attempts}/${MAX_POLL_ATTEMPTS}] Checking validation status for job: ${metadataId} (elapsed: ${elapsedTime}ms)`);

        // Check timeout
        if (elapsedTime > TIMEOUT_MS) {
          const timeoutError = new Error(`Polling timeout: validation took too long to complete (${TIMEOUT_MS}ms)`);
          console.error('Polling timeout exceeded:', timeoutError);
          reject(timeoutError);
          return;
        }

        // Check max attempts
        if (attempts > MAX_POLL_ATTEMPTS) {
          const attemptsError = new Error(`Polling timeout: exceeded maximum attempts (${MAX_POLL_ATTEMPTS})`);
          console.error('Max polling attempts exceeded:', attemptsError);
          reject(attemptsError);
          return;
        }

        // Make API call to get validation status
        const response = await getValidationStatus(metadataId, token);

        console.log(`[Poll ${attempts}] API response:`, {
          success: response.success,
          status: response.status,
          jobId: response.jobId,
          hasResults: !!response.latestResults,
          hasValidationResults: !!response.latestResults?.validationResults,
          hasSchemaAlignmentResults: !!response.latestResults?.schemaAlignmentResults,
          hasChangeTracking: !!response.latestResults?.changeTracking,
          error: response.error
        });

        if (!response.success) {
          const apiError = new Error(response.error || 'Failed to get validation status');
          console.error('API error during polling:', apiError);
          reject(apiError);
          return;
        }

        const status = response.status;

        if (!status) {
          const statusError = new Error('Invalid response: missing status field');
          console.error('Invalid API response:', statusError, response);
          reject(statusError);
          return;
        }

        console.log(`[Poll ${attempts}] Current validation status: ${status}`);

        // Notify caller of status update
        if (onStatusUpdate) {
          try {
            onStatusUpdate(status, response);
          } catch (callbackError) {
            console.warn('Error in status update callback:', callbackError);
            // Don't fail polling due to callback errors
          }
        }

        // Normalize status to handle both string and enum values
        const normalizedStatus = status.toString().toUpperCase();

        // Check if job is complete (terminal states)
        if (normalizedStatus === 'COMPLETED' || normalizedStatus === 'COMPLETED_WITH_ERRORS' || normalizedStatus === 'FAILED') {
          console.log(`[Poll ${attempts}] Validation ${normalizedStatus.toLowerCase()}. Stopping polling.`);
          console.log('Final validation response:', {
            jobId: response.jobId,
            status: response.status,
            hasResults: !!response.latestResults,
            hasValidationResults: !!response.latestResults?.validationResults,
            hasSchemaAlignmentResults: !!response.latestResults?.schemaAlignmentResults,
            hasChangeTracking: !!response.latestResults?.changeTracking,
            validationErrorCount: response.latestResults?.validationResults?.validationResults?.length || 0,
            schemaAlignmentChangesCount: response.latestResults?.schemaAlignmentResults?.schemaAlignmentResults?.length || 0,
            changeTrackingCount: response.latestResults?.changeTracking?.changes?.length || 0
          });
          resolve(response);
          return;
        }

        // Continue polling for pending/processing status (non-terminal states)
        if (normalizedStatus === 'PENDING' || normalizedStatus === 'PROCESSING') {
          console.log(`[Poll ${attempts}] Status is ${normalizedStatus}, continuing to poll in ${POLL_INTERVAL}ms...`);
          setTimeout(poll, POLL_INTERVAL);
          return;
        }

        // Unknown status - treat as error
        const unknownStatusError = new Error(`Unknown validation status: ${status} (normalized: ${normalizedStatus})`);
        console.error('Unknown status received:', unknownStatusError, response);
        reject(unknownStatusError);

      } catch (error) {
        console.error(`[Poll ${attempts}] Error during polling:`, error);

        // For network errors, retry a few times before giving up
        if (error instanceof TypeError && error.message.includes('fetch') && attempts <= 3) {
          console.log(`[Poll ${attempts}] Network error, retrying in ${POLL_INTERVAL}ms...`);
          setTimeout(poll, POLL_INTERVAL);
          return;
        }

        // For other errors or after max network retries, fail
        reject(error);
      }
    };

    // Start polling immediately
    poll();
  });
}

/**
 * Test API connectivity and endpoints
 * This function can be used to verify that the API is reachable and working
 */
export async function testApiConnectivity(token?: string): Promise<{
  success: boolean;
  results: {
    schemaEndpoint: boolean;
    schemaError?: string;
  };
  error?: string;
}> {
  const results = {
    schemaEndpoint: false,
    schemaError: undefined as string | undefined,
  };

  try {
    console.log('Testing API connectivity...');

    // Test schema endpoint
    try {
      const schemaResponse = await getAvailableSchemas(token);
      results.schemaEndpoint = schemaResponse.success;
      if (!schemaResponse.success) {
        results.schemaError = schemaResponse.error;
      }
      console.log('Schema endpoint test:', results.schemaEndpoint ? 'PASS' : 'FAIL', results.schemaError);
    } catch (error) {
      results.schemaEndpoint = false;
      results.schemaError = error instanceof Error ? error.message : 'Unknown error';
      console.log('Schema endpoint test: FAIL', results.schemaError);
    }

    const allTestsPassed = results.schemaEndpoint;

    console.log('API connectivity test results:', {
      overall: allTestsPassed ? 'PASS' : 'FAIL',
      results
    });

    return {
      success: allTestsPassed,
      results,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error during API testing';
    console.error('API connectivity test failed:', errorMessage);

    return {
      success: false,
      results,
      error: errorMessage,
    };
  }
}

/**
 * Validate that all required API methods are properly configured
 * This is a development/debugging helper function
 */
export function validateApiConfiguration(): {
  isValid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];

  try {
    const config = getConfig();

    // Check if API_URI is configured
    if (!config.API_URI) {
      errors.push('API_URI is not configured');
    } else if (!config.API_URI.startsWith('http')) {
      errors.push('API_URI must start with http:// or https://');
    }

    // Check if required functions exist. Referenced directly rather than looked
    // up by name so the check is statically verifiable and needs no eval().
    const requiredFunctions: Record<string, unknown> = {
      createValidationJob,
      updateValidationJob,
      getValidationStatus,
      pollValidationStatus,
      getAvailableSchemas
    };

    for (const [funcName, func] of Object.entries(requiredFunctions)) {
      if (typeof func !== 'function') {
        errors.push(`Required function ${funcName} is not available`);
      }
    }

    // Warnings for optional configurations
    if (config.API_URI && config.API_URI.includes('localhost')) {
      warnings.push('Using localhost API endpoint - ensure backend is running locally');
    }

  } catch (error) {
    errors.push(`Configuration validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }

  const isValid = errors.length === 0;

  console.log('API configuration validation:', {
    isValid,
    errors,
    warnings
  });

  return {
    isValid,
    errors,
    warnings
  };
}

// Schema Alignment Helper Functions

/**
 * Process CombinedResults from API response to ensure proper structure
 * Validates and normalizes the combined validation and schema alignment results
 * Handles both new CombinedResults format and legacy direct validation results format
 */
export function processCombinedResults(rawResults: any): CombinedResults {
  try {
    if (!rawResults || typeof rawResults !== 'object') {
      console.warn('Invalid combined results: not an object', rawResults);
      return {
        validationResults: null,
        schemaAlignmentResults: null
      };
    }

    const processed: CombinedResults = {
      validationResults: null,
      schemaAlignmentResults: null,
      changeTracking: null
    };

    // Check if this is the new CombinedResults format
    if (rawResults.validationResults || rawResults.schemaAlignmentResults || rawResults.changeTracking) {
      // New format: CombinedResults with separate validationResults, schemaAlignmentResults, and changeTracking
      if (rawResults.validationResults) {
        try {
          processed.validationResults = processValidationResults(rawResults.validationResults);
        } catch (error) {
          console.warn('Error processing validation results:', error);
          processed.validationResults = null;
        }
      }

      if (rawResults.schemaAlignmentResults) {
        try {
          processed.schemaAlignmentResults = processSchemaAlignmentResults(rawResults.schemaAlignmentResults);
        } catch (error) {
          console.warn('Error processing schema alignment results:', error);
          processed.schemaAlignmentResults = null;
        }
      }

      if (rawResults.changeTracking) {
        try {
          processed.changeTracking = processChangeTrackingResults(rawResults.changeTracking);
        } catch (error) {
          console.warn('Error processing change tracking results:', error);
          processed.changeTracking = null;
        }
      }
    } else if (rawResults.validation_results || rawResults.validationResults || rawResults.summary) {
      // Legacy format: direct validation results (for backward compatibility)
      try {
        processed.validationResults = processValidationResults(rawResults);
      } catch (error) {
        console.warn('Error processing legacy validation results:', error);
        processed.validationResults = null;
      }
    }

    return processed;
  } catch (error) {
    console.error('Error processing combined results:', error);
    return {
      validationResults: null,
      schemaAlignmentResults: null,
      changeTracking: null
    };
  }
}

/**
 * Process and validate ValidationResults structure
 * Handles both camelCase and snake_case formats from API
 */
function processValidationResults(rawValidationResults: any): ValidationResults | null {
  if (!rawValidationResults || typeof rawValidationResults !== 'object') {
    return null;
  }

  // Handle both camelCase and snake_case formats
  const validationResults = Array.isArray(rawValidationResults.validationResults)
    ? rawValidationResults.validationResults
    : Array.isArray(rawValidationResults.validation_results)
    ? rawValidationResults.validation_results
    : [];

  // Process summary or create default, handling both formats
  let summary = rawValidationResults.summary;
  if (!summary && rawValidationResults.summary) {
    summary = rawValidationResults.summary;
  }

  // Convert snake_case summary to camelCase if needed
  if (summary && (summary.total_rows !== undefined || summary.total_errors !== undefined)) {
    summary = {
      totalRows: summary.total_rows || 0,
      totalErrors: summary.total_errors || validationResults.length,
      errorTypes: summary.error_types || {}
    };
  } else if (!summary) {
    summary = {
      totalRows: 0,
      totalErrors: validationResults.length,
      errorTypes: {}
    };
  }

  // Convert validation results from snake_case to camelCase if needed
  const processedValidationResults = validationResults.map((result: any) => {
    if (result.current_value !== undefined) {
      // Convert from snake_case
      return {
        row: result.row,
        column: result.column,
        currentValue: result.current_value,
        validOptions: result.valid_options,
        recommendedValue: result.recommended_value,
        errorType: result.error_type
      };
    }
    // Already in camelCase
    return result;
  });

  return {
    validationResults: processedValidationResults,
    summary
  };
}

/**
 * Process and validate SchemaAlignmentResults structure (new format)
 */
function processSchemaAlignmentResults(rawSchemaResults: any): SchemaAlignmentResults | null {
  if (!rawSchemaResults || typeof rawSchemaResults !== 'object') {
    return null;
  }

  try {
    // Process schema alignment results array
    const schemaAlignmentResults: SchemaAlignmentChangeDetail[] = [];
    if (Array.isArray(rawSchemaResults.schemaAlignmentResults)) {
      for (const change of rawSchemaResults.schemaAlignmentResults) {
        if (change && typeof change === 'object' && typeof change.changeType === 'string') {
          const processedChange: SchemaAlignmentChangeDetail = {
            changeType: change.changeType
          };

          if (typeof change.originalColumn === 'string') {
            processedChange.originalColumn = change.originalColumn;
          }

          if (typeof change.newColumn === 'string') {
            processedChange.newColumn = change.newColumn;
          }

          if (typeof change.reason === 'string') {
            processedChange.reason = change.reason;
          }

          if (typeof change.rowCountAffected === 'number') {
            processedChange.rowCountAffected = change.rowCountAffected;
          }

          schemaAlignmentResults.push(processedChange);
        }
      }
    }

    // Process summary
    if (!rawSchemaResults.summary || typeof rawSchemaResults.summary !== 'object') {
      return null;
    }

    const summary = rawSchemaResults.summary;
    const processedSummary: SchemaAlignmentResultsSummary = {
      jobId: summary.jobId || '',
      version: summary.version || 1,
      timestamp: summary.timestamp || new Date().toISOString(),
      originalDataCsv: summary.originalDataCsv || '',
      alignedDataCsv: summary.alignedDataCsv || '',
      totalChanges: summary.totalChanges || 0,
      columnsRenamed: summary.columnsRenamed || 0,
      columnsAdded: summary.columnsAdded || 0,
      columnsRemoved: summary.columnsRemoved || 0,
      rowsOriginal: summary.rowsOriginal || 0,
      rowsAligned: summary.rowsAligned || 0
    };

    return {
      schemaAlignmentResults,
      summary: processedSummary
    };
  } catch (error) {
    console.error('Error processing schema alignment results:', error);
    return null;
  }
}

/**
 * Process and validate ChangeTrackingResults structure
 * Handles both camelCase and snake_case formats from API
 */
function processChangeTrackingResults(rawChangeTracking: any): import('./types').ChangeTrackingResults | null {
  if (!rawChangeTracking || typeof rawChangeTracking !== 'object') {
    return null;
  }

  try {
    // Process changes array
    const changes = Array.isArray(rawChangeTracking.changes) ? rawChangeTracking.changes : [];

    // Process summary
    const summary = rawChangeTracking.summary || {
      totalChanges: changes.length,
      adds: 0,
      removes: 0,
      renames: 0,
      systemChanges: 0,
      userChanges: 0
    };

    // Process comparison metadata
    const comparisonMetadata = rawChangeTracking.comparisonMetadata || rawChangeTracking.comparison_metadata || {};

    return {
      changes,
      summary,
      comparisonMetadata
    };
  } catch (error) {
    console.error('Error processing change tracking results:', error);
    return null;
  }
}



/**
 * Validate and sanitize column mappings from API response
 */
function validateColumnMappings(rawMappings: any): Record<string, string> {
  const validated: Record<string, string> = {};

  if (!rawMappings || typeof rawMappings !== 'object') {
    return validated;
  }

  for (const [key, value] of Object.entries(rawMappings)) {
    if (typeof key === 'string' && typeof value === 'string') {
      validated[key] = value;
    } else {
      console.warn('Invalid column mapping entry:', { key, value });
    }
  }

  return validated;
}

/**
 * Extract schema alignment results from validation status response
 * Returns null if no schema alignment results are present
 */
export function extractSchemaAlignmentResults(
  statusResponse: ValidationStatusResponse
): SchemaAlignmentResults | null {
  try {
    if (!statusResponse.success || !statusResponse.latestResults) {
      return null;
    }

    return statusResponse.latestResults.schemaAlignmentResults || null;
  } catch (error) {
    console.error('Error extracting schema alignment results:', error);
    return null;
  }
}



/**
 * Check if validation status response contains schema alignment data
 */
export function hasSchemaAlignmentResults(statusResponse: ValidationStatusResponse): boolean {
  const schemaResults = extractSchemaAlignmentResults(statusResponse);
  return !!(schemaResults && (
    schemaResults.schemaAlignmentResults.length > 0 ||
    schemaResults.summary.originalDataCsv ||
    schemaResults.summary.alignedDataCsv
  ));
}

/**
 * Process column mappings into UI-friendly schema alignment changes
 * Converts API columnMappings into structured change objects for display
 */
export function processColumnMappingsToChanges(
  columnMappings: Record<string, string>
): SchemaAlignmentChange[] {
  const changes: SchemaAlignmentChange[] = [];

  if (!columnMappings || typeof columnMappings !== 'object') {
    return changes;
  }

  let changeIndex = 0;

  for (const [originalColumn, alignedColumn] of Object.entries(columnMappings)) {
    if (originalColumn !== alignedColumn) {
      changes.push({
        id: `schema-change-${changeIndex++}`,
        type: SchemaAlignmentChangeType.COLUMN_RENAMED,
        originalColumn,
        alignedColumn,
        expectedSchemaColumn: alignedColumn,
        description: `Column "${originalColumn}" renamed to "${alignedColumn}"`,
        reason: `Required by schema specification to match expected column name`,
        canRevert: true,
        isAccepted: false
      });
    }
  }

  return changes;
}

/**
 * Apply schema alignment transformations to original data
 * Uses column mappings to transform data structure
 */
export function applySchemaAlignmentToData(
  originalData: string[][],
  columnMappings: Record<string, string>
): string[][] {
  try {
    if (!originalData || originalData.length === 0) {
      return [];
    }

    if (!columnMappings || Object.keys(columnMappings).length === 0) {
      return originalData;
    }

    const transformedData: string[][] = [];
    const headerRow = originalData[0];

    if (!headerRow) {
      return originalData;
    }

    // Create new header row with aligned column names
    const alignedHeader = headerRow.map(originalColumnName =>
      columnMappings[originalColumnName] || originalColumnName
    );
    transformedData.push(alignedHeader);

    // Copy data rows unchanged (only headers are transformed)
    for (let i = 1; i < originalData.length; i++) {
      transformedData.push([...originalData[i]]);
    }

    return transformedData;
  } catch (error) {
    console.error('Error applying schema alignment to data:', error);
    return originalData;
  }
}

/**
 * Generate transformation summary from schema alignment data
 */
export function generateSchemaAlignmentSummary(
  originalData: string[][],
  alignedData: string[][],
  columnMappings: Record<string, string>
): TransformationSummary {
  try {
    const summary: TransformationSummary = {
      columnsRenamed: 0,
      columnsAdded: 0,
      columnsRemoved: 0,
      rowsOriginal: originalData.length,
      rowsAligned: alignedData.length,
      columnMappings: { ...columnMappings },
      addedColumns: [],
      removedColumns: []
    };

    if (!columnMappings) {
      return summary;
    }

    // Count renamed columns
    for (const [original, aligned] of Object.entries(columnMappings)) {
      if (original !== aligned) {
        summary.columnsRenamed = (summary.columnsRenamed || 0) + 1;
      }
    }

    // Detect added/removed columns by comparing headers
    if (originalData.length > 0 && alignedData.length > 0) {
      const originalHeaders = new Set(originalData[0]);
      const alignedHeaders = new Set(alignedData[0]);

      // Find added columns (in aligned but not in original)
      for (const alignedHeader of alignedHeaders) {
        if (!originalHeaders.has(alignedHeader)) {
          summary.addedColumns = summary.addedColumns || [];
          summary.addedColumns.push(alignedHeader);
          summary.columnsAdded = (summary.columnsAdded || 0) + 1;
        }
      }

      // Find removed columns (in original but not in aligned)
      for (const originalHeader of originalHeaders) {
        if (!alignedHeaders.has(originalHeader)) {
          summary.removedColumns = summary.removedColumns || [];
          summary.removedColumns.push(originalHeader);
          summary.columnsRemoved = (summary.columnsRemoved || 0) + 1;
        }
      }
    }

    return summary;
  } catch (error) {
    console.error('Error generating schema alignment summary:', error);
    return {
      columnsRenamed: 0,
      columnsAdded: 0,
      columnsRemoved: 0,
      rowsOriginal: originalData.length,
      rowsAligned: alignedData.length,
      columnMappings: columnMappings || {},
      addedColumns: [],
      removedColumns: []
    };
  }
}

/**
 * Parse CSV string into 2D array with error handling
 */
export function parseSchemaAlignmentCsv(csvString: string): string[][] {
  try {
    if (!csvString || typeof csvString !== 'string') {
      return [];
    }

    const lines = csvString.split('\n');
    const result: string[][] = [];

    for (const line of lines) {
      if (line.trim() === '') continue;

      const row: string[] = [];
      let current = '';
      let inQuotes = false;

      for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          row.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }

      row.push(current.trim());
      result.push(row);
    }

    return result;
  } catch (error) {
    console.error('Error parsing schema alignment CSV:', error);
    return [];
  }
}

/**
 * Validate schema alignment data integrity
 */
export function validateSchemaAlignmentData(
  schemaAlignmentResults: SchemaAlignmentResults
): {
  isValid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];

  try {
    if (!schemaAlignmentResults) {
      errors.push('Schema alignment results are missing');
      return { isValid: false, errors, warnings };
    }

    // Validate summary structure
    if (!schemaAlignmentResults.summary) {
      errors.push('Schema alignment results summary is missing');
      return { isValid: false, errors, warnings };
    }

    // Validate CSV data strings in summary
    if (schemaAlignmentResults.summary.originalDataCsv) {
      const originalData = parseSchemaAlignmentCsv(schemaAlignmentResults.summary.originalDataCsv);
      if (originalData.length === 0) {
        warnings.push('Original data CSV appears to be empty');
      }
    } else {
      warnings.push('Original data CSV is missing');
    }

    if (schemaAlignmentResults.summary.alignedDataCsv) {
      const alignedData = parseSchemaAlignmentCsv(schemaAlignmentResults.summary.alignedDataCsv);
      if (alignedData.length === 0) {
        warnings.push('Aligned data CSV appears to be empty');
      }
    } else {
      warnings.push('Aligned data CSV is missing');
    }

    // Validate schema alignment results array
    if (!Array.isArray(schemaAlignmentResults.schemaAlignmentResults)) {
      errors.push('Schema alignment results array is invalid');
    } else {
      // Validate individual change details
      for (let i = 0; i < schemaAlignmentResults.schemaAlignmentResults.length; i++) {
        const change = schemaAlignmentResults.schemaAlignmentResults[i];
        if (!change.changeType) {
          warnings.push(`Change at index ${i} is missing changeType`);
        }
        if (!['add', 'remove', 'rename'].includes(change.changeType)) {
          warnings.push(`Change at index ${i} has invalid changeType: ${change.changeType}`);
        }
      }
    }

    // Validate summary statistics consistency
    const summary = schemaAlignmentResults.summary;
    const actualChanges = schemaAlignmentResults.schemaAlignmentResults.length;
    if (summary.totalChanges !== actualChanges) {
      warnings.push(`Summary totalChanges (${summary.totalChanges}) doesn't match actual changes count (${actualChanges})`);
    }

    const isValid = errors.length === 0;
    return { isValid, errors, warnings };
  } catch (error) {
    errors.push(`Validation error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    return { isValid: false, errors, warnings };
  }
}
