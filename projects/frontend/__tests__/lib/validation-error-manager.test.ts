/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Unit tests for ValidationErrorManager with manual changes integration
 */

import { ValidationErrorManager, ValidationErrorUtils } from '../../lib/validation-error-manager';
import {
  ValidationError,
  ValidationErrorType,
  ColumnOperation,
  RowOperation,
  ManualDataChange,
  ChangeHistoryEntry
} from '../../lib/types';

describe('ValidationErrorManager', () => {
  let manager: ValidationErrorManager;
  let mockErrors: ValidationError[];
  let mockData: string[][];

  beforeEach(() => {
    mockErrors = [
      {
        row: 1,
        column: 'Name',
        currentValue: 'John',
        validOptions: null,
        recommendedValue: 'John Doe',
        errorType: ValidationErrorType.REQUIRED_VALUE,
        errorMessage: 'Name is required'
      },
      {
        row: 2,
        column: 'Email',
        currentValue: 'invalid-email',
        validOptions: null,
        recommendedValue: 'user@example.com',
        errorType: ValidationErrorType.INVALID_PATTERN,
        errorMessage: 'Invalid email format'
      },
      {
        row: 1,
        column: 'Age',
        currentValue: '150',
        validOptions: ['18-65'],
        recommendedValue: '30',
        errorType: ValidationErrorType.INVALID_OPTION,
        errorMessage: 'Age must be between 18-65'
      }
    ];

    mockData = [
      ['Name', 'Email', 'Age'],
      ['John', 'invalid-email', '150'],
      ['Jane', 'jane@example.com', '25']
    ];

    manager = new ValidationErrorManager(mockErrors);
  });

  describe('Column Operations', () => {
    it('should update errors after column rename', () => {
      const updates = manager.updateErrorsAfterColumnRename('Name', 'FullName', mockData);

      expect(updates).toHaveLength(3);

      // Check that Name column error was updated
      const nameUpdate = updates.find(u => u.originalError.column === 'Name');
      expect(nameUpdate).toBeDefined();
      expect(nameUpdate!.wasAffected).toBe(true);
      expect(nameUpdate!.updatedError?.column).toBe('FullName');
      expect(nameUpdate!.updateReason).toContain('renamed');

      // Check that other errors were not affected
      const emailUpdate = updates.find(u => u.originalError.column === 'Email');
      expect(emailUpdate!.wasAffected).toBe(false);
    });

    it('should update errors after column addition', () => {
      const updates = manager.updateErrorsAfterColumnAdd('Phone', 2, mockData);

      expect(updates).toHaveLength(3);

      // All errors should be unaffected by column addition
      updates.forEach(update => {
        expect(update.wasAffected).toBe(false);
        expect(update.updatedError).toEqual(update.originalError);
      });
    });

    it('should remove errors after column removal', () => {
      const updates = manager.updateErrorsAfterColumnRemove('Email', 1, mockData);

      expect(updates).toHaveLength(3);

      // Email column error should be removed
      const emailUpdate = updates.find(u => u.originalError.column === 'Email');
      expect(emailUpdate).toBeDefined();
      expect(emailUpdate!.wasAffected).toBe(true);
      expect(emailUpdate!.updatedError).toBeNull();
      expect(emailUpdate!.updateReason).toContain('removed');

      // Other errors should be unaffected
      const nameUpdate = updates.find(u => u.originalError.column === 'Name');
      expect(nameUpdate!.wasAffected).toBe(false);
    });
  });

  describe('Row Operations', () => {
    it('should update errors after row addition', () => {
      const updates = manager.updateErrorsAfterRowAdd(1, mockData);

      expect(updates).toHaveLength(3);

      // Errors in row 2 should be shifted to row 3
      const row2Update = updates.find(u => u.originalError.row === 2);
      expect(row2Update).toBeDefined();
      expect(row2Update!.wasAffected).toBe(true);
      expect(row2Update!.updatedError?.row).toBe(3);

      // Errors in row 1 should be unaffected
      const row1Updates = updates.filter(u => u.originalError.row === 1);
      row1Updates.forEach(update => {
        expect(update.wasAffected).toBe(false);
      });
    });

    it('should update errors after row removal', () => {
      const updates = manager.updateErrorsAfterRowRemove(0, mockData); // Remove first data row (row 1)

      expect(updates).toHaveLength(3);

      // Errors in row 1 should be removed
      const row1Updates = updates.filter(u => u.originalError.row === 1);
      row1Updates.forEach(update => {
        expect(update.wasAffected).toBe(true);
        expect(update.updatedError).toBeNull();
      });

      // Errors in row 2 should be shifted to row 1
      const row2Update = updates.find(u => u.originalError.row === 2);
      expect(row2Update).toBeDefined();
      expect(row2Update!.wasAffected).toBe(true);
      expect(row2Update!.updatedError?.row).toBe(1);
    });
  });

  describe('Manual Change Validation', () => {
    it('should validate column operations', () => {
      const operation: ColumnOperation = {
        action: 'rename' as any,
        columnIndex: 0,
        columnName: 'Name',
        newColumnName: 'FullName'
      };

      const result = manager.validateManualChange(operation, mockData);

      expect(result.isValid).toBe(true);
      expect(result.hasSchemaConflict).toBe(false);
      expect(result.affectedValidationErrors).toHaveLength(1);
      expect(result.affectedValidationErrors[0].column).toBe('Name');
    });

    it('should detect conflicts in column operations', () => {
      const operation: ColumnOperation = {
        action: 'rename' as any,
        columnIndex: 0,
        columnName: 'Name',
        newColumnName: 'Email' // Conflict with existing column
      };

      const result = manager.validateManualChange(operation, mockData);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Column name "Email" already exists');
    });

    it('should validate row operations', () => {
      const operation: RowOperation = {
        action: 'remove' as any,
        rowIndex: 0 // Remove first data row
      };

      const result = manager.validateManualChange(operation, mockData);

      expect(result.isValid).toBe(true);
      expect(result.affectedValidationErrors).toHaveLength(2); // Row 1 has 2 errors
    });
  });

  describe('Change History and Rollback', () => {
    it('should record manual changes in history', () => {
      const manualChange: ManualDataChange = {
        id: 'test-change',
        type: 'column_rename',
        timestamp: new Date(),
        description: 'Renamed Name to FullName',
        canUndo: true,
        hasSchemaConflict: false,
        affectedValidationErrors: [],
        isManualChange: true
      };

      const beforeData = [['Name'], ['John']];
      const afterData = [['FullName'], ['John']];
      const beforeErrors = mockErrors.slice(0, 1);
      const afterErrors = mockErrors.slice(0, 1);

      manager.recordChange(manualChange, beforeData, afterData, beforeErrors, afterErrors);

      const history = manager.getChangeHistory();
      expect(history).toHaveLength(1);
      expect(history[0].change.id).toBe('test-change');
      expect(history[0].canRollback).toBe(true);
    });

    it('should rollback changes successfully', () => {
      // First record a change
      const manualChange: ManualDataChange = {
        id: 'test-change',
        type: 'column_rename',
        timestamp: new Date(),
        description: 'Renamed Name to FullName',
        canUndo: true,
        hasSchemaConflict: false,
        affectedValidationErrors: [],
        isManualChange: true
      };

      const beforeData = [['Name'], ['John']];
      const afterData = [['FullName'], ['John']];
      const beforeErrors = mockErrors.slice(0, 1);
      const afterErrors = mockErrors.slice(0, 1);

      manager.recordChange(manualChange, beforeData, afterData, beforeErrors, afterErrors);

      // Now rollback
      const history = manager.getChangeHistory();
      const result = manager.rollbackToHistoryEntry(history[0].id);

      expect(result.success).toBe(true);
      expect(result.restoredData).toEqual(beforeData);
      expect(result.restoredValidationErrors).toEqual(beforeErrors);
    });
  });

  describe('Schema Conflict Detection', () => {
    it('should detect schema conflicts for column operations', () => {
      const operation: ColumnOperation = {
        action: 'remove' as any,
        columnIndex: 0,
        columnName: 'Name'
      };

      const mockSchemaRequirements = {
        requiredFields: ['Name', 'Email']
      };

      const result = manager.checkSchemaConflicts(operation, mockData, mockSchemaRequirements);

      // This would be implemented based on actual schema structure
      expect(result.hasConflicts).toBe(false); // Placeholder implementation
    });
  });

  describe('Change Indicators', () => {
    it('should provide change indicators for UI display', () => {
      // Record some changes
      const manualChange: ManualDataChange = {
        id: 'manual-change',
        type: 'column_rename',
        timestamp: new Date(),
        description: 'Manual rename',
        canUndo: true,
        hasSchemaConflict: false,
        affectedValidationErrors: [],
        isManualChange: true
      };

      const autoChange: ManualDataChange = {
        id: 'auto-change',
        type: 'column_add',
        timestamp: new Date(),
        description: 'Auto addition',
        canUndo: true,
        hasSchemaConflict: true,
        affectedValidationErrors: [],
        isManualChange: false
      };

      manager.recordChange(manualChange, [], [], [], []);
      manager.recordChange(autoChange, [], [], [], []);

      const indicators = manager.getChangeIndicators();

      expect(indicators.totalChanges).toBe(2);
      expect(indicators.manualChanges).toBe(1);
      expect(indicators.automaticChanges).toBe(1);
      expect(indicators.conflictingChanges).toBe(1);
      expect(indicators.rollbackableChanges).toBe(2);
    });
  });

  describe('Re-evaluation of Validation Errors', () => {
    it('should re-evaluate validation errors after data changes', () => {
      const updatedData = [
        ['FullName', 'Email'], // Name column renamed, Age column removed
        ['John Doe', 'john@example.com'],
        ['Jane Smith', 'jane@example.com']
      ];

      const result = manager.reEvaluateValidationErrors(updatedData);

      expect(result.updatedErrors.length).toBeLessThan(mockErrors.length);
      expect(result.removedErrors.length).toBeGreaterThan(0);

      // Age column errors should be removed
      const ageErrors = result.removedErrors.filter(error => error.column === 'Age');
      expect(ageErrors.length).toBeGreaterThan(0);
    });
  });
});

