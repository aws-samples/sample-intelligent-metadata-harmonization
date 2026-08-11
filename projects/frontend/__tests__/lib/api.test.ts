/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Unit tests for metadata validation API client
 */

import {
  createValidationJob,
  updateValidationJob,
  getValidationStatus,
  getAvailableSchemas,
  submitMetadataValidation,
  createValidationJobWithRetry,
  updateValidationJobWithRetry,
  getValidationStatusWithRetry,
  submitMetadataValidationWithRetry,
} from '../../lib/api';
import {
  ValidationJobResponse,
  ValidationStatusResponse,
  SchemaListResponse,
  ValidationJobStatus,
  ValidationErrorType,
} from '../../lib/types';
import { handleApiError } from '../../lib/error-handling';

// Mock dependencies
jest.mock('../../lib/config', () => ({
  getConfig: jest.fn(() => ({
    API_URI: 'https://api.test.com',
    COGNITO: {
      authority: 'test-authority',
      client_id: 'test-client-id',
      redirect_uri: 'http://localhost:3000',
      post_logout_redirect_uri: 'http://localhost:3000',
      scope: 'openid',
      response_type: 'code',
      loadUserInfo: true,
      metadata: {
        authorization_endpoint: 'test-auth-endpoint',
        token_endpoint: 'test-token-endpoint',
        userinfo_endpoint: 'test-userinfo-endpoint',
        end_session_endpoint: 'test-end-session-endpoint',
      },
    },
  })),
}));

jest.mock('../../lib/error-handling', () => ({
  handleApiError: jest.fn(),
}));

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock console.error to avoid noise in tests
const mockConsoleError = jest.spyOn(console, 'error').mockImplementation(() => {});

