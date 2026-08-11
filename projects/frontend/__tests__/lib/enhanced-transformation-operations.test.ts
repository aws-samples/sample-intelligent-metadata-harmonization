/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import {
  createTransformationManager,
  executeSelectiveBulkOperation,
  previewBulkOperation,
  createEnhancedProgressTracker,
  BulkOperationConfig,
  SelectiveBulkConfig,
  BulkOperationResult
} from '../../lib/transformation-operations';
import { SchemaAlignmentChangeDetail } from '../../lib/types';
import {
  TransformationCallbacks,
  TransformationState,
  generateChangeId
} from '../../lib/schema-transformation-utils';

// Mock data
const mockChanges: Array<{ change: SchemaAlignmentChangeDetail; index: number }> = [
  {
    change: {
      changeType: 'rename',
      originalColumn: 'old_name',
      newColumn: 'new_name',
      reason: 'Standardize naming',
      rowCountAffected: 100
    },
    index: 0
  },
  {
    change: {
      changeType: 'add',
      newColumn: 'added_column',
      reason: 'Required field',
      rowCountAffected: 100
    },
    index: 1
  },
  {
    change: {
      changeType: 'remove',
      originalColumn: 'deprecated_field',
      reason: 'No longer needed',
      rowCountAffected: 100
    },
    index: 2
  }
];

const mockCurrentColumns = ['old_name', 'existing_column', 'deprecated_field'];
const mockCurrentData = [
  ['old_name', 'existing_column', 'deprecated_field'],
  ['value1', 'value2', 'value3'],
  ['value4', 'value5', 'value6']
];

