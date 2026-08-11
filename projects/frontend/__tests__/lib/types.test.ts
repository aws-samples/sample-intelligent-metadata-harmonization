/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Type safety tests for metadata validation interfaces
 * These tests ensure interface compatibility and type correctness
 */

import {
  ValidationJobStatus,
  ValidationErrorType,
  ValidationJobResponse,
  ValidationStatusResponse,
  SchemaListResponse,
  SchemaInfo,
  ProgramSchemaInfo,
  ValidationResults,
  ValidationErrorDetail,
  ValidationResultsSummary,
  Change,
  ValidationError,
  AppState,
  ValidationResult,
  CSVParseConfig,
  CSVGenerateConfig,
  CSVStats,
  CSVValidationResult,
  // Post-Schema Alignment Data Sharing Types
  TransformationSummary,
  PostSchemaAlignmentData, // Keep for backward compatibility test
  SchemaAlignmentResults,
  SchemaAlignmentChangeDetail,
  SchemaAlignmentResultsSummary,
  CombinedResults,
  // DataViewType and DataViewState removed - using unified data view approach
  SchemaAlignmentChangeType,
  SchemaAlignmentChange,
  SchemaAlignmentChangeState,
  SchemaAlignmentChangeConfig
} from '../../lib/types';

describe('Type Definitions', () => {
  describe('Enums', () => {
    it('should have correct ValidationJobStatus values', () => {
      expect(ValidationJobStatus.PENDING).toBe('pending');
      expect(ValidationJobStatus.PROCESSING).toBe('processing');
      expect(ValidationJobStatus.COMPLETED).toBe('completed');
      expect(ValidationJobStatus.FAILED).toBe('failed');
    });

    it('should have correct ValidationErrorType values', () => {
      expect(ValidationErrorType.REQUIRED_VALUE).toBe('REQUIRED_VALUE');
      expect(ValidationErrorType.INVALID_OPTION).toBe('INVALID_OPTION');
    });
  });

  describe('API Response Types', () => {
    it('should accept valid ValidationJobResponse', () => {
      const successResponse: ValidationJobResponse = {
        success: true,
        jobId: 'job-123'
      };

      const errorResponse: ValidationJobResponse = {
        success: false,
        error: 'Something went wrong'
      };

      expect(successResponse.success).toBe(true);
      expect(successResponse.jobId).toBe('job-123');
      expect(errorResponse.success).toBe(false);
      expect(errorResponse.error).toBe('Something went wrong');
    });

    it('should accept valid ValidationStatusResponse', () => {
      const response: ValidationStatusResponse = {
        success: true,
        jobId: 'job-123',
        userId: 'user-456',
        coreSchemaId: 'core-schema-789',
        programSchemaId: 'program-schema-012',
        status: ValidationJobStatus.COMPLETED,
        createdAt: '2024-01-01T00:00:00Z',
        completedAt: '2024-01-01T01:00:00Z',
        currentVersion: 1,
        latestResults: null
      };

      expect(response.success).toBe(true);
      expect(response.status).toBe(ValidationJobStatus.COMPLETED);
    });

    it('should accept ValidationStatusResponse with schema alignment results', () => {
      const response: ValidationStatusResponse = {
        success: true,
        jobId: 'job-123',
        status: ValidationJobStatus.COMPLETED,
        latestResults: {
          validationResults: {
            validationResults: [],
            summary: {
              totalRows: 2,
              totalErrors: 0,
              errorTypes: {
                [ValidationErrorType.INVALID_OPTION]: 0,
                [ValidationErrorType.REQUIRED_VALUE]: 0
              }
            }
          },
          schemaAlignmentResults: {
            schemaAlignmentResults: [
              {
                changeType: 'rename',
                originalColumn: 'name',
                newColumn: 'full_name',
                reason: 'Schema alignment requirement',
                rowCountAffected: 2
              },
              {
                changeType: 'rename',
                originalColumn: 'age',
                newColumn: 'age_years',
                reason: 'Schema alignment requirement',
                rowCountAffected: 2
              }
            ],
            summary: {
              jobId: 'job-123',
              version: 1,
              timestamp: '2024-01-01T12:00:00Z',
              originalDataCsv: 'name,age\nJohn,25',
              alignedDataCsv: 'full_name,age_years\nJohn,25',
              totalChanges: 2,
              columnsRenamed: 2,
              columnsAdded: 0,
              columnsRemoved: 0,
              rowsOriginal: 2,
              rowsAligned: 2
            }
          }
        }
      };

      expect(response.success).toBe(true);
      expect(response.latestResults?.schemaAlignmentResults).toBeDefined();
      expect(response.latestResults?.schemaAlignmentResults?.summary.originalDataCsv).toContain('name,age');
      expect(response.latestResults?.schemaAlignmentResults?.summary.alignedDataCsv).toContain('full_name,age_years');
      expect(response.latestResults?.schemaAlignmentResults?.summary.columnsRenamed).toBe(2);
      expect(response.latestResults?.schemaAlignmentResults?.schemaAlignmentResults).toHaveLength(2);
    });

    it('should accept valid SchemaListResponse', () => {
      const response: SchemaListResponse = {
        success: true,
        schemas: [
          {
            coreSchemaId: 'schema-1',
            name: 'Test Schema',
            coreSchemaPath: '/path/to/schema',
            coreSchemaS3Bucket: 'test-bucket',
            programSchemas: []
          }
        ]
      };

      expect(response.success).toBe(true);
      expect(response.schemas).toHaveLength(1);
    });
  });

  describe('Schema Types', () => {
    it('should accept valid SchemaInfo', () => {
      const schema: SchemaInfo = {
        coreSchemaId: 'core-123',
        name: 'Test Schema',
        coreSchemaPath: '/path/to/core.json',
        coreSchemaS3Bucket: 'core-bucket',
        programSchemas: [
          {
            programName: 'Test Program',
            s3Location: '/path/to/program.json',
            s3Bucket: 'program-bucket',
            programSchemaId: 'program-123'
          }
        ]
      };

      expect(schema.coreSchemaId).toBe('core-123');
      expect(schema.programSchemas).toHaveLength(1);
    });

    it('should accept valid ProgramSchemaInfo', () => {
      const programSchema: ProgramSchemaInfo = {
        programName: 'Test Program',
        s3Location: '/path/to/program.json',
        s3Bucket: 'program-bucket',
        programSchemaId: 'program-123'
      };

      expect(programSchema.programName).toBe('Test Program');
      expect(programSchema.programSchemaId).toBe('program-123');
    });
  });

  describe('Validation Result Types', () => {
    it('should accept valid ValidationResults', () => {
      const results: ValidationResults = {
        validationResults: [
          {
            row: 1,
            column: 'Name',
            currentValue: 'invalid',
            validOptions: ['option1', 'option2'],
            recommendedValue: 'option1',
            errorType: ValidationErrorType.INVALID_OPTION
          }
        ],
        summary: {
          totalRows: 100,
          totalErrors: 1,
          errorTypes: {
            [ValidationErrorType.INVALID_OPTION]: 1,
            [ValidationErrorType.REQUIRED_VALUE]: 0
          }
        }
      };

      expect(results.validationResults).toHaveLength(1);
      expect(results.summary.totalErrors).toBe(1);
    });

    it('should accept valid ValidationErrorDetail', () => {
      const error: ValidationErrorDetail = {
        row: 5,
        column: 'Age',
        currentValue: 'invalid-age',
        validOptions: null,
        recommendedValue: '25',
        errorType: ValidationErrorType.REQUIRED_VALUE
      };

      expect(error.row).toBe(5);
      expect(error.column).toBe('Age');
      expect(error.errorType).toBe(ValidationErrorType.REQUIRED_VALUE);
      expect(error.errorMessage).toBeUndefined();
      expect(error.schemaFieldName).toBeUndefined();
    });

    it('should accept ValidationErrorDetail with custom error messages', () => {
      const error: ValidationErrorDetail = {
        row: 2,
        column: 'library_strategy',
        currentValue: 'Invalid',
        validOptions: ['Amplicon'],
        recommendedValue: 'Amplicon',
        errorType: ValidationErrorType.INVALID_OPTION,
        errorMessage: 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]',
        schemaFieldName: 'library_strategy'
      };

      expect(error.row).toBe(2);
      expect(error.column).toBe('library_strategy');
      expect(error.errorType).toBe(ValidationErrorType.INVALID_OPTION);
      expect(error.errorMessage).toBe('library_strategy is a required field. Valid input(s) are: ["Amplicon"]');
      expect(error.schemaFieldName).toBe('library_strategy');
    });

    it('should accept ValidationErrorDetail with partial custom fields', () => {
      const error: ValidationErrorDetail = {
        row: 1,
        column: 'sequence_id',
        currentValue: 'invalid-format',
        validOptions: null,
        recommendedValue: null,
        errorType: ValidationErrorType.INVALID_PATTERN,
        errorMessage: 'sequence_id is a required field that must follow the proper formatting'
        // schemaFieldName is optional and not provided
      };

      expect(error.errorMessage).toBe('sequence_id is a required field that must follow the proper formatting');
      expect(error.schemaFieldName).toBeUndefined();
    });

    it('should accept valid ValidationResultsSummary', () => {
      const summary: ValidationResultsSummary = {
        totalRows: 50,
        totalErrors: 3,
        errorTypes: {
          [ValidationErrorType.REQUIRED_VALUE]: 2,
          [ValidationErrorType.INVALID_OPTION]: 1
        }
      };

      expect(summary.totalRows).toBe(50);
      expect(summary.totalErrors).toBe(3);
      expect(summary.errorTypes[ValidationErrorType.REQUIRED_VALUE]).toBe(2);
    });
  });

  describe('UI Component Types', () => {
    it('should accept valid Change', () => {
      const change: Change = {
        row: 2,
        column: 1,
        oldValue: 'old',
        newValue: 'new',
        timestamp: new Date('2024-01-01T12:00:00Z')
      };

      expect(change.row).toBe(2);
      expect(change.column).toBe(1);
      expect(change.oldValue).toBe('old');
      expect(change.newValue).toBe('new');
      expect(change.timestamp).toBeInstanceOf(Date);
    });

    it('should accept valid ValidationError (extends ValidationErrorDetail)', () => {
      const error: ValidationError = {
        row: 3,
        column: 'Email',
        currentValue: 'invalid-email',
        validOptions: null,
        recommendedValue: 'user@example.com',
        errorType: ValidationErrorType.INVALID_OPTION
      };

      // Should work as ValidationErrorDetail too
      const errorDetail: ValidationErrorDetail = error;

      expect(error.row).toBe(3);
      expect(errorDetail.column).toBe('Email');
    });

    it('should accept ValidationError with custom error messages', () => {
      const error: ValidationError = {
        row: 1,
        column: 'submitter_state',
        currentValue: 'XX',
        validOptions: ['AK', 'AL', 'AZ', 'AR', 'CA'],
        recommendedValue: 'CA',
        errorType: ValidationErrorType.INVALID_OPTION,
        errorMessage: 'submitter_state is a required field and must be formatted as the two-letter State abbreviation',
        schemaFieldName: 'submitter_state'
      };

      // Should work as ValidationErrorDetail too
      const errorDetail: ValidationErrorDetail = error;

      expect(error.row).toBe(1);
      expect(error.errorMessage).toBe('submitter_state is a required field and must be formatted as the two-letter State abbreviation');
      expect(error.schemaFieldName).toBe('submitter_state');
      expect(errorDetail.errorMessage).toBe('submitter_state is a required field and must be formatted as the two-letter State abbreviation');
      expect(errorDetail.schemaFieldName).toBe('submitter_state');
    });

    it('should accept valid AppState', () => {
      const uploadState: AppState = {
        stage: 'upload',
        csvData: null,
        validationErrors: null
      };

      const editState: AppState = {
        stage: 'edit',
        csvData: [['Name', 'Age'], ['John', '25']],
        validationErrors: [
          {
            row: 1,
            column: 'Name',
            currentValue: 'John',
            validOptions: null,
            recommendedValue: 'John Doe',
            errorType: ValidationErrorType.INVALID_OPTION
          }
        ]
      };

      const completeState: AppState = {
        stage: 'complete',
        csvData: [['Name', 'Age'], ['John', '25']],
        validationErrors: []
      };

      expect(uploadState.stage).toBe('upload');
      expect(editState.stage).toBe('edit');
      expect(completeState.stage).toBe('complete');
      expect(editState.csvData).toHaveLength(2);
      expect(editState.validationErrors).toHaveLength(1);
    });

    it('should accept valid ValidationResult', () => {
      const successResult: ValidationResult = {
        success: true,
        errors: [],
        message: 'Validation passed'
      };

      const errorResult: ValidationResult = {
        success: false,
        errors: [
          {
            row: 1,
            column: 'Name',
            currentValue: 'invalid',
            validOptions: ['valid1', 'valid2'],
            recommendedValue: 'valid1',
            errorType: ValidationErrorType.INVALID_OPTION
          }
        ]
      };

      expect(successResult.success).toBe(true);
      expect(successResult.errors).toHaveLength(0);
      expect(errorResult.success).toBe(false);
      expect(errorResult.errors).toHaveLength(1);
    });
  });

  describe('CSV Configuration Types', () => {
    it('should accept valid CSVParseConfig', () => {
      const config: CSVParseConfig = {
        delimiter: ';',
        quote: "'",
        skipEmptyLines: false
      };

      const defaultConfig: CSVParseConfig = {};

      expect(config.delimiter).toBe(';');
      expect(config.quote).toBe("'");
      expect(config.skipEmptyLines).toBe(false);
      expect(defaultConfig).toEqual({});
    });

    it('should accept valid CSVGenerateConfig', () => {
      const config: CSVGenerateConfig = {
        delimiter: '|',
        quote: '"',
        forceQuotes: true
      };

      expect(config.delimiter).toBe('|');
      expect(config.forceQuotes).toBe(true);
    });

    it('should accept valid CSVStats', () => {
      const stats: CSVStats = {
        totalRows: 100,
        totalColumns: 5,
        emptyRows: 2,
        emptyCells: 10,
        totalCells: 500
      };

      expect(stats.totalRows).toBe(100);
      expect(stats.totalColumns).toBe(5);
      expect(stats.emptyRows).toBe(2);
      expect(stats.emptyCells).toBe(10);
      expect(stats.totalCells).toBe(500);
    });

    it('should accept valid CSVValidationResult', () => {
      const validResult: CSVValidationResult = {
        isValid: true,
        errors: [],
        warnings: ['Column 3 has no name']
      };

      const invalidResult: CSVValidationResult = {
        isValid: false,
        errors: ['CSV data is empty', 'Header row is missing'],
        warnings: []
      };

      expect(validResult.isValid).toBe(true);
      expect(validResult.errors).toHaveLength(0);
      expect(validResult.warnings).toHaveLength(1);

      expect(invalidResult.isValid).toBe(false);
      expect(invalidResult.errors).toHaveLength(2);
      expect(invalidResult.warnings).toHaveLength(0);
    });
  });

  describe('Post-Schema Alignment Data Sharing Types', () => {
    describe('Enums', () => {
      // DataViewType tests removed - no longer using toggle functionality

      it('should have correct SchemaAlignmentChangeType values', () => {
        expect(SchemaAlignmentChangeType.COLUMN_RENAMED).toBe('column_renamed');
        expect(SchemaAlignmentChangeType.COLUMN_ADDED).toBe('column_added');
        expect(SchemaAlignmentChangeType.COLUMN_REMOVED).toBe('column_removed');
      });
    });

    describe('TransformationSummary', () => {
      it('should accept valid TransformationSummary', () => {
        const summary: TransformationSummary = {
          columnsRenamed: 2,
          columnsAdded: 1,
          columnsRemoved: 0,
          rowsOriginal: 100,
          rowsAligned: 100,
          columnMappings: {
            'old_name': 'new_name',
            'another_old': 'another_new'
          },
          addedColumns: ['new_column'],
          removedColumns: []
        };

        expect(summary.columnsRenamed).toBe(2);
        expect(summary.columnsAdded).toBe(1);
        expect(summary.columnsRemoved).toBe(0);
        expect(summary.rowsOriginal).toBe(100);
        expect(summary.rowsAligned).toBe(100);
        expect(Object.keys(summary.columnMappings)).toHaveLength(2);
        expect(summary.addedColumns).toHaveLength(1);
        expect(summary.removedColumns).toHaveLength(0);
      });
    });

    describe('PostSchemaAlignmentData', () => {
      it('should accept valid PostSchemaAlignmentData with all fields', () => {
        const data: PostSchemaAlignmentData = {
          originalDataCsv: 'name,age\nJohn,25\nJane,30',
          alignedDataCsv: 'full_name,age_years\nJohn,25\nJane,30',
          columnMappings: {
            'name': 'full_name',
            'age': 'age_years'
          },
          transformationSummary: {
            columnsRenamed: 2,
            columnsAdded: 0,
            columnsRemoved: 0,
            rowsOriginal: 3,
            rowsAligned: 3,
            columnMappings: { 'name': 'full_name', 'age': 'age_years' },
            addedColumns: [],
            removedColumns: []
          }
        };

        expect(data.originalDataCsv).toContain('name,age');
        expect(data.alignedDataCsv).toContain('full_name,age_years');
        expect(data.columnMappings).toEqual({ 'name': 'full_name', 'age': 'age_years' });
        expect(data.transformationSummary?.columnsRenamed).toBe(2);
      });

      it('should accept minimal PostSchemaAlignmentData', () => {
        const minimalData: PostSchemaAlignmentData = {};

        expect(minimalData.originalDataCsv).toBeUndefined();
        expect(minimalData.alignedDataCsv).toBeUndefined();
        expect(minimalData.columnMappings).toBeUndefined();
        expect(minimalData.transformationSummary).toBeUndefined();
      });
    });

    describe('SchemaAlignmentResults', () => {
      it('should accept valid SchemaAlignmentChangeDetail', () => {
        const changeDetail: SchemaAlignmentChangeDetail = {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'new_name',
          reason: 'Schema alignment requirement',
          rowCountAffected: 100
        };

        expect(changeDetail.changeType).toBe('rename');
        expect(changeDetail.originalColumn).toBe('old_name');
        expect(changeDetail.newColumn).toBe('new_name');
        expect(changeDetail.reason).toBe('Schema alignment requirement');
        expect(changeDetail.rowCountAffected).toBe(100);
      });

      it('should accept minimal SchemaAlignmentChangeDetail', () => {
        const minimalChange: SchemaAlignmentChangeDetail = {
          changeType: 'add'
        };

        expect(minimalChange.changeType).toBe('add');
        expect(minimalChange.originalColumn).toBeUndefined();
        expect(minimalChange.newColumn).toBeUndefined();
        expect(minimalChange.reason).toBeUndefined();
        expect(minimalChange.rowCountAffected).toBeUndefined();
      });

      it('should accept valid SchemaAlignmentResultsSummary', () => {
        const summary: SchemaAlignmentResultsSummary = {
          jobId: 'job-123',
          version: 1,
          timestamp: '2024-01-01T12:00:00Z',
          originalDataCsv: 'name,age\nJohn,25',
          alignedDataCsv: 'full_name,age_years\nJohn,25',
          totalChanges: 2,
          columnsRenamed: 2,
          columnsAdded: 0,
          columnsRemoved: 0,
          rowsOriginal: 2,
          rowsAligned: 2
        };

        expect(summary.jobId).toBe('job-123');
        expect(summary.version).toBe(1);
        expect(summary.timestamp).toBe('2024-01-01T12:00:00Z');
        expect(summary.originalDataCsv).toContain('name,age');
        expect(summary.alignedDataCsv).toContain('full_name,age_years');
        expect(summary.totalChanges).toBe(2);
        expect(summary.columnsRenamed).toBe(2);
        expect(summary.columnsAdded).toBe(0);
        expect(summary.columnsRemoved).toBe(0);
        expect(summary.rowsOriginal).toBe(2);
        expect(summary.rowsAligned).toBe(2);
      });

      it('should accept valid SchemaAlignmentResults', () => {
        const results: SchemaAlignmentResults = {
          schemaAlignmentResults: [
            {
              changeType: 'rename',
              originalColumn: 'name',
              newColumn: 'full_name',
              reason: 'Schema requires full_name field',
              rowCountAffected: 100
            },
            {
              changeType: 'add',
              newColumn: 'required_field',
              reason: 'Schema requires this field',
              rowCountAffected: 100
            }
          ],
          summary: {
            jobId: 'job-123',
            version: 1,
            timestamp: '2024-01-01T12:00:00Z',
            originalDataCsv: 'name\nJohn',
            alignedDataCsv: 'full_name,required_field\nJohn,',
            totalChanges: 2,
            columnsRenamed: 1,
            columnsAdded: 1,
            columnsRemoved: 0,
            rowsOriginal: 2,
            rowsAligned: 2
          }
        };

        expect(results.schemaAlignmentResults).toHaveLength(2);
        expect(results.schemaAlignmentResults[0].changeType).toBe('rename');
        expect(results.schemaAlignmentResults[1].changeType).toBe('add');
        expect(results.summary.totalChanges).toBe(2);
        expect(results.summary.columnsRenamed).toBe(1);
        expect(results.summary.columnsAdded).toBe(1);
      });

      it('should accept empty SchemaAlignmentResults', () => {
        const emptyResults: SchemaAlignmentResults = {
          schemaAlignmentResults: [],
          summary: {
            jobId: 'job-123',
            version: 1,
            timestamp: '2024-01-01T12:00:00Z',
            originalDataCsv: 'name\nJohn',
            alignedDataCsv: 'name\nJohn',
            totalChanges: 0,
            columnsRenamed: 0,
            columnsAdded: 0,
            columnsRemoved: 0,
            rowsOriginal: 2,
            rowsAligned: 2
          }
        };

        expect(emptyResults.schemaAlignmentResults).toHaveLength(0);
        expect(emptyResults.summary.totalChanges).toBe(0);
      });
    });

    describe('CombinedResults', () => {
      it('should accept valid CombinedResults with both validation and schema alignment results', () => {
        const combinedResults: CombinedResults = {
          validationResults: {
            validationResults: [
              {
                row: 1,
                column: 'name',
                currentValue: 'invalid',
                validOptions: ['valid1', 'valid2'],
                recommendedValue: 'valid1',
                errorType: ValidationErrorType.INVALID_OPTION
              }
            ],
            summary: {
              totalRows: 2,
              totalErrors: 1,
              errorTypes: {
                [ValidationErrorType.INVALID_OPTION]: 1,
                [ValidationErrorType.REQUIRED_VALUE]: 0
              }
            }
          },
          schemaAlignmentResults: {
            schemaAlignmentResults: [
              {
                changeType: 'rename',
                originalColumn: 'name',
                newColumn: 'full_name',
                reason: 'Schema alignment',
                rowCountAffected: 2
              }
            ],
            summary: {
              jobId: 'job-123',
              version: 1,
              timestamp: '2024-01-01T12:00:00Z',
              originalDataCsv: 'name\nJohn',
              alignedDataCsv: 'full_name\nJohn',
              totalChanges: 1,
              columnsRenamed: 1,
              columnsAdded: 0,
              columnsRemoved: 0,
              rowsOriginal: 2,
              rowsAligned: 2
            }
          }
        };

        expect(combinedResults.validationResults).toBeDefined();
        expect(combinedResults.schemaAlignmentResults).toBeDefined();
        expect(combinedResults.validationResults?.validationResults).toHaveLength(1);
        expect(combinedResults.schemaAlignmentResults?.schemaAlignmentResults).toHaveLength(1);
      });

      it('should accept CombinedResults with only validation results', () => {
        const validationOnlyResults: CombinedResults = {
          validationResults: {
            validationResults: [],
            summary: {
              totalRows: 0,
              totalErrors: 0,
              errorTypes: {
                [ValidationErrorType.INVALID_OPTION]: 0,
                [ValidationErrorType.REQUIRED_VALUE]: 0
              }
            }
          },
          schemaAlignmentResults: null
        };

        expect(validationOnlyResults.validationResults).toBeDefined();
        expect(validationOnlyResults.schemaAlignmentResults).toBeNull();
      });

      it('should accept minimal CombinedResults', () => {
        const minimalResults: CombinedResults = {};

        expect(minimalResults.validationResults).toBeUndefined();
        expect(minimalResults.schemaAlignmentResults).toBeUndefined();
      });
    });

    // DataViewState tests removed - no longer using toggle functionality

    describe('SchemaAlignmentChange', () => {
      it('should accept valid column rename change', () => {
        const change: SchemaAlignmentChange = {
          id: 'change-1',
          type: SchemaAlignmentChangeType.COLUMN_RENAMED,
          originalColumn: 'old_name',
          alignedColumn: 'new_name',
          description: 'Column "old_name" was renamed to "new_name"',
          canRevert: true,
          isAccepted: false
        };

        expect(change.id).toBe('change-1');
        expect(change.type).toBe(SchemaAlignmentChangeType.COLUMN_RENAMED);
        expect(change.originalColumn).toBe('old_name');
        expect(change.alignedColumn).toBe('new_name');
        expect(change.canRevert).toBe(true);
        expect(change.isAccepted).toBe(false);
      });

      it('should accept valid column addition change', () => {
        const change: SchemaAlignmentChange = {
          id: 'change-2',
          type: SchemaAlignmentChangeType.COLUMN_ADDED,
          alignedColumn: 'new_required_column',
          description: 'Column "new_required_column" was added to match schema',
          canRevert: false,
          isAccepted: true
        };

        expect(change.type).toBe(SchemaAlignmentChangeType.COLUMN_ADDED);
        expect(change.originalColumn).toBeUndefined();
        expect(change.alignedColumn).toBe('new_required_column');
        expect(change.canRevert).toBe(false);
        expect(change.isAccepted).toBe(true);
      });

      it('should accept valid column removal change', () => {
        const change: SchemaAlignmentChange = {
          id: 'change-3',
          type: SchemaAlignmentChangeType.COLUMN_REMOVED,
          originalColumn: 'deprecated_column',
          description: 'Column "deprecated_column" was removed during alignment',
          canRevert: true,
          isAccepted: false
        };

        expect(change.type).toBe(SchemaAlignmentChangeType.COLUMN_REMOVED);
        expect(change.originalColumn).toBe('deprecated_column');
        expect(change.alignedColumn).toBeUndefined();
        expect(change.canRevert).toBe(true);
        expect(change.isAccepted).toBe(false);
      });
    });

    describe('SchemaAlignmentChangeState', () => {
      it('should accept valid SchemaAlignmentChangeState', () => {
        const state: SchemaAlignmentChangeState = {
          changes: [
            {
              id: 'change-1',
              type: SchemaAlignmentChangeType.COLUMN_RENAMED,
              originalColumn: 'old_name',
              alignedColumn: 'new_name',
              description: 'Column renamed',
              canRevert: true,
              isAccepted: true
            },
            {
              id: 'change-2',
              type: SchemaAlignmentChangeType.COLUMN_ADDED,
              alignedColumn: 'required_column',
              description: 'Column added',
              canRevert: false,
              isAccepted: true
            }
          ],
          acceptedCount: 2,
          revertableCount: 1,
          isBulkOperationInProgress: false
        };

        expect(state.changes).toHaveLength(2);
        expect(state.acceptedCount).toBe(2);
        expect(state.revertableCount).toBe(1);
        expect(state.isBulkOperationInProgress).toBe(false);
      });
    });

    describe('SchemaAlignmentChangeConfig', () => {
      it('should accept valid SchemaAlignmentChangeConfig', () => {
        const config: SchemaAlignmentChangeConfig = {
          autoAcceptRequired: true,
          showBulkConfirmations: false,
          maxDisplayedChanges: 50
        };

        expect(config.autoAcceptRequired).toBe(true);
        expect(config.showBulkConfirmations).toBe(false);
        expect(config.maxDisplayedChanges).toBe(50);
      });
    });
  });

  describe('Type Compatibility', () => {
    it('should allow ValidationError to be used as ValidationErrorDetail', () => {
      const validationError: ValidationError = {
        row: 1,
        column: 'Test',
        currentValue: 'test',
        validOptions: null,
        recommendedValue: 'corrected',
        errorType: ValidationErrorType.REQUIRED_VALUE
      };

      // Should be assignable to ValidationErrorDetail
      const errorDetail: ValidationErrorDetail = validationError;

      expect(errorDetail.row).toBe(1);
      expect(errorDetail.column).toBe('Test');
    });

    it('should allow enum values to be used as strings', () => {
      const status: string = ValidationJobStatus.COMPLETED;
      const errorType: string = ValidationErrorType.INVALID_OPTION;
      // dataView removed - no longer using toggle functionality
      const changeType: string = SchemaAlignmentChangeType.COLUMN_RENAMED;

      expect(status).toBe('completed');
      expect(errorType).toBe('INVALID_OPTION');
      expect(changeType).toBe('column_renamed');
    });

    it('should support optional properties correctly', () => {
      // Minimal ValidationJobResponse
      const minimalResponse: ValidationJobResponse = {
        success: false
      };

      // Minimal ValidationStatusResponse
      const minimalStatus: ValidationStatusResponse = {
        success: true
      };

      // Minimal SchemaListResponse
      const minimalSchemas: SchemaListResponse = {
        success: true
      };

      expect(minimalResponse.success).toBe(false);
      expect(minimalResponse.jobId).toBeUndefined();
      expect(minimalResponse.error).toBeUndefined();

      expect(minimalStatus.success).toBe(true);
      expect(minimalSchemas.success).toBe(true);
    });

    // DataViewState view switching test removed - no longer using toggle functionality

    it('should maintain backward compatibility for ValidationStatusResponse', () => {
      // Existing code should still work without schema alignment results
      const legacyResponse: ValidationStatusResponse = {
        success: true,
        jobId: 'job-123',
        status: ValidationJobStatus.COMPLETED,
        latestResults: {
          validationResults: {
            validationResults: [],
            summary: {
              totalRows: 0,
              totalErrors: 0,
              errorTypes: {
                [ValidationErrorType.REQUIRED_VALUE]: 0,
                [ValidationErrorType.INVALID_OPTION]: 0
              }
            }
          },
          schemaAlignmentResults: null
        }
      };

      // Should work without schema alignment results
      expect(legacyResponse.success).toBe(true);
      expect(legacyResponse.latestResults?.schemaAlignmentResults).toBeNull();
      expect(legacyResponse.latestResults?.validationResults).toBeDefined();
    });
  });
});