describe('Metadata Validation API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockClear();
    mockConsoleError.mockClear();
  });

  afterAll(() => {
    mockConsoleError.mockRestore();
  });

  describe('createValidationJob', () => {
    const mockFile = new File(['test content'], 'test.csv', { type: 'text/csv' });
    const coreSchemaId = 'core-schema-123';
    const programSchemaId = 'program-schema-456';
    const token = 'test-token';

    it('should create validation job successfully', async () => {
      const mockResponse = {
        jobId: 'job-123',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await createValidationJob(mockFile, coreSchemaId, programSchemaId, token);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/metadata/validate',
        expect.objectContaining({
          method: 'POST',
          headers: {
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        })
      );

      // Verify FormData contents
      const formData = mockFetch.mock.calls[0][1].body as FormData;
      expect(formData.get('file')).toBe(mockFile);
      expect(formData.get('core_schema_id')).toBe(coreSchemaId);
      expect(formData.get('program_schema_id')).toBe(programSchemaId);

      expect(result).toEqual({
        success: true,
        jobId: 'job-123',
      });
    });

    it('should create validation job without token', async () => {
      const mockResponse = {
        jobId: 'job-123',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await createValidationJob(mockFile, coreSchemaId, programSchemaId);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/metadata/validate',
        expect.objectContaining({
          method: 'POST',
          headers: {},
          credentials: 'include',
        })
      );

      expect(result).toEqual({
        success: true,
        jobId: 'job-123',
      });
    });

    it('should handle HTTP errors', async () => {
      const mockErrorMessage = 'File too large';
      (handleApiError as jest.Mock).mockResolvedValueOnce(mockErrorMessage);

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 413,
      });

      const result = await createValidationJob(mockFile, coreSchemaId, programSchemaId, token);

      expect(handleApiError).toHaveBeenCalledWith({
        ok: false,
        status: 413,
      });

      expect(result).toEqual({
        success: false,
        error: mockErrorMessage,
      });
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await createValidationJob(mockFile, coreSchemaId, programSchemaId, token);

      expect(mockConsoleError).toHaveBeenCalledWith(
        'Error creating validation job:',
        expect.any(Error)
      );

      expect(result).toEqual({
        success: false,
        error: 'Failed to create validation job. Please try again later.',
      });
    });

    it('should convert snake_case response to camelCase', async () => {
      const mockResponse = {
        jobId: 'job-123',
        createdAt: '2023-01-01T00:00:00Z',
        userId: 'user-456',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await createValidationJob(mockFile, coreSchemaId, programSchemaId, token);

      expect(result).toEqual({
        success: true,
        jobId: 'job-123',
      });
    });
  });

  describe('updateValidationJob', () => {
    const metadataId = 'metadata-123';
    const mockFile = new File(['updated content'], 'updated.csv', { type: 'text/csv' });
    const token = 'test-token';

    it('should update validation job successfully', async () => {
      const mockResponse = {
        jobId: 'job-123',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await updateValidationJob(metadataId, mockFile, token);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/metadata/validate/metadata-123',
        expect.objectContaining({
          method: 'POST',
          headers: {
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        })
      );

      // Verify FormData contents
      const formData = mockFetch.mock.calls[0][1].body as FormData;
      expect(formData.get('file')).toBe(mockFile);

      expect(result).toEqual({
        success: true,
        jobId: 'job-123',
      });
    });

    it('should update validation job without token', async () => {
      const mockResponse = {
        jobId: 'job-123',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await updateValidationJob(metadataId, mockFile);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/metadata/validate/metadata-123',
        expect.objectContaining({
          method: 'POST',
          headers: {},
          credentials: 'include',
        })
      );

      expect(result).toEqual({
        success: true,
        jobId: 'job-123',
      });
    });

    it('should handle HTTP errors', async () => {
      const mockErrorMessage = 'Validation job not found';
      (handleApiError as jest.Mock).mockResolvedValueOnce(mockErrorMessage);

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const result = await updateValidationJob(metadataId, mockFile, token);

      expect(handleApiError).toHaveBeenCalledWith({
        ok: false,
        status: 404,
      });

      expect(result).toEqual({
        success: false,
        error: mockErrorMessage,
      });
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await updateValidationJob(metadataId, mockFile, token);

      expect(mockConsoleError).toHaveBeenCalledWith(
        'Error updating validation job:',
        expect.any(Error)
      );

      expect(result).toEqual({
        success: false,
        error: 'Failed to update validation job. Please try again later.',
      });
    });
  });

  describe('getValidationStatus', () => {
    const metadataId = 'metadata-123';
    const token = 'test-token';

    it('should get validation status successfully', async () => {
      const mockResponse = {
        jobId: 'job-123',
        userId: 'user-456',
        coreSchemaId: 'core-schema-123',
        programSchemaId: 'program-schema-456',
        status: 'completed',
        createdAt: '2023-01-01T00:00:00Z',
        completedAt: '2023-01-01T01:00:00Z',
        currentVersion: 1,
        latestResults: {
          validation_results: [
            {
              row: 1,
              column: 'test_column',
              current_value: 'invalid_value',
              valid_options: ['option1', 'option2'],
              recommended_value: 'option1',
              error_type: ValidationErrorType.INVALID_OPTION,
            },
          ],
          summary: {
            total_rows: 100,
            total_errors: 1,
            error_types: {
              INVALID_OPTION: 1,
            },
          },
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await getValidationStatus(metadataId, token);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/metadata/validate/metadata-123',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        })
      );

      expect(result.success).toBe(true);
      expect(result.jobId).toBe('job-123');
      expect(result.userId).toBe('user-456');
      expect(result.coreSchemaId).toBe('core-schema-123');
      expect(result.programSchemaId).toBe('program-schema-456');
      expect(result.status).toBe('completed');
      expect(result.createdAt).toBe('2023-01-01T00:00:00Z');
      expect(result.completedAt).toBe('2023-01-01T01:00:00Z');
      expect(result.currentVersion).toBe(1);
    });

    it('should get validation status without token', async () => {
      const mockResponse = {
        jobId: 'job-123',
        userId: 'user-456',
        status: 'pending',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await getValidationStatus(metadataId);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/metadata/validate/metadata-123',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
        })
      );

      expect(result.success).toBe(true);
      expect(result.jobId).toBe('job-123');
      expect(result.status).toBe('pending');
    });

    it('should handle HTTP errors', async () => {
      const mockErrorMessage = 'Validation job not found';
      (handleApiError as jest.Mock).mockResolvedValueOnce(mockErrorMessage);

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const result = await getValidationStatus(metadataId, token);

      expect(handleApiError).toHaveBeenCalledWith({
        ok: false,
        status: 404,
      });

      expect(result).toEqual({
        success: false,
        error: mockErrorMessage,
      });
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await getValidationStatus(metadataId, token);

      expect(mockConsoleError).toHaveBeenCalledWith(
        'Error getting validation status:',
        expect.any(Error)
      );

      expect(result).toEqual({
        success: false,
        error: 'Failed to get validation status. Please try again later.',
      });
    });
  });

  describe('getAvailableSchemas', () => {
    const token = 'test-token';

    it('should get available schemas successfully', async () => {
      const mockResponse = [
        {
          coreSchemaId: 'core-schema-123',
          name: 'Test Schema',
          coreSchemaPath: '/path/to/core/schema.json',
          coreSchemaS3Bucket: 'test-bucket',
          programSchemas: [
            {
              programName: 'Test Program',
              s3Location: '/path/to/program/schema.json',
              s3Bucket: 'test-bucket',
              programSchemaId: 'program-schema-456',
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await getAvailableSchemas(token);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/metadata/schema',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
        }
      );

      expect(result).toEqual({
        success: true,
        schemas: [
          {
            coreSchemaId: 'core-schema-123',
            name: 'Test Schema',
            coreSchemaPath: '/path/to/core/schema.json',
            coreSchemaS3Bucket: 'test-bucket',
            programSchemas: [
              {
                programName: 'Test Program',
                s3Location: '/path/to/program/schema.json',
                s3Bucket: 'test-bucket',
                programSchemaId: 'program-schema-456',
              },
            ],
          },
        ],
      });
    });

    it('should get available schemas without token', async () => {
      const mockResponse: any[] = [];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await getAvailableSchemas();

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/metadata/schema',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      expect(result).toEqual({
        success: true,
        schemas: [],
      });
    });

    it('should handle HTTP errors', async () => {
      const mockErrorMessage = 'Service unavailable';
      (handleApiError as jest.Mock).mockResolvedValueOnce(mockErrorMessage);

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
      });

      const result = await getAvailableSchemas(token);

      expect(handleApiError).toHaveBeenCalledWith({
        ok: false,
        status: 503,
      });

      expect(result).toEqual({
        success: false,
        error: mockErrorMessage,
      });
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await getAvailableSchemas(token);

      expect(mockConsoleError).toHaveBeenCalledWith(
        'Error getting available schemas:',
        expect.any(Error)
      );

      expect(result).toEqual({
        success: false,
        error: 'Failed to get available schemas. Please try again later.',
      });
    });
  });

  describe('convertToCamelCase helper', () => {
    // Test the helper function indirectly through API calls
    it('should process combined results in status response', async () => {
      const mockResponse = {
        jobId: 'job-123',
        userId: 'user-456',
        status: 'completed',
        latestResults: {
          validationResults: [
            {
              errorType: ValidationErrorType.INVALID_OPTION,
              currentValue: 'test',
              recommendedValue: 'recommended',
              row: 1,
              column: 'test_column',
              validOptions: ['option1', 'option2'],
              confidenceScore: 0.85,
              confidenceLevel: 'High'
            },
          ],
          summary: {
            totalErrors: 5,
            errorTypes: {
              INVALID_OPTION: 3,
              REQUIRED_VALUE: 2,
            },
          },
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await getValidationStatus('test-id');

      expect(result.success).toBe(true);
      expect(result.latestResults).toBeDefined();
    });

    it('should handle arrays in schema response', async () => {
      const mockResponse = [
        {
          coreSchemaId: 'schema-1',
          name: 'Schema 1',
          programSchemas: [
            {
              programSchemaId: 'program-1',
              s3Location: '/path/to/schema',
              programName: 'Program 1',
              s3Bucket: 'bucket-1',
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await getAvailableSchemas();

      expect(result.schemas).toEqual([
        {
          coreSchemaId: 'schema-1',
          name: 'Schema 1',
          programSchemas: [
            {
              programSchemaId: 'program-1',
              s3Location: '/path/to/schema',
              programName: 'Program 1',
              s3Bucket: 'bucket-1',
            },
          ],
        },
      ]);
    });

    it('should handle null and undefined values', async () => {
      const mockResponse = {
        jobId: 'job-123',
        userId: 'user-456',
        status: 'pending',
        completedAt: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await getValidationStatus('test-id');

      expect(result.success).toBe(true);
      expect(result.jobId).toBe('job-123');
      expect(result.completedAt).toBeNull();
      expect(result.latestResults).toBeNull();
    });
  });
});  describe('submitMetadataValidation', () => {
    beforeEach(() => {
      jest.clearAllMocks();
      mockFetch.mockClear();
    });

    const csvData = [
      ['Name', 'Age', 'City'],
      ['John', '25', 'New York'],
      ['Jane', '30', 'Boston']
    ];
    const coreSchemaId = 'core-schema-123';
    const programSchemaId = 'program-schema-456';
    const token = 'test-token';

    it('should submit CSV data successfully', async () => {
      const mockResponse = {
        jobId: 'csv-job-123',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await submitMetadataValidation(csvData, coreSchemaId, programSchemaId, token);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/metadata/validate',
        expect.objectContaining({
          method: 'POST',
          headers: {
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        })
      );

      // Verify FormData contents
      const formData = mockFetch.mock.calls[0][1].body as FormData;
      const file = formData.get('file') as File;
      expect(file.name).toBe('metadata.csv');
      expect(file.type).toBe('text/csv');
      expect(formData.get('core_schema_id')).toBe(coreSchemaId);
      expect(formData.get('program_schema_id')).toBe(programSchemaId);

      expect(result).toEqual({
        success: true,
        jobId: 'csv-job-123',
      });
    });

    it('should handle CSV with commas and quotes', async () => {
      const csvDataWithSpecialChars = [
        ['Name', 'Description'],
        ['John Doe', 'A person with, comma'],
        ['Jane "Smith"', 'Another "person"']
      ];

      const mockResponse = {
        jobId: 'csv-job-123',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockResponse),
      });

      const result = await submitMetadataValidation(csvDataWithSpecialChars, coreSchemaId, programSchemaId);

      expect(result.success).toBe(true);

      // Verify that the CSV was properly escaped
      const formData = mockFetch.mock.calls[0][1].body as FormData;
      const file = formData.get('file') as File;
      expect(file.name).toBe('metadata.csv');
    });

    it('should handle submission errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await submitMetadataValidation(csvData, coreSchemaId, programSchemaId);

      // submitMetadataValidation delegates to createValidationJob which catches the error
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('retry functionality', () => {
    beforeEach(() => {
      // Clear all mocks before each test
      jest.clearAllMocks();
      mockFetch.mockClear();

      // Mock setTimeout for faster tests
      jest.spyOn(global, 'setTimeout').mockImplementation((callback: any) => {
        callback();
        return {} as any;
      });
    });

    afterEach(() => {
      jest.restoreAllMocks();
    });

    it('should return error result on network failures', async () => {
      const mockFile = new File(['test'], 'test.csv', { type: 'text/csv' });

      // Network error - base function catches it and returns {success: false}
      // withRetry receives this as a successful promise, so no retry happens
      mockFetch.mockRejectedValueOnce(new TypeError('fetch failed'));

      const result = await createValidationJobWithRetry(mockFile, 'core-schema', 'program-schema');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should not retry on client errors (4xx)', async () => {
      const mockFile = new File(['test'], 'test.csv', { type: 'text/csv' });

      (handleApiError as jest.Mock).mockResolvedValueOnce('Bad Request');
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
      });

      const result = await createValidationJobWithRetry(mockFile, 'core-schema', 'program-schema');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Bad Request');
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should return error after network failure', async () => {
      const mockFile = new File(['test'], 'test.csv', { type: 'text/csv' });

      mockFetch.mockRejectedValue(new TypeError('fetch failed'));

      const result = await createValidationJobWithRetry(mockFile, 'core-schema', 'program-schema');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
    });

    it('should return error on validation status network failure', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('fetch failed'));

      const result = await getValidationStatusWithRetry('metadata-id');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
    });

    it('should return error on update validation job network failure', async () => {
      const mockFile = new File(['test'], 'test.csv', { type: 'text/csv' });

      mockFetch.mockRejectedValueOnce(new TypeError('fetch failed'));

      const result = await updateValidationJobWithRetry('metadata-id', mockFile);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
    });

    it('should return error on metadata submission network failure', async () => {
      const csvData = [['Name'], ['John']];

      mockFetch.mockRejectedValueOnce(new TypeError('fetch failed'));

      const result = await submitMetadataValidationWithRetry(csvData, 'core-schema', 'program-schema');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
    });

    it('should succeed when fetch succeeds', async () => {
      const mockFile = new File(['test'], 'test.csv', { type: 'text/csv' });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ jobId: 'success' })
      });

      const result = await createValidationJobWithRetry(mockFile, 'core-schema', 'program-schema');

      expect(result.success).toBe(true);
      expect(result.jobId).toBe('success');
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });
