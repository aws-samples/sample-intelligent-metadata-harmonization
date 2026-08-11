/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Error handling utilities for frontend API calls
 */

/**
 * API error categories
 */
export enum ApiErrorCategory {
  CONNECTION = 'connection',
  AUTHENTICATION = 'authentication',
  VALIDATION = 'validation',
  API = 'api',
  SESSION = 'session',
  TIMEOUT = 'timeout',
  UNKNOWN = 'unknown'
}

/**
 * API error codes
 */
export enum ApiErrorCode {
  // Authentication errors
  UNAUTHORIZED = 'UNAUTHORIZED',
  INVALID_CREDENTIALS = 'INVALID_CREDENTIALS',
  TOKEN_EXPIRED = 'TOKEN_EXPIRED',

  // Validation errors
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  INVALID_REQUEST = 'INVALID_REQUEST',
  MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD',
  INVALID_FILE_TYPE = 'INVALID_FILE_TYPE',
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',

  // Metadata validation errors
  VALIDATION_JOB_NOT_FOUND = 'VALIDATION_JOB_NOT_FOUND',
  VALIDATION_JOB_FAILED = 'VALIDATION_JOB_FAILED',
  INVALID_SCHEMA_ID = 'INVALID_SCHEMA_ID',
  SCHEMA_NOT_FOUND = 'SCHEMA_NOT_FOUND',

  // Service errors
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  RATE_LIMITED = 'RATE_LIMITED',
  INTERNAL_ERROR = 'INTERNAL_ERROR',

  // Connection errors
  CONNECTION_ERROR = 'CONNECTION_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',

