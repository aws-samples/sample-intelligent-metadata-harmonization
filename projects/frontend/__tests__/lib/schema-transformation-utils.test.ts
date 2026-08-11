/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import {
  validateSchemaChange,
  generateChangeId,
  orderChangesForExecution,
  detectChangeConflicts,
  generateTransformationPreview,
  withErrorHandling,
  TransformationError,
  createProgressTracker,
  updateProgress,
  isDestructiveChange,
  hasDestructiveChanges,
  formatChangeDescription,
  createTransformationOperation,
  executeSingleTransformation,
  executeBulkTransformations,
  revertSingleTransformation,
  revertBulkTransformations,
  updateColumnsAfterChange,
  TransformationCallbacks,
  TransformationState
} from '../../lib/schema-transformation-utils';
import { SchemaAlignmentChangeDetail } from '../../lib/types';

describe('Schema Transformation Utils', () => {
  const mockChanges: SchemaAlignmentChangeDetail[] = [
    {
      changeType: 'rename',
      originalColumn: 'old_name',
      newColumn: 'new_name',
      reason: 'Schema alignment',
      rowCountAffected: 100
    },
    {
      changeType: 'add',
      newColumn: 'additional_field',
      reason: 'Required field missing',
      rowCountAffected: 100
    },
    {
      changeType: 'remove',
      originalColumn: 'deprecated_field',
      reason: 'Field no longer needed',
      rowCountAffected: 100
    }
  ];

  describe('validateSchemaChange', () => {
    const currentColumns = ['existing_col', 'old_name', 'another_col'];

    it('should validate rename operations correctly', () => {
      const validRename = mockChanges[0];
      const result = validateSchemaChange(validRename, currentColumns);
      expect(result.isValid).toBe(true);
    });

    it('should reject rename to existing column', () => {
      const invalidRename = {
        ...mockChanges[0],
        newColumn: 'existing_col'
      };
      const result = validateSchemaChange(invalidRename, currentColumns);
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('already exists');
    });

    it('should validate add operations correctly', () => {
      const validAdd = mockChanges[1];
      const result = validateSchemaChange(validAdd, currentColumns);
      expect(result.isValid).toBe(true);
    });

    it('should reject add of existing column', () => {
      const invalidAdd = {
        ...mockChanges[1],
        newColumn: 'existing_col'
      };
      const result = validateSchemaChange(invalidAdd, currentColumns);
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('already exists');
    });

    it('should validate remove operations correctly', () => {
      const validRemove = mockChanges[2];
      const result = validateSchemaChange(validRemove, ['col1', 'deprecated_field', 'col3']);
      expect(result.isValid).toBe(true);
    });

    it('should reject remove of non-existent column', () => {
      const invalidRemove = {
        ...mockChanges[2],
        originalColumn: 'non_existent'
      };
      const result = validateSchemaChange(invalidRemove, currentColumns);
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('not found');
    });

    it('should reject remove of last column', () => {
      const validRemove = mockChanges[2];
      const result = validateSchemaChange(validRemove, ['deprecated_field']); // Only one column
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('Cannot remove last column');
    });
  });

  describe('generateChangeId', () => {
    it('should generate consistent IDs', () => {
      const change = mockChanges[0];
      const id1 = generateChangeId(change, 0);
      const id2 = generateChangeId(change, 0);
      expect(id1).toBe(id2);
      expect(id1).toContain('rename');
      expect(id1).toContain('old_name');
    });

    it('should generate unique IDs for different changes', () => {
      const id1 = generateChangeId(mockChanges[0], 0);
      const id2 = generateChangeId(mockChanges[1], 1);
      expect(id1).not.toBe(id2);
    });
  });

  describe('createTransformationOperation', () => {
    const mockCallbacks: TransformationCallbacks = {
      onApplyColumnRename: jest.fn(),
      onApplyColumnAddition: jest.fn(),
      onApplyColumnRemoval: jest.fn(),
      onRevertChange: jest.fn()
    };

    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('should create rename operation', () => {
      const operation = createTransformationOperation(mockChanges[0], mockCallbacks);
      expect(operation.changeType).toBe('rename');
      expect(operation.originalColumn).toBe('old_name');
      expect(operation.newColumn).toBe('new_name');
    });

    it('should execute rename operation', () => {
      const operation = createTransformationOperation(mockChanges[0], mockCallbacks);
      operation.execute();
      expect(mockCallbacks.onApplyColumnRename).toHaveBeenCalledWith('old_name', 'new_name');
    });

    it('should execute add operation', () => {
      const operation = createTransformationOperation(mockChanges[1], mockCallbacks);
      operation.execute();
      expect(mockCallbacks.onApplyColumnAddition).toHaveBeenCalledWith('additional_field');
    });

    it('should execute remove operation', () => {
      const operation = createTransformationOperation(mockChanges[2], mockCallbacks);
      operation.execute();
      expect(mockCallbacks.onApplyColumnRemoval).toHaveBeenCalledWith('deprecated_field');
    });

    it('should throw error for missing callback', () => {
      const operation = createTransformationOperation(mockChanges[0], {});
      expect(() => operation.execute()).toThrow(TransformationError);
    });
  });

  describe('executeSingleTransformation', () => {
    const mockCallbacks: TransformationCallbacks = {
      onApplyColumnRename: jest.fn(),
      onApplyColumnAddition: jest.fn(),
      onApplyColumnRemoval: jest.fn(),
      onRevertChange: jest.fn()
    };

    const mockState: TransformationState = {
      appliedChangeIds: new Set(),
      markAsApplied: jest.fn(),
      markAsReverted: jest.fn(),
      isApplied: jest.fn(() => false)
    };

    const currentColumns = ['existing_col', 'old_name', 'another_col'];

    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('should execute valid transformation successfully', async () => {
      const result = await executeSingleTransformation(
        mockChanges[0],
        0,
        currentColumns,
        mockCallbacks,
        mockState
      );

      expect(result.success).toBe(true);
      expect(result.error).toBeUndefined();
      expect(mockCallbacks.onApplyColumnRename).toHaveBeenCalled();
      expect(mockState.markAsApplied).toHaveBeenCalled();
    });

    it('should fail for invalid transformation', async () => {
      const invalidChange = {
        ...mockChanges[0],
        newColumn: 'existing_col' // Conflicts with existing column
      };

      const result = await executeSingleTransformation(
        invalidChange,
        0,
        currentColumns,
        mockCallbacks,
        mockState
      );

      expect(result.success).toBe(false);
      expect(result.error).toBeInstanceOf(TransformationError);
      expect(mockState.markAsApplied).not.toHaveBeenCalled();
    });
  });

  describe('updateColumnsAfterChange', () => {
    const initialColumns = ['col1', 'old_name', 'col3'];

    it('should update columns after rename', () => {
      const result = updateColumnsAfterChange(initialColumns, mockChanges[0]);
      expect(result).toEqual(['col1', 'new_name', 'col3']);
    });

    it('should update columns after addition', () => {
      const result = updateColumnsAfterChange(initialColumns, mockChanges[1]);
      expect(result).toEqual(['col1', 'old_name', 'col3', 'additional_field']);
    });

    it('should update columns after removal', () => {
      const columnsWithDeprecated = ['col1', 'deprecated_field', 'col3'];
      const result = updateColumnsAfterChange(columnsWithDeprecated, mockChanges[2]);
      expect(result).toEqual(['col1', 'col3']);
    });
  });

  describe('revertSingleTransformation', () => {
    const mockCallbacks: TransformationCallbacks = {
      onRevertChange: jest.fn()
    };

    const mockState: TransformationState = {
      appliedChangeIds: new Set(),
      markAsApplied: jest.fn(),
      markAsReverted: jest.fn(),
      isApplied: jest.fn(() => true)
    };

    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('should revert transformation successfully', () => {
      const result = revertSingleTransformation('test-change-id', mockCallbacks, mockState);

      expect(result.success).toBe(true);
      expect(result.error).toBeUndefined();
      expect(mockCallbacks.onRevertChange).toHaveBeenCalledWith('test-change-id');
      expect(mockState.markAsReverted).toHaveBeenCalledWith('test-change-id');
    });

    it('should fail when revert callback is missing', () => {
      const result = revertSingleTransformation('test-change-id', {}, mockState);

      expect(result.success).toBe(false);
      expect(result.error).toBeInstanceOf(TransformationError);
      expect(mockState.markAsReverted).not.toHaveBeenCalled();
    });
  });

  describe('Progress Tracker', () => {
    it('should create progress tracker', () => {
      const tracker = createProgressTracker(5);
      expect(tracker.total).toBe(5);
      expect(tracker.completed).toBe(0);
      expect(tracker.failed).toBe(0);
      expect(tracker.errors).toEqual([]);
    });

    it('should update progress on success', () => {
      const tracker = createProgressTracker(5);
      const updated = updateProgress(tracker, true, 'test operation');

      expect(updated.completed).toBe(1);
      expect(updated.failed).toBe(0);
      expect(updated.current).toBe('test operation');
      expect(updated.errors).toEqual([]);
    });

    it('should update progress on failure', () => {
      const tracker = createProgressTracker(5);
      const error = new TransformationError('Test error', 'test', 'column');
      const updated = updateProgress(tracker, false, 'test operation', error);

      expect(updated.completed).toBe(0);
      expect(updated.failed).toBe(1);
      expect(updated.current).toBe('test operation');
      expect(updated.errors).toEqual([error]);
    });
  });

  describe('Shared Utilities Integration', () => {
    it('should work with all utilities together', () => {
      const change = mockChanges[0];
      const id1 = generateChangeId(change, 0);
      const id2 = generateChangeId(change, 0);
      expect(id1).toBe(id2);
      expect(id1).toBe('rename-old_name-0');
    });

    it('should generate different IDs for different indices', () => {
      const change = mockChanges[0];
      const id1 = generateChangeId(change, 0);
      const id2 = generateChangeId(change, 1);
      expect(id1).not.toBe(id2);
    });

    it('should handle add operations', () => {
      const change = mockChanges[1];
      const id = generateChangeId(change, 1);
      expect(id).toBe('add-additional_field-1');
    });
  });

  describe('orderChangesForExecution', () => {
    it('should order changes correctly', () => {
      const changes = mockChanges.map((change, index) => ({ change, index }));
      const ordered = orderChangesForExecution(changes);

      expect(ordered.renames).toHaveLength(1);
      expect(ordered.additions).toHaveLength(1);
      expect(ordered.removals).toHaveLength(1);

      expect(ordered.renames[0].change.changeType).toBe('rename');
      expect(ordered.additions[0].change.changeType).toBe('add');
      expect(ordered.removals[0].change.changeType).toBe('remove');
    });

    it('should handle empty changes', () => {
      const ordered = orderChangesForExecution([]);
      expect(ordered.renames).toHaveLength(0);
      expect(ordered.additions).toHaveLength(0);
      expect(ordered.removals).toHaveLength(0);
    });
  });

  describe('detectChangeConflicts', () => {
    it('should detect rename conflicts', () => {
      const conflictingChanges = [
        {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'existing_col', // Conflicts with existing column
          reason: 'Test'
        }
      ];

      const conflicts = detectChangeConflicts(conflictingChanges, ['existing_col', 'old_name']);
      expect(conflicts).toHaveLength(1);
      expect(conflicts[0]).toContain('already exists');
    });

    it('should detect add conflicts', () => {
      const conflictingChanges = [
        {
          changeType: 'add',
          newColumn: 'existing_col', // Conflicts with existing column
          reason: 'Test'
        }
      ];

      const conflicts = detectChangeConflicts(conflictingChanges, ['existing_col']);
      expect(conflicts).toHaveLength(1);
      expect(conflicts[0]).toContain('already exists');
    });

    it('should return no conflicts for valid changes', () => {
      const validChanges = [
        {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'new_name',
          reason: 'Test'
        }
      ];

      const conflicts = detectChangeConflicts(validChanges, ['old_name', 'other_col']);
      expect(conflicts).toHaveLength(0);
    });
  });

  describe('generateTransformationPreview', () => {
    it('should generate correct preview', () => {
      const appliedIds = new Set(['rename-old_name-0']);
      const preview = generateTransformationPreview(mockChanges, appliedIds);

      expect(preview.pendingChanges).toHaveLength(2); // add and remove are pending
      expect(preview.renameCount).toBe(0); // rename is applied
      expect(preview.addCount).toBe(1);
      expect(preview.removeCount).toBe(1);
      expect(preview.hasDestructive).toBe(true); // has remove operation
      expect(preview.totalRowsAffected).toBe(200); // 100 + 100 for pending changes
    });

    it('should handle all applied changes', () => {
      const appliedIds = new Set([
        'rename-old_name-0',
        'add-additional_field-1',
        'remove-deprecated_field-2'
      ]);
      const preview = generateTransformationPreview(mockChanges, appliedIds);

      expect(preview.pendingChanges).toHaveLength(0);
      expect(preview.renameCount).toBe(0);
      expect(preview.addCount).toBe(0);
      expect(preview.removeCount).toBe(0);
      expect(preview.hasDestructive).toBe(false);
      expect(preview.totalRowsAffected).toBe(0);
    });
  });

  describe('isDestructiveChange and hasDestructiveChanges', () => {
    it('should identify destructive changes', () => {
      expect(isDestructiveChange(mockChanges[0])).toBe(false); // rename
      expect(isDestructiveChange(mockChanges[1])).toBe(false); // add
      expect(isDestructiveChange(mockChanges[2])).toBe(true);  // remove
    });

    it('should detect if any changes are destructive', () => {
      expect(hasDestructiveChanges(mockChanges)).toBe(true);
      expect(hasDestructiveChanges([mockChanges[0], mockChanges[1]])).toBe(false);
      expect(hasDestructiveChanges([])).toBe(false);
    });
  });

  describe('formatChangeDescription', () => {
    it('should format rename descriptions', () => {
      const description = formatChangeDescription(mockChanges[0]);
      expect(description).toBe('Rename "old_name" to "new_name"');
    });

    it('should format add descriptions', () => {
      const description = formatChangeDescription(mockChanges[1]);
      expect(description).toBe('Add column "additional_field"');
    });

    it('should format remove descriptions', () => {
      const description = formatChangeDescription(mockChanges[2]);
      expect(description).toBe('Remove column "deprecated_field"');
    });
  });

  describe('Progress Tracker', () => {
    it('should create progress tracker', () => {
      const tracker = createProgressTracker(5);
      expect(tracker.total).toBe(5);
      expect(tracker.completed).toBe(0);
      expect(tracker.failed).toBe(0);
    });

    it('should update progress on success', () => {
      let tracker = createProgressTracker(3);
      tracker = updateProgress(tracker, true, 'test operation');

      expect(tracker.completed).toBe(1);
      expect(tracker.failed).toBe(0);
      expect(tracker.current).toBe('test operation');
    });

    it('should update progress on failure', () => {
      let tracker = createProgressTracker(3);
      tracker = updateProgress(tracker, false, 'failed operation');

      expect(tracker.completed).toBe(0);
      expect(tracker.failed).toBe(1);
      expect(tracker.current).toBe('failed operation');
    });
  });

  describe('withErrorHandling', () => {
    it('should handle successful operations', async () => {
      const operation = () => 'success';
      const result = await withErrorHandling(operation, 'test', 'column1');

      expect(result.success).toBe(true);
      expect(result.result).toBe('success');
      expect(result.error).toBeUndefined();
    });

    it('should handle failed operations', async () => {
      const operation = () => {
        throw new Error('Operation failed');
      };
      const result = await withErrorHandling(operation, 'test', 'column1');

      expect(result.success).toBe(false);
      expect(result.result).toBeUndefined();
      expect(result.error).toBeInstanceOf(TransformationError);
      expect(result.error?.message).toContain('Operation failed');
    });

    it('should handle async operations', async () => {
      const operation = async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
        return 'async success';
      };
      const result = await withErrorHandling(operation, 'test', 'column1');

      expect(result.success).toBe(true);
      expect(result.result).toBe('async success');
    });
  });

  describe('TransformationError', () => {
    it('should create transformation error with details', () => {
      const originalError = new Error('Original error');
      const transformationError = new TransformationError(
        'Transformation failed',
        'rename',
        'column1',
        originalError
      );

      expect(transformationError.message).toBe('Transformation failed');
      expect(transformationError.changeType).toBe('rename');
      expect(transformationError.columnName).toBe('column1');
      expect(transformationError.originalError).toBe(originalError);
      expect(transformationError.name).toBe('TransformationError');
    });
  });
});