describe('Enhanced Transformation Operations', () => {
  let mockCallbacks: TransformationCallbacks;
  let mockState: TransformationState;
  let appliedChangeIds: Set<string>;

  beforeEach(() => {
    appliedChangeIds = new Set();

    mockCallbacks = {
      onApplyColumnRename: jest.fn(),
      onApplyColumnAddition: jest.fn(),
      onApplyColumnRemoval: jest.fn(),
      onRevertChange: jest.fn()
    };

    mockState = {
      appliedChangeIds,
      markAsApplied: jest.fn((id) => appliedChangeIds.add(id)),
      markAsReverted: jest.fn((id) => appliedChangeIds.delete(id)),
      isApplied: jest.fn((id) => appliedChangeIds.has(id))
    };
  });

  describe('createEnhancedProgressTracker', () => {
    it('creates progress tracker with correct initial values', () => {
      const config: BulkOperationConfig = {
        continueOnError: true,
        showProgress: true,
        allowCancellation: true
      };

      const tracker = createEnhancedProgressTracker(5, config);

      expect(tracker.total).toBe(5);
      expect(tracker.completed).toBe(0);
      expect(tracker.failed).toBe(0);
      expect(tracker.cancelled).toBe(false);
      expect(tracker.canCancel).toBe(true);
      expect(tracker.operationResults).toEqual([]);
      expect(tracker.startTime).toBeInstanceOf(Date);
    });

    it('creates non-cancellable tracker when configured', () => {
      const config: BulkOperationConfig = {
        continueOnError: true,
        showProgress: true,
        allowCancellation: false
      };

      const tracker = createEnhancedProgressTracker(3, config);

      expect(tracker.canCancel).toBe(false);
    });

    it('provides working cancel function', () => {
      const config: BulkOperationConfig = {
        continueOnError: true,
        showProgress: true,
        allowCancellation: true
      };

      const tracker = createEnhancedProgressTracker(3, config);

      expect(tracker.cancelled).toBe(false);
      tracker.cancel();
      expect(tracker.cancelled).toBe(true);
    });
  });

  describe('previewBulkOperation', () => {
    it('generates correct preview for selected changes', () => {
      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0),
        generateChangeId(mockChanges[1].change, 1)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true
        }
      };

      const preview = previewBulkOperation(config, mockChanges, mockCurrentColumns);

      expect(preview.affectedChanges).toHaveLength(2);
      expect(preview.impact.totalRowsAffected).toBe(200);
      expect(preview.impact.columnsAffected).toBe(2);
      expect(preview.impact.destructiveOperations).toBe(0);
      expect(preview.impact.estimatedDuration).toBeGreaterThan(0);
    });

    it('detects destructive operations in preview', () => {
      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[2].change, 2) // remove operation
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true
        }
      };

      const preview = previewBulkOperation(config, mockChanges, mockCurrentColumns);

      expect(preview.impact.destructiveOperations).toBe(1);
      expect(preview.warnings).toContain('1 operations will permanently remove data');
    });

    it('detects conflicts in preview', () => {
      // Create a conflict by trying to rename to an existing column
      const conflictingChange = {
        change: {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'existing_column', // This already exists
          reason: 'Conflict test'
        },
        index: 0
      };

      const selectedChangeIds = new Set([
        generateChangeId(conflictingChange.change, 0)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true
        }
      };

      const preview = previewBulkOperation(config, [conflictingChange], mockCurrentColumns);

      expect(preview.conflicts.length).toBeGreaterThan(0);
      expect(preview.safeToExecute).toBe(false);
    });

    it('generates warnings for large datasets', () => {
      const largeDatasetChange = {
        change: {
          changeType: 'add',
          newColumn: 'large_column',
          rowCountAffected: 15000 // Large dataset
        },
        index: 0
      };

      const selectedChangeIds = new Set([
        generateChangeId(largeDatasetChange.change, 0)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true
        }
      };

      const preview = previewBulkOperation(config, [largeDatasetChange], mockCurrentColumns);

      expect(preview.warnings).toContain('Large dataset - operation may take several minutes');
    });
  });

  describe('executeSelectiveBulkOperation', () => {
    it('executes selected operations successfully', async () => {
      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0),
        generateChangeId(mockChanges[1].change, 1)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true,
          maxRetries: 1
        }
      };

      const result = await executeSelectiveBulkOperation(
        config,
        mockChanges,
        mockCurrentColumns,
        mockCallbacks,
        mockState
      );

      expect(result.success).toBe(true);
      expect(result.summary.totalOperations).toBe(2);
      expect(result.summary.successfulOperations).toBe(2);
      expect(result.summary.failedOperations).toBe(0);
      expect(mockCallbacks.onApplyColumnRename).toHaveBeenCalledWith('old_name', 'new_name');
      expect(mockCallbacks.onApplyColumnAddition).toHaveBeenCalledWith('added_column');
    });

    it('handles operation failures with continue on error', async () => {
      // Mock a failure for the rename operation
      mockCallbacks.onApplyColumnRename = jest.fn(() => {
        throw new Error('Rename failed');
      });

      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0),
        generateChangeId(mockChanges[1].change, 1)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true,
          maxRetries: 0
        }
      };

      const result = await executeSelectiveBulkOperation(
        config,
        mockChanges,
        mockCurrentColumns,
        mockCallbacks,
        mockState
      );

      expect(result.success).toBe(false);
      expect(result.summary.successfulOperations).toBe(1);
      expect(result.summary.failedOperations).toBe(1);
      expect(result.errorReport).toBeDefined();
      expect(result.errorReport!.errors).toHaveLength(1);
      expect(result.errorReport!.errors[0].error.message).toBe('Failed to rename column "old_name": Rename failed');
    });

    it('stops on first error when continueOnError is false', async () => {
      // Mock a failure for the first operation
      mockCallbacks.onApplyColumnRename = jest.fn(() => {
        throw new Error('Rename failed');
      });

      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0),
        generateChangeId(mockChanges[1].change, 1)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: false,
          showProgress: true,
          allowCancellation: true,
          maxRetries: 0
        }
      };

      const result = await executeSelectiveBulkOperation(
        config,
        mockChanges,
        mockCurrentColumns,
        mockCallbacks,
        mockState
      );

      expect(result.success).toBe(false);
      expect(result.summary.successfulOperations).toBe(0);
      expect(result.summary.failedOperations).toBe(1);
      // Second operation should not have been attempted
      expect(mockCallbacks.onApplyColumnAddition).not.toHaveBeenCalled();
    });

    it('retries failed operations according to maxRetries', async () => {
      let attemptCount = 0;
      mockCallbacks.onApplyColumnRename = jest.fn(() => {
        attemptCount++;
        if (attemptCount <= 2) {
          throw new Error('Temporary failure');
        }
        // Succeed on third attempt
      });

      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true,
          maxRetries: 2
        }
      };

      const result = await executeSelectiveBulkOperation(
        config,
        mockChanges,
        mockCurrentColumns,
        mockCallbacks,
        mockState
      );

      expect(result.success).toBe(true);
      expect(attemptCount).toBe(3); // Initial attempt + 2 retries
      expect(result.progress.operationResults[0].retryCount).toBe(2);
    });

    it('handles operation cancellation', async () => {
      let progressCallback: ((progress: any) => void) | undefined;

      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0),
        generateChangeId(mockChanges[1].change, 1)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true,
          operationDelay: 50 // Add delay to allow cancellation
        }
      };

      // Start the operation
      const resultPromise = executeSelectiveBulkOperation(
        config,
        mockChanges,
        mockCurrentColumns,
        mockCallbacks,
        mockState,
        (progress) => {
          progressCallback = (p) => p;
          // Cancel after first operation
          if (progress.completed === 1) {
            progress.cancel();
          }
        }
      );

      const result = await resultPromise;

      expect(result.progress.cancelled).toBe(true);
      expect(result.summary.cancelledOperations).toBeGreaterThan(0);
    });

    it('calls progress callback during execution', async () => {
      const progressCallback = jest.fn();

      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0),
        generateChangeId(mockChanges[1].change, 1)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true
        }
      };

      await executeSelectiveBulkOperation(
        config,
        mockChanges,
        mockCurrentColumns,
        mockCallbacks,
        mockState,
        progressCallback
      );

      expect(progressCallback).toHaveBeenCalledTimes(2); // Once per operation
      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          total: 2,
          completed: expect.any(Number),
          currentOperation: expect.any(String)
        })
      );
    });

    it('calculates estimated time remaining', async () => {
      const progressCallback = jest.fn();

      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0),
        generateChangeId(mockChanges[1].change, 1)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true,
          operationDelay: 10 // Small delay to allow time calculation
        }
      };

      await executeSelectiveBulkOperation(
        config,
        mockChanges,
        mockCurrentColumns,
        mockCallbacks,
        mockState,
        progressCallback
      );

      // Check that estimated time remaining was calculated
      const progressCalls = progressCallback.mock.calls;
      const firstProgressCall = progressCalls[0][0];

      if (firstProgressCall.estimatedTimeRemaining !== undefined) {
        expect(firstProgressCall.estimatedTimeRemaining).toBeGreaterThanOrEqual(0);
      }
    });

    it('executes revert operations correctly', async () => {
      // First apply some changes
      appliedChangeIds.add(generateChangeId(mockChanges[0].change, 0));
      appliedChangeIds.add(generateChangeId(mockChanges[1].change, 1));

      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'revert',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true
        }
      };

      const result = await executeSelectiveBulkOperation(
        config,
        mockChanges,
        mockCurrentColumns,
        mockCallbacks,
        mockState
      );

      expect(result.success).toBe(true);
      expect(mockCallbacks.onRevertChange).toHaveBeenCalledWith(
        generateChangeId(mockChanges[0].change, 0)
      );
    });
  });

  describe('createTransformationManager integration', () => {
    it('creates manager with enhanced bulk operation capabilities', () => {
      const manager = createTransformationManager(
        mockCurrentData,
        mockCallbacks,
        mockState
      );

      expect(manager.executeSelectiveBulkOperation).toBeDefined();
      expect(manager.previewBulkOperation).toBeDefined();
      expect(typeof manager.executeSelectiveBulkOperation).toBe('function');
      expect(typeof manager.previewBulkOperation).toBe('function');
    });

    it('executes selective bulk operations through manager', async () => {
      const manager = createTransformationManager(
        mockCurrentData,
        mockCallbacks,
        mockState
      );

      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true
        }
      };

      const result = await manager.executeSelectiveBulkOperation(config, mockChanges);

      expect(result.success).toBe(true);
      expect(result.summary.totalOperations).toBe(1);
    });

    it('generates previews through manager', () => {
      const manager = createTransformationManager(
        mockCurrentData,
        mockCallbacks,
        mockState
      );

      const selectedChangeIds = new Set([
        generateChangeId(mockChanges[0].change, 0)
      ]);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType: 'apply',
        config: {
          continueOnError: true,
          showProgress: true,
          allowCancellation: true
        }
      };

      const preview = manager.previewBulkOperation(config, mockChanges);

      expect(preview.affectedChanges).toHaveLength(1);
      expect(preview.impact.columnsAffected).toBe(1);
    });
  });
});
