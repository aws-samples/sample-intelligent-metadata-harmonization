/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import { beforeEach } from 'node:test';
import {
  createValidationJob,
  updateValidationJob,
  getValidationStatus,
  pollValidationStatus,
  getAvailableSchemas,
  testApiConnectivity,
  validateApiConfiguration
} from '../../lib/api';
import { ValidationJobStatus } from '../../lib/types';

// Mock fetch globally
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// Mock config
jest.mock('../../lib/config', () => ({
  getConfig: () => ({
    API_URI: 'https://test-api.example.com'
  })
}));

describe('API Client Validation Methods', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockClear();
  });

  describe('createValidationJob', () => {
    it('should make POST request to correct endpoint with FormData', async () => {
      const mockFile = new File(['test,data\n1,2'], 'test.csv', { type: 'text/csv' });
      const mockResponse = { jobId: 'test-job-123' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        status: 200,
        statusText: 'OK'
      } as Response);

      const result = await createValidationJob(
        mockFile,
        'core-schema-1',
        'program-schema-1',
        'test-token'
      );

      expect(mockFetch).toHaveBeenCalledWith(
        'https://test-api.example.com/api/v1/metadata/validate',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          }),
          body: expect.any(FormData)
        })
      );

      expect(result).toEqual({
        success: true,
        jobId: 'test-job-123'
      });
    });

    it('should handle API errors correctly', async () => {
      const mockFile = new File(['test,data\n1,2'], 'test.csv', { type: 'text/csv' });

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: async () => 'Invalid file format'
      } as Response);

      const result = await createValidationJob(
        mockFile,
        'core-schema-1',
        'program-schema-1'
      );

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('should validate required parameters', async () => {
      const result = await createValidationJob(
        null as any,
        'core-schema-1',
        'program-schema-1'
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('File is required');
    });
  });

  describe('updateValidationJob', () => {
    it('should make POST request to correct endpoint with job ID', async () => {
      const mockFile = new File(['test,data\n1,2'], 'test.csv', { type: 'text/csv' });
      const mockResponse = { jobId: 'test-job-123' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        status: 200,
        statusText: 'OK'
      } as Response);

      const result = await updateValidationJob(
        'test-job-123',
        mockFile,
        'test-token'
      );

      expect(mockFetch).toHaveBeenCalledWith(
        'https://test-api.example.com/api/v1/metadata/validate/test-job-123',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          }),
          body: expect.any(FormData)
        })
      );

      expect(result).toEqual({
        success: true,
        jobId: 'test-job-123'
      });
    });
  });

  describe('getValidationStatus', () => {
    it('should make GET request to correct endpoint', async () => {
      const mockResponse = {
        jobId: 'test-job-123',
        userId: 'test-user',
        status: 'COMPLETED',
        coreSchemaId: 'core-schema-1',
        programSchemaId: 'program-schema-1',
        createdAt: '2024-01-01T00:00:00Z',
        completedAt: '2024-01-01T00:01:00Z',
        currentVersion: 1,
        latestResults: null
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        status: 200,
        statusText: 'OK'
      } as Response);

      const result = await getValidationStatus('test-job-123', 'test-token');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://test-api.example.com/api/v1/metadata/validate/test-job-123',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
          })
        })
      );

      expect(result.success).toBe(true);
      expect(result.jobId).toBe('test-job-123');
      expect(result.status).toBe('COMPLETED');
    });
  });

  describe('pollValidationStatus', () => {
    it('should handle polling configuration correctly', async () => {
      // Test that polling function exists and can be called
      expect(typeof pollValidationStatus).toBe('function');

      // Test with mock that immediately returns completed status
      const mockCompletedResponse = {
        success: true,
        jobId: 'test-job-123',
        userId: 'test-user',
        status: ValidationJobStatus.COMPLETED,
        latestResults: null
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          jobId: 'test-job-123',
          userId: 'test-user',
          status: 'COMPLETED',
          latestResults: null
        }),
        status: 200,
        statusText: 'OK'
      } as Response);

      const statusUpdateCallback = jest.fn();

      const result = await pollValidationStatus(
        'test-job-123',
        statusUpdateCallback,
        'test-token',
        {
          pollInterval: 10, // Fast polling for test
          maxAttempts: 10,
          timeoutMs: 5000
        }
      );

      expect(result.success).toBe(true);
      expect(result.status).toBe('COMPLETED'); // API returns string, not enum
      expect(statusUpdateCallback).toHaveBeenCalled();
    }, 10000);

    it('should handle timeout configuration', async () => {
      // Test that timeout options are accepted
      const options = {
        pollInterval: 100,
        maxAttempts: 2,
        timeoutMs: 1000
      };

      // Mock to return pending status to trigger timeout
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          jobId: 'test-job-123',
          userId: 'test-user',
          status: 'PENDING',
          latestResults: null
        }),
        status: 200,
        statusText: 'OK'
      } as Response);

      await expect(
        pollValidationStatus('test-job-123', undefined, 'test-token', options)
      ).rejects.toThrow();
    }, 10000);
  });

  describe('getAvailableSchemas', () => {
    it('should make GET request to schema endpoint', async () => {
      const mockSchemas = [
        {
          coreSchemaId: 'core-1',
          name: 'Test Core Schema',
          coreSchemaPath: '/path/to/core',
          coreSchemaS3Bucket: 'test-bucket',
          programSchemas: [
            {
              programName: 'Test Program',
              s3Location: '/path/to/program',
              s3Bucket: 'test-bucket',
              programSchemaId: 'program-1'
            }
          ]
        }
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSchemas,
        status: 200,
        statusText: 'OK'
      } as Response);

      const result = await getAvailableSchemas('test-token');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://test-api.example.com/api/v1/metadata/schema',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
          })
        })
      );

      expect(result.success).toBe(true);
      expect(result.schemas).toEqual(mockSchemas);
    });
  });

  describe('testApiConnectivity', () => {
    it('should test schema endpoint connectivity', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
        status: 200,
        statusText: 'OK'
      } as Response);

      const result = await testApiConnectivity('test-token');

      expect(result.success).toBe(true);
      expect(result.results.schemaEndpoint).toBe(true);
    });

    it('should handle connectivity failures', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await testApiConnectivity('test-token');

      expect(result.success).toBe(false);
      expect(result.results.schemaEndpoint).toBe(false);
      expect(result.results.schemaError).toBeDefined();
    });
  });

  describe('validateApiConfiguration', () => {
    it('should validate API configuration', () => {
      const result = validateApiConfiguration();

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });
});
