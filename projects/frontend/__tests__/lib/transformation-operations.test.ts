/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import {
  createTransformationManager,
  createUndoRedoManager,
  createSequencingManager,
  TransformationManager,
  UndoRedoManager,
  SequencingManager
} from '../../lib/transformation-operations';
import {
  TransformationCallbacks,
  TransformationState
} from '../../lib/schema-transformation-utils';
import { SchemaAlignmentChangeDetail } from '../../lib/types';

describe('Transformation Operations', () => {
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

  const mockCallbacks: TransformationCallbacks = {
    onApplyColumnRename: jest.fn((originalColumn: string, newColumn: string, workingData?: string[][]) => {
      if (workingData) {
        const updatedData = workingData.map(row => [...row]);
        const colIndex = updatedData[0].indexOf(originalColumn);
        if (colIndex !== -1) {
          updatedData[0][colIndex] = newColumn;
        }
        return updatedData;
      }
    }),
    onApplyColumnAddition: jest.fn((newColumn: string, workingData?: string[][]) => {
      if (workingData) {
        const updatedData = workingData.map(row => [...row, '']);
        updatedData[0][updatedData[0].length - 1] = newColumn;
        return updatedData;
      }
    }),
    onApplyColumnRemoval: jest.fn((columnName: string, workingData?: string[][]) => {
      if (workingData) {
        const colIndex = workingData[0].indexOf(columnName);
        if (colIndex !== -1) {
          return workingData.map(row => row.filter((_, i) => i !== colIndex));
        }
        return workingData;
      }
    }),
    onRevertChange: jest.fn()
  };

  const mockState: TransformationState = {
    appliedChangeIds: new Set(),
    markAsApplied: jest.fn(),
    markAsReverted: jest.fn(),
    isApplied: jest.fn(() => false)
  };

  const currentColumns = ['existing_col', 'old_name', 'another_col'];
  const currentData = [currentColumns];

  beforeEach(() => {
    jest.clearAllMocks();
    mockState.appliedChangeIds.clear();
  });

  describe('createTransformationManager', () => {
    let manager: TransformationManager;

    beforeEach(() => {
      manager = createTransformationManager(
        currentData,
        mockCallbacks,
        mockState
      );
    });

    it('should create transformation manager with all methods', () => {
      expect(manager.applyChange).toBeDefined();
      expect(manager.revertChange).toBeDefined();
      expect(manager.applyAllChanges).toBeDefined();
      expect(manager.revertAllChanges).toBeDefined();
      expect(manager.checkConfirmationNeeded).toBeDefined();
      expect(manager.getAppliedChanges).toBeDefined();
      expect(manager.isChangeApplied).toBeDefined();
    });

    it('should apply individual change successfully', async () => {
      const result = await manager.applyChange(mockChanges[0], 0);

      expect(result.success).toBe(true);
      expect(mockCallbacks.onApplyColumnRename).toHaveBeenCalledWith('old_name', 'new_name');
      expect(mockState.markAsApplied).toHaveBeenCalled();
    });

    it('should revert individual change successfully', () => {
      const changeId = 'test-change-id';
      const result = manager.revertChange(changeId);

      expect(result.success).toBe(true);
      expect(mockCallbacks.onRevertChange).toHaveBeenCalledWith(changeId);
      expect(mockState.markAsReverted).toHaveBeenCalledWith(changeId);
    });

    it('should check confirmation requirements', () => {
      // Test for destructive change (remove)
      const confirmationConfig = manager.checkConfirmationNeeded('remove', [mockChanges[2]]);
      expect(confirmationConfig).not.toBeNull();
      expect(confirmationConfig?.type).toBe('remove');

      // Test for non-destructive change (add)
      const noConfirmationConfig = manager.checkConfirmationNeeded('apply', [mockChanges[1]]);
      expect(noConfirmationConfig).toBeNull(); // Single non-destructive change doesn't need confirmation
    });

    it('should get applied changes', () => {
      const appliedChanges = manager.getAppliedChanges();
      expect(appliedChanges).toBeInstanceOf(Set);
      expect(appliedChanges.size).toBe(0);
    });

    it('should check if change is applied', () => {
      const changeId = 'test-change-id';
      const isApplied = manager.isChangeApplied(changeId);
      expect(isApplied).toBe(false);
      expect(mockState.isApplied).toHaveBeenCalledWith(changeId);
    });

    it('should apply all changes in bulk', async () => {
      // Use columns that will pass validation
      const validColumns = ['old_name', 'existing_col', 'deprecated_field'];
      const validData = [validColumns];
      const validManager = createTransformationManager(
        validData,
        mockCallbacks,
        mockState
      );

      const changesToApply = mockChanges.map((change, index) => ({ change, index }));
      const progress = await validManager.applyAllChanges(changesToApply);

      expect(progress.total).toBe(3);
      expect(progress.completed).toBeGreaterThan(0);
      expect(mockCallbacks.onApplyColumnRename).toHaveBeenCalled();
      expect(mockCallbacks.onApplyColumnAddition).toHaveBeenCalled();
      expect(mockCallbacks.onApplyColumnRemoval).toHaveBeenCalled();
    });

    it('should revert all changes in bulk', () => {
      // First mark some changes as applied
      mockState.isApplied = jest.fn(() => true);

      const changesToRevert = mockChanges.map((change, index) => ({ change, index }));
      const progress = manager.revertAllChanges(changesToRevert);

      expect(progress.total).toBe(3);
      expect(progress.completed).toBeGreaterThan(0);
      expect(mockCallbacks.onRevertChange).toHaveBeenCalledTimes(3);
    });
  });

  describe('createUndoRedoManager', () => {
    let transformationManager: TransformationManager;
    let undoRedoManager: UndoRedoManager;

    beforeEach(() => {
      transformationManager = createTransformationManager(
        currentData,
        mockCallbacks,
        mockState
      );
      undoRedoManager = createUndoRedoManager(transformationManager);
    });

    it('should create undo/redo manager with all methods', () => {
      expect(undoRedoManager.canUndo).toBeDefined();
      expect(undoRedoManager.canRedo).toBeDefined();
      expect(undoRedoManager.undo).toBeDefined();
      expect(undoRedoManager.redo).toBeDefined();
      expect(undoRedoManager.clearHistory).toBeDefined();
      expect(undoRedoManager.getHistorySize).toBeDefined();
    });

    it('should initially have no undo/redo operations', () => {
      expect(undoRedoManager.canUndo()).toBe(false);
      expect(undoRedoManager.canRedo()).toBe(false);

      const historySize = undoRedoManager.getHistorySize();
      expect(historySize.undoCount).toBe(0);
      expect(historySize.redoCount).toBe(0);
    });

    it('should fail undo when no operations exist', async () => {
      const result = await undoRedoManager.undo();
      expect(result.success).toBe(false);
      expect(result.error?.message).toContain('Nothing to undo');
    });

    it('should fail redo when no operations exist', async () => {
      const result = await undoRedoManager.redo();
      expect(result.success).toBe(false);
      expect(result.error?.message).toContain('Nothing to redo');
    });

    it('should clear history', () => {
      undoRedoManager.clearHistory();
      expect(undoRedoManager.canUndo()).toBe(false);
      expect(undoRedoManager.canRedo()).toBe(false);
    });
  });

  describe('createSequencingManager', () => {
    let sequencingManager: SequencingManager;

    beforeEach(() => {
      sequencingManager = createSequencingManager();
    });

    it('should create sequencing manager with all methods', () => {
      expect(sequencingManager.validateSequence).toBeDefined();
      expect(sequencingManager.optimizeSequence).toBeDefined();
      expect(sequencingManager.estimateImpact).toBeDefined();
    });

    it('should validate sequence without conflicts', () => {
      const validation = sequencingManager.validateSequence(mockChanges);
      expect(validation.isValid).toBe(true);
      expect(validation.conflicts).toEqual([]);
    });

    it('should detect sequence conflicts', () => {
      const conflictingChanges: SchemaAlignmentChangeDetail[] = [
        {
          changeType: 'add',
          newColumn: 'test_column',
          reason: 'Add column'
        },
        {
          changeType: 'add',
          newColumn: 'test_column', // Same name - conflict
          reason: 'Add same column again'
        }
      ];

      const validation = sequencingManager.validateSequence(conflictingChanges);
      expect(validation.isValid).toBe(false);
      expect(validation.conflicts.length).toBeGreaterThan(0);
      expect(validation.conflicts[0]).toContain('already exists');
    });

    it('should optimize sequence order', () => {
      const changesToOptimize = mockChanges.map((change, index) => ({ change, index }));
      const optimized = sequencingManager.optimizeSequence(changesToOptimize);

      expect(optimized.length).toBe(3);

      // Should be ordered: renames, additions, removals
      const types = optimized.map(({ change }) => change.changeType.toLowerCase());
      const renameIndex = types.indexOf('rename');
      const addIndex = types.indexOf('add');
      const removeIndex = types.indexOf('remove');

      expect(renameIndex).toBeLessThan(addIndex);
      expect(addIndex).toBeLessThan(removeIndex);
    });

    it('should estimate impact correctly', () => {
      const impact = sequencingManager.estimateImpact(mockChanges);

      expect(impact.totalRowsAffected).toBe(300); // 100 * 3 changes
      expect(impact.columnsAffected).toBe(3);
      expect(impact.destructiveOperations).toBe(1); // Only the remove operation
      expect(impact.estimatedDuration).toBeGreaterThan(0);
    });

    it('should estimate zero impact for empty changes', () => {
      const impact = sequencingManager.estimateImpact([]);

      expect(impact.totalRowsAffected).toBe(0);
      expect(impact.columnsAffected).toBe(0);
      expect(impact.destructiveOperations).toBe(0);
      expect(impact.estimatedDuration).toBe(0);
    });
  });

  describe('Integration Tests', () => {
    it('should work together for complete transformation workflow', async () => {
      // Use columns that will pass validation
      const validColumns = ['old_name', 'existing_col', 'deprecated_field'];
      const validData = [validColumns];
      const manager = createTransformationManager(
        validData,
        mockCallbacks,
        mockState
      );

      const sequencing = createSequencingManager();

      // Validate sequence
      const validation = sequencing.validateSequence(mockChanges);
      expect(validation.isValid).toBe(true);

      // Optimize sequence
      const changesToApply = mockChanges.map((change, index) => ({ change, index }));
      const optimized = sequencing.optimizeSequence(changesToApply);
      expect(optimized.length).toBe(3);

      // Estimate impact
      const impact = sequencing.estimateImpact(mockChanges);
      expect(impact.totalRowsAffected).toBe(300);

      // Apply changes
      const progress = await manager.applyAllChanges(optimized);
      expect(progress.completed).toBeGreaterThan(0);

      // Check applied state - the state should have been updated by markAsApplied calls
      expect(mockState.markAsApplied).toHaveBeenCalled();
    });

    it('should handle errors gracefully in workflow', async () => {
      // Create manager with failing callbacks
      const failingCallbacks: TransformationCallbacks = {
        onApplyColumnRename: jest.fn(() => { throw new Error('Rename failed'); }),
        onApplyColumnAddition: jest.fn(() => { throw new Error('Addition failed'); }),
        onApplyColumnRemoval: jest.fn(() => { throw new Error('Removal failed'); }),
        onRevertChange: jest.fn()
      };

      const manager = createTransformationManager(
        currentData,
        failingCallbacks,
        mockState
      );

      // Try to apply changes - should handle errors
      const changesToApply = mockChanges.map((change, index) => ({ change, index }));
      const progress = await manager.applyAllChanges(changesToApply);

      expect(progress.failed).toBe(3); // All should fail
      expect(progress.completed).toBe(0);
      expect(progress.errors.length).toBe(3);
    });
  });
});