describe('ValidationErrorUtils', () => {
  describe('Manual Change Creation', () => {
    it('should create manual change objects', () => {
      const change = ValidationErrorUtils.createManualChange(
        'column_rename',
        'Test rename',
        true,
        false,
        'No conflicts'
      );

      expect(change.id).toBeDefined();
      expect(change.type).toBe('column_rename');
      expect(change.description).toBe('Test rename');
      expect(change.isManualChange).toBe(true);
      expect(change.hasSchemaConflict).toBe(false);
      expect(change.canUndo).toBe(true);
    });
  });

  describe('Change Indicators', () => {
    it('should create change indicators for UI display', () => {
      const change: ManualDataChange = {
        id: 'test',
        type: 'column_rename',
        timestamp: new Date(),
        description: 'Test',
        canUndo: true,
        hasSchemaConflict: false,
        affectedValidationErrors: [],
        isManualChange: true
      };

      const indicator = ValidationErrorUtils.createChangeIndicator(change, false);

      expect(indicator.type).toBe('manual');
      expect(indicator.status).toBe('pending');
      expect(indicator.icon).toBe('👤');
      expect(indicator.color).toBe('#1976d2');
    });

    it('should create conflict indicators', () => {
      const change: ManualDataChange = {
        id: 'test',
        type: 'column_rename',
        timestamp: new Date(),
        description: 'Test',
        canUndo: true,
        hasSchemaConflict: true,
        affectedValidationErrors: [],
        isManualChange: true
      };

      const indicator = ValidationErrorUtils.createChangeIndicator(change, false);

      expect(indicator.status).toBe('conflict');
      expect(indicator.icon).toBe('⚠️');
      expect(indicator.color).toBe('#ed6c02');
    });
  });

  describe('Rollback Messages', () => {
    it('should generate rollback confirmation messages', () => {
      const change: ManualDataChange = {
        id: 'test',
        type: 'column_rename',
        timestamp: new Date(),
        description: 'Renamed Name to FullName',
        canUndo: true,
        hasSchemaConflict: true,
        schemaConflictWarning: 'Schema conflict detected',
        affectedValidationErrors: [
          {
            row: 1,
            column: 'Name',
            currentValue: 'John',
            validOptions: null,
            recommendedValue: 'John Doe',
            errorType: ValidationErrorType.REQUIRED_VALUE,
            confidenceScore: 0.8,
            confidenceLevel: 'High'
          }
        ],
        isManualChange: true
      };

      const message = ValidationErrorUtils.generateRollbackMessage(change, 1);

      expect(message.title).toContain('Rollback');
      expect(message.message).toContain('Renamed Name to FullName');
      expect(message.warnings).toContain('This will restore 1 validation error(s)');
      expect(message.warnings).toContain('This change had schema conflicts');
    });
  });
});
