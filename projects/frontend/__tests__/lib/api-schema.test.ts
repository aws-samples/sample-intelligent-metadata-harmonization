/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Tests for schema-related API client methods
 */

import {
  getAvailableSchemas,
  getAvailableSchemasForUI,
  parseSchemaResponse,
  validateSchemaSelection,
  createValidationJob,
} from '../../lib/api';
import { SchemaInfo, ParsedSchemaData } from '../../lib/types';

// Mock fetch globally
global.fetch = jest.fn();

// Mock config
jest.mock('../../lib/config', () => ({
  getConfig: () => ({
    API_URI: 'http://localhost:8080',
  }),
}));

// Mock error handling
jest.mock('../../lib/error-handling', () => ({
  handleApiError: jest.fn().mockResolvedValue('API Error'),
}));

describe('Schema API Methods', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getAvailableSchemas', () => {
    const mockSchemas: SchemaInfo[] = [
      {
        coreSchemaId: 'core-1',
        name: 'Core Schema 1',
        coreSchemaPath: '/path/to/core1.json',
        coreSchemaS3Bucket: 'metadata-schemas',
        programSchemas: [
          {
            programName: 'Program A',
            s3Location: '/path/to/programa.json',
            s3Bucket: 'metadata-schemas',
            programSchemaId: 'program-a',
          },
          {
            programName: 'Program B',
            s3Location: '/path/to/programb.json',
            s3Bucket: 'metadata-schemas',
            programSchemaId: 'program-b',
          },
        ],
      },
      {
        coreSchemaId: 'core-2',
        name: 'Core Schema 2',
        coreSchemaPath: '/path/to/core2.json',
        coreSchemaS3Bucket: 'metadata-schemas',
        programSchemas: [
          {
            programName: 'Program C',
            s3Location: '/path/to/programc.json',
            s3Bucket: 'metadata-schemas',
            programSchemaId: 'program-c',
          },
        ],
      },
    ];

    it('should successfully fetch and parse schemas', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSchemas,
      });

      const result = await getAvailableSchemas();

      expect(result.success).toBe(true);
      expect(result.schemas).toEqual(mockSchemas);
      expect(result.error).toBeUndefined();
    });

    it('should handle API errors', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const result = await getAvailableSchemas();

      expect(result.success).toBe(false);
      expect(result.error).toBe('API Error');
      expect(result.schemas).toBeUndefined();
    });

    it('should handle invalid response format', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ invalid: 'format' }),
      });

      const result = await getAvailableSchemas();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid response format from schema API');
    });

    it('should handle network errors', async () => {
      (fetch as jest.Mock).mockRejectedValueOnce(new TypeError('fetch failed'));

      const result = await getAvailableSchemas();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Network error: Unable to connect to schema service.');
    });

    it('should include authorization header when token provided', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSchemas,
      });

      await getAvailableSchemas('test-token');

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/metadata/schema',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
          }),
        })
      );
    });
  });

  describe('parseSchemaResponse', () => {
    const mockSchemas: SchemaInfo[] = [
      {
        coreSchemaId: 'core-1',
        name: 'Core Schema 1',
        coreSchemaPath: '/path/to/core1.json',
        coreSchemaS3Bucket: 'metadata-schemas',
        programSchemas: [
          {
            programName: 'Program A',
            s3Location: '/path/to/programa.json',
            s3Bucket: 'metadata-schemas',
            programSchemaId: 'program-a',
          },
          {
            programName: 'Program B',
            s3Location: '/path/to/programb.json',
            s3Bucket: 'metadata-schemas',
            programSchemaId: 'program-b',
          },
        ],
      },
      {
        coreSchemaId: 'core-2',
        name: 'Core Schema 2',
        coreSchemaPath: '/path/to/core2.json',
        coreSchemaS3Bucket: 'metadata-schemas',
        programSchemas: [
          {
            programName: 'Program C',
            s3Location: '/path/to/programc.json',
            s3Bucket: 'metadata-schemas',
            programSchemaId: 'program-c',
          },
        ],
      },
    ];

    it('should extract unique core schemas', () => {
      const result = parseSchemaResponse(mockSchemas);

      expect(result.coreSchemas).toHaveLength(2);
      expect(result.coreSchemas[0]).toEqual({
        id: 'core-1',
        name: 'Core Schema 1',
        description: 'Core schema: Core Schema 1',
      });
      expect(result.coreSchemas[1]).toEqual({
        id: 'core-2',
        name: 'Core Schema 2',
        description: 'Core schema: Core Schema 2',
      });
    });

    it('should extract all program schemas', () => {
      const result = parseSchemaResponse(mockSchemas);

      expect(result.programSchemas).toHaveLength(3);
      expect(result.programSchemas).toContainEqual({
        id: 'program-a',
        name: 'Program A',
        description: 'Program: Program A',
      });
      expect(result.programSchemas).toContainEqual({
        id: 'program-b',
        name: 'Program B',
        description: 'Program: Program B',
      });
      expect(result.programSchemas).toContainEqual({
        id: 'program-c',
        name: 'Program C',
        description: 'Program: Program C',
      });
    });

    it('should handle empty schema array', () => {
      const result = parseSchemaResponse([]);

      expect(result.coreSchemas).toHaveLength(0);
      expect(result.programSchemas).toHaveLength(0);
      expect(result.rawSchemas).toEqual([]);
    });
  });

  describe('getAvailableSchemasForUI', () => {
    const mockSchemas: SchemaInfo[] = [
      {
        coreSchemaId: 'core-1',
        name: 'Core Schema 1',
        coreSchemaPath: '/path/to/core1.json',
        coreSchemaS3Bucket: 'metadata-schemas',
        programSchemas: [
          {
            programName: 'Program A',
            s3Location: '/path/to/programa.json',
            s3Bucket: 'metadata-schemas',
            programSchemaId: 'program-a',
          },
        ],
      },
    ];

    it('should return parsed schema data for UI', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSchemas,
      });

      const result = await getAvailableSchemasForUI();

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.data!.coreSchemas).toHaveLength(1);
      expect(result.data!.programSchemas).toHaveLength(1);
    });

    it('should handle no schemas available', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      const result = await getAvailableSchemasForUI();

      expect(result.success).toBe(false);
      expect(result.error).toBe('No schemas available for validation');
    });
  });

  describe('validateSchemaSelection', () => {
    const mockParsedData: ParsedSchemaData = {
      coreSchemas: [
        { id: 'core-1', name: 'Core 1', description: 'Core schema 1' },
        { id: 'core-2', name: 'Core 2', description: 'Core schema 2' },
      ],
      programSchemas: [
        { id: 'program-a', name: 'Program A', description: 'Program A' },
        { id: 'program-b', name: 'Program B', description: 'Program B' },
      ],
      rawSchemas: [],
    };

    it('should validate correct schema selection', () => {
      const result = validateSchemaSelection('core-1', 'program-a', mockParsedData);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect missing core schema ID', () => {
      const result = validateSchemaSelection('', 'program-a', mockParsedData);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Core schema ID is required');
    });

    it('should detect missing program schema ID', () => {
      const result = validateSchemaSelection('core-1', '', mockParsedData);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Program schema ID is required');
    });

    it('should detect invalid core schema ID', () => {
      const result = validateSchemaSelection('invalid-core', 'program-a', mockParsedData);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Core schema ID "invalid-core" is not available');
    });

    it('should detect invalid program schema ID', () => {
      const result = validateSchemaSelection('core-1', 'invalid-program', mockParsedData);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Program schema ID "invalid-program" is not available');
    });

    it('should work without available schemas for basic validation', () => {
      const result = validateSchemaSelection('core-1', 'program-a');

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('createValidationJob with schema parameters', () => {
    const mockFile = new File(['test content'], 'test.csv', { type: 'text/csv' });

    it('should create validation job with schema IDs', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ jobId: 'test-job-id' }),
      });

      const result = await createValidationJob(mockFile, 'core-1', 'program-a');

      expect(result.success).toBe(true);
      expect(result.jobId).toBe('test-job-id');

      // Verify FormData was created with correct schema IDs
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/metadata/validate',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );
    });

    it('should validate required parameters', async () => {
      const result = await createValidationJob(mockFile, '', 'program-a');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Both core schema ID and program schema ID are required');
    });

    it('should validate file parameter', async () => {
      const result = await createValidationJob(null as any, 'core-1', 'program-a');

      expect(result.success).toBe(false);
      expect(result.error).toBe('File is required for validation job creation');
    });
  });
});
