/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Schema alignment helper functions tests

import {
  processCombinedResults,
  extractSchemaAlignmentResults,
  hasSchemaAlignmentResults,
  processColumnMappingsToChanges,
  applySchemaAlignmentToData,
  generateSchemaAlignmentSummary,
  parseSchemaAlignmentCsv,
  validateSchemaAlignmentData,
} from '../../lib/api';
import {
  ValidationStatusResponse,
  SchemaAlignmentResults,
  SchemaAlignmentChangeDetail,
  SchemaAlignmentResultsSummary,
  SchemaAlignmentChangeType,
  CombinedResults,
  ValidationErrorType,
} from '../../lib/types';

describe('Schema Alignment Helper Functions', () => {
  describe('processCombinedResults', () => {
    it('should process new CombinedResults format', () => {
      const rawResults = {
        validationResults: {
          validationResults: [
            {
              row: 1,
              column: 'test_column',
              currentValue: 'invalid_value',
              validOptions: ['option1', 'option2'],
              recommendedValue: 'option1',
              errorType: ValidationErrorType.INVALID_OPTION,
              confidenceScore: 0.85,
              confidenceLevel: 'High'
            },
          ],
          summary: {
            totalRows: 100,
            totalErrors: 1,
            errorTypes: {
              INVALID_OPTION: 1,
            },
          },
        },
        schemaAlignmentResults: {
          schemaAlignmentResults: [
            {
              changeType: 'rename',
              originalColumn: 'name',
              newColumn: 'full_name',
              reason: 'Schema standardization',
              rowCountAffected: 1
            },
            {
              changeType: 'rename',
              originalColumn: 'age',
              newColumn: 'age_years',
              reason: 'Schema standardization',
              rowCountAffected: 1
            }
          ],
          summary: {
            jobId: 'test-job-123',
            version: 1,
            timestamp: new Date().toISOString(),
            originalDataCsv: 'name,age\nJohn,30',
            alignedDataCsv: 'full_name,age_years\nJohn,30',
            totalChanges: 2,
            columnsRenamed: 2,
            columnsAdded: 0,
            columnsRemoved: 0,
            rowsOriginal: 1,
            rowsAligned: 1
          }
        }
      };

      const result = processCombinedResults(rawResults);

      expect(result.validationResults).toBeTruthy();
      expect(result.validationResults?.validationResults).toHaveLength(1);
      expect(result.schemaAlignmentResults).toBeTruthy();
      expect(result.schemaAlignmentResults?.schemaAlignmentResults).toHaveLength(2);
      expect(result.schemaAlignmentResults?.summary.originalDataCsv).toBe('name,age\nJohn,30');
      expect(result.schemaAlignmentResults?.summary.alignedDataCsv).toBe('full_name,age_years\nJohn,30');
    });

    it('should process legacy validation results format', () => {
      const rawResults = {
        validation_results: [
          {
            row: 1,
            column: 'test_column',
            current_value: 'invalid_value',
            valid_options: ['option1', 'option2'],
            recommended_value: 'option1',
            error_type: ValidationErrorType.INVALID_OPTION,
            confidence_score: 0.85,
            confidence_level: 'High'
          },
        ],
        summary: {
          total_rows: 100,
          total_errors: 1,
          error_types: {
            INVALID_OPTION: 1,
          },
        },
      };

      const result = processCombinedResults(rawResults);

      expect(result.validationResults).toBeTruthy();
      expect(result.validationResults?.validationResults).toHaveLength(1);
      expect(result.validationResults?.validationResults[0].currentValue).toBe('invalid_value');
      expect(result.schemaAlignmentResults).toBeNull();
    });

    it('should handle invalid input', () => {
      const result = processCombinedResults(null);
      expect(result.validationResults).toBeNull();
      expect(result.schemaAlignmentResults).toBeNull();
    });
  });

  describe('extractSchemaAlignmentResults', () => {
    it('should extract schema alignment results from status response', () => {
      const statusResponse: ValidationStatusResponse = {
        success: true,
        jobId: 'test-job',
        latestResults: {
          validationResults: null,
          schemaAlignmentResults: {
            originalDataCsv: 'name,age\nJohn,30',
            alignedDataCsv: 'full_name,age_years\nJohn,30',
            columnMappings: {
              'name': 'full_name',
              'age': 'age_years'
            }
          }
        }
      };

      const result = extractSchemaAlignmentResults(statusResponse);
      expect(result).toBeTruthy();
      expect(result?.columnMappings).toEqual({
        'name': 'full_name',
        'age': 'age_years'
      });
    });

    it('should return null when no schema alignment results', () => {
      const statusResponse: ValidationStatusResponse = {
        success: true,
        jobId: 'test-job',
        latestResults: {
          validationResults: null,
          schemaAlignmentResults: null
        }
      };

      const result = extractSchemaAlignmentResults(statusResponse);
      expect(result).toBeNull();
    });
  });

  describe('hasSchemaAlignmentResults', () => {
    it('should return true when schema alignment results exist', () => {
      const statusResponse: ValidationStatusResponse = {
        success: true,
        jobId: 'test-job',
        latestResults: {
          validationResults: null,
          schemaAlignmentResults: {
            schemaAlignmentResults: [
              {
                changeType: 'rename',
                originalColumn: 'name',
                newColumn: 'full_name',
                reason: 'Schema standardization',
                rowCountAffected: 1
              }
            ],
            summary: {
              jobId: 'test-job-123',
              version: 1,
              timestamp: new Date().toISOString(),
              originalDataCsv: 'name\nJohn',
              alignedDataCsv: 'full_name\nJohn',
              totalChanges: 1,
              columnsRenamed: 1,
              columnsAdded: 0,
              columnsRemoved: 0,
              rowsOriginal: 1,
              rowsAligned: 1
            }
          }
        }
      };

      expect(hasSchemaAlignmentResults(statusResponse)).toBe(true);
    });

    it('should return false when no schema alignment results', () => {
      const statusResponse: ValidationStatusResponse = {
        success: true,
        jobId: 'test-job',
        latestResults: {
          validationResults: null,
          schemaAlignmentResults: null
        }
      };

      expect(hasSchemaAlignmentResults(statusResponse)).toBe(false);
    });
  });

  describe('processColumnMappingsToChanges', () => {
    it('should convert column mappings to schema alignment changes', () => {
      const columnMappings = {
        'name': 'full_name',
        'age': 'age_years',
        'city': 'city' // No change
      };

      const changes = processColumnMappingsToChanges(columnMappings);

      expect(changes).toHaveLength(2); // Only changed columns
      expect(changes[0]).toMatchObject({
        type: SchemaAlignmentChangeType.COLUMN_RENAMED,
        originalColumn: 'name',
        alignedColumn: 'full_name',
        description: 'Column "name" renamed to "full_name"',
        canRevert: true,
        isAccepted: false
      });
    });

    it('should handle empty column mappings', () => {
      const changes = processColumnMappingsToChanges({});
      expect(changes).toHaveLength(0);
    });
  });

  describe('applySchemaAlignmentToData', () => {
    it('should apply column mappings to transform data', () => {
      const originalData = [
        ['name', 'age', 'city'],
        ['John', '30', 'New York'],
        ['Jane', '25', 'Boston']
      ];

      const columnMappings = {
        'name': 'full_name',
        'age': 'age_years'
      };

      const result = applySchemaAlignmentToData(originalData, columnMappings);

      expect(result[0]).toEqual(['full_name', 'age_years', 'city']);
      expect(result[1]).toEqual(['John', '30', 'New York']);
      expect(result[2]).toEqual(['Jane', '25', 'Boston']);
    });

    it('should handle empty data', () => {
      const result = applySchemaAlignmentToData([], {});
      expect(result).toEqual([]);
    });
  });

  describe('generateSchemaAlignmentSummary', () => {
    it('should generate transformation summary', () => {
      const originalData = [
        ['name', 'age', 'city'],
        ['John', '30', 'New York']
      ];

      const alignedData = [
        ['full_name', 'age_years', 'city'],
        ['John', '30', 'New York']
      ];

      const columnMappings = {
        'name': 'full_name',
        'age': 'age_years'
      };

      const summary = generateSchemaAlignmentSummary(originalData, alignedData, columnMappings);

      expect(summary.columnsRenamed).toBe(2);
      expect(summary.rowsOriginal).toBe(2);
      expect(summary.rowsAligned).toBe(2);
      expect(summary.columnMappings).toEqual(columnMappings);
    });
  });

  describe('parseSchemaAlignmentCsv', () => {
    it('should parse CSV string into 2D array', () => {
      const csvString = 'name,age,city\nJohn,30,"New York"\nJane,25,Boston';
      const result = parseSchemaAlignmentCsv(csvString);

      expect(result).toEqual([
        ['name', 'age', 'city'],
        ['John', '30', 'New York'],
        ['Jane', '25', 'Boston']
      ]);
    });

    it('should handle empty CSV string', () => {
      const result = parseSchemaAlignmentCsv('');
      expect(result).toEqual([]);
    });
  });

  describe('validateSchemaAlignmentData', () => {
    it('should validate complete schema alignment data', () => {
      const schemaAlignmentData: SchemaAlignmentResults = {
        schemaAlignmentResults: [
          {
            changeType: 'rename',
            originalColumn: 'name',
            newColumn: 'full_name',
            reason: 'Schema standardization',
            rowCountAffected: 1
          },
          {
            changeType: 'rename',
            originalColumn: 'age',
            newColumn: 'age_years',
            reason: 'Schema standardization',
            rowCountAffected: 1
          }
        ],
        summary: {
          jobId: 'test-job-123',
          version: 1,
          timestamp: new Date().toISOString(),
          originalDataCsv: 'name,age\nJohn,30',
          alignedDataCsv: 'full_name,age_years\nJohn,30',
          totalChanges: 2,
          columnsRenamed: 2,
          columnsAdded: 0,
          columnsRemoved: 0,
          rowsOriginal: 1,
          rowsAligned: 1
        }
      };

      const result = validateSchemaAlignmentData(schemaAlignmentData);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should identify missing data', () => {
      const schemaAlignmentData: SchemaAlignmentResults = {
        schemaAlignmentResults: [],
        summary: {
          jobId: 'test-job-123',
          version: 1,
          timestamp: new Date().toISOString(),
          originalDataCsv: '',
          alignedDataCsv: '',
          totalChanges: 0,
          columnsRenamed: 0,
          columnsAdded: 0,
          columnsRemoved: 0,
          rowsOriginal: 0,
          rowsAligned: 0
        }
      };

      const result = validateSchemaAlignmentData(schemaAlignmentData);

      expect(result.isValid).toBe(true); // No errors, just warnings
      expect(result.warnings.length).toBeGreaterThan(0);
    });
  });
});