  // Unknown error
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

/**
 * API error details
 */
export interface ApiErrorDetails {
  code: ApiErrorCode;
  message: string;
  category: ApiErrorCategory;
  statusCode?: number;
  details?: Record<string, unknown>;
  recoveryOptions?: string[];
  retryAllowed?: boolean;
}

/**
 * Parse API error response
 * @param response - Fetch response object
 * @param errorData - Error data from response JSON
 * @returns API error details
 */
export async function parseApiError(
  response: Response,
  errorData?: { detail?: string; message?: string; [key: string]: unknown }
): Promise<ApiErrorDetails> {
  // Default error details
  const defaultError: ApiErrorDetails = {
    code: ApiErrorCode.UNKNOWN_ERROR,
    message: 'An unknown error occurred',
    category: ApiErrorCategory.UNKNOWN
  };

  try {
    // If no error data provided, try to parse from response
    if (!errorData) {
      try {
        errorData = await response.json();
      } catch {
        // If JSON parsing fails, use text
        try {
          errorData = { detail: await response.text() };
        } catch {
          // If text parsing fails, use status text
          errorData = { detail: response.statusText };
        }
      }
    }

    // Check if error data has API error structure
    if (errorData?.error && typeof errorData.error === 'object') {
      const apiError = errorData.error as {
        code?: string;
        message?: string;
        details?: { recovery_options?: string[]; retry_allowed?: boolean };
      };

      return {
        code: (apiError.code as any) || defaultError.code,
        message: apiError.message || defaultError.message,
        category: mapErrorCodeToCategory((apiError.code as any)) || defaultError.category,
        statusCode: response.status,
        details: apiError.details || {},
        recoveryOptions: apiError.details?.recovery_options || [],
        retryAllowed: apiError.details?.retry_allowed || false
      };
    }

    // If error data doesn't have API error structure, create from status code
    return createErrorFromStatusCode(response.status, errorData?.detail || errorData?.message);

  } catch (e) {
    console.error('Error parsing API error:', e);
    return {
      ...defaultError,
      statusCode: response.status,
      message: `Error ${response.status}: ${response.statusText}`
    };
  }
}

/**
 * Create error details from HTTP status code
 * @param statusCode - HTTP status code
 * @param message - Error message
 * @returns API error details
 */
function createErrorFromStatusCode(
  statusCode: number,
  message?: string
): ApiErrorDetails {
  // Default message based on status code
  let defaultMessage = 'An unknown error occurred';
  let code = ApiErrorCode.UNKNOWN_ERROR;
  let category = ApiErrorCategory.UNKNOWN;
  let retryAllowed = false;
  let recoveryOptions: string[] = [];

  if (400 <= statusCode && statusCode < 500) {
    if (statusCode === 400) {
      code = ApiErrorCode.INVALID_REQUEST;
      category = ApiErrorCategory.VALIDATION;
      defaultMessage = 'The request was invalid or malformed';
      recoveryOptions = ['Check request format and try again'];
    } else if (statusCode === 401) {
      code = ApiErrorCode.UNAUTHORIZED;
      category = ApiErrorCategory.AUTHENTICATION;
      defaultMessage = 'Authentication failed';
      recoveryOptions = ['Check API credentials', 'Renew authentication token'];
    } else if (statusCode === 403) {
      code = ApiErrorCode.UNAUTHORIZED;
      category = ApiErrorCategory.AUTHENTICATION;
      defaultMessage = 'Access denied';
      recoveryOptions = ['Verify permissions', 'Contact administrator'];
    } else if (statusCode === 404) {
      code = ApiErrorCode.VALIDATION_JOB_NOT_FOUND;
      category = ApiErrorCategory.VALIDATION;
      defaultMessage = 'Validation job not found';
      recoveryOptions = ['Check validation job ID', 'Create a new validation job'];
    } else if (statusCode === 413) {
      code = ApiErrorCode.FILE_TOO_LARGE;
      category = ApiErrorCategory.VALIDATION;
      defaultMessage = 'File size too large';
      recoveryOptions = ['Upload a smaller CSV file', 'Compress the file'];
    } else if (statusCode === 415) {
      code = ApiErrorCode.INVALID_FILE_TYPE;
      category = ApiErrorCategory.VALIDATION;
      defaultMessage = 'Invalid file type';
      recoveryOptions = ['Upload a CSV file', 'Check file format'];
    } else if (statusCode === 422) {
      code = ApiErrorCode.VALIDATION_ERROR;
      category = ApiErrorCategory.VALIDATION;
      defaultMessage = 'Validation error in request data';
      recoveryOptions = ['Check request data format'];
    } else if (statusCode === 429) {
      code = ApiErrorCode.RATE_LIMITED;
      category = ApiErrorCategory.API;
      defaultMessage = 'Rate limit exceeded';
      retryAllowed = true;
      recoveryOptions = ['Wait and retry later', 'Reduce request frequency'];
    }
  } else if (500 <= statusCode && statusCode < 600) {
    code = ApiErrorCode.INTERNAL_ERROR;
    category = ApiErrorCategory.API;
    defaultMessage = 'Server error';
    retryAllowed = true;
    recoveryOptions = ['Retry later', 'Contact support if the issue persists'];
  }

  return {
    code,
    message: message || defaultMessage,
    category,
    statusCode,
    retryAllowed,
    recoveryOptions
  };
}

/**
 * Map error code to category
 * @param code - API error code
 * @returns API error category
 */
function mapErrorCodeToCategory(code: ApiErrorCode): ApiErrorCategory {
  switch (code) {
    case ApiErrorCode.UNAUTHORIZED:
    case ApiErrorCode.INVALID_CREDENTIALS:
    case ApiErrorCode.TOKEN_EXPIRED:
      return ApiErrorCategory.AUTHENTICATION;

    case ApiErrorCode.VALIDATION_ERROR:
    case ApiErrorCode.INVALID_REQUEST:
    case ApiErrorCode.MISSING_REQUIRED_FIELD:
    case ApiErrorCode.INVALID_FILE_TYPE:
    case ApiErrorCode.FILE_TOO_LARGE:
    case ApiErrorCode.VALIDATION_JOB_NOT_FOUND:
    case ApiErrorCode.INVALID_SCHEMA_ID:
    case ApiErrorCode.SCHEMA_NOT_FOUND:
      return ApiErrorCategory.VALIDATION;

    case ApiErrorCode.VALIDATION_JOB_FAILED:
    case ApiErrorCode.SERVICE_UNAVAILABLE:
    case ApiErrorCode.RATE_LIMITED:
    case ApiErrorCode.INTERNAL_ERROR:
      return ApiErrorCategory.API;

    case ApiErrorCode.CONNECTION_ERROR:
    case ApiErrorCode.TIMEOUT_ERROR:
      return ApiErrorCategory.CONNECTION;

    default:
      return ApiErrorCategory.UNKNOWN;
  }
}

/**
 * Get user-friendly error message
 * @param error - API error details
 * @returns User-friendly error message
 */
export function getUserFriendlyErrorMessage(error: ApiErrorDetails): string {
  const baseMessage = error.message;

  switch (error.category) {
    case ApiErrorCategory.CONNECTION:
      return `${baseMessage}. Please check your internet connection and try again.`;

    case ApiErrorCategory.AUTHENTICATION:
      return `${baseMessage}. Your authentication credentials may have expired or are invalid. Please try logging in again.`;

    case ApiErrorCategory.VALIDATION:
      if (error.code === ApiErrorCode.FILE_TOO_LARGE) {
        return `${baseMessage}. Please upload a smaller CSV file and try again.`;
      } else if (error.code === ApiErrorCode.INVALID_FILE_TYPE) {
        return `${baseMessage}. Please upload a valid CSV file.`;
      } else if (error.code === ApiErrorCode.VALIDATION_JOB_NOT_FOUND) {
        return `${baseMessage}. The validation job may have expired or been removed. Please create a new validation job.`;
      } else if (error.code === ApiErrorCode.INVALID_SCHEMA_ID || error.code === ApiErrorCode.SCHEMA_NOT_FOUND) {
        return `${baseMessage}. Please select a valid schema and try again.`;
      } else {
        return `${baseMessage}. Please check your input data and try again.`;
      }

    case ApiErrorCategory.API:
      if (error.code === ApiErrorCode.RATE_LIMITED) {
        return `${baseMessage}. You've made too many requests in a short period. Please wait a moment before trying again.`;
      } else if (error.code === ApiErrorCode.SERVICE_UNAVAILABLE) {
        return `${baseMessage}. The metadata validation service is temporarily unavailable. Please try again later.`;
      } else if (error.code === ApiErrorCode.VALIDATION_JOB_FAILED) {
        return `${baseMessage}. The metadata validation failed to complete. Please check your file and try again.`;
      } else {
        return `${baseMessage}. Please try again later or contact support if the problem persists.`;
      }

    case ApiErrorCategory.TIMEOUT:
      return `${baseMessage}. The request took too long to complete. Please try again or try with a smaller file.`;

    default:
      return `${baseMessage}. If this issue persists, please contact support.`;
  }
}

/**
 * Handle API error response
 * @param response - Fetch response object
 * @returns Error message
 */
export async function handleApiError(response: Response): Promise<string> {
  try {
    const errorData = await response.json().catch(() => ({}));
    const error = await parseApiError(response, errorData);
    const userMessage = getUserFriendlyErrorMessage(error);

    // Log error for debugging
    console.error('API Error:', {
      status: response.status,
      statusText: response.statusText,
      error,
      userMessage
    });

    return userMessage;
  } catch (error) {
    console.error('Error handling API error:', error);
    return `Error: HTTP ${response.status} - ${response.statusText}`;
  }
}
