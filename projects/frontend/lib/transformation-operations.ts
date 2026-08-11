/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import { SchemaAlignmentChangeDetail } from './types';
import {
  TransformationCallbacks,
  TransformationState,
  ProgressTracker,
  executeSingleTransformation,
  executeBulkTransformations,
  revertSingleTransformation,
  revertBulkTransformations,
  generateChangeId,
  createProgressTracker,
  updateProgress,
  orderChangesForExecution,
  detectChangeConflicts,
  formatChangeDescription,
  updateColumnsAfterChange
} from './schema-transformation-utils';
import {
  shouldShowConfirmation,
  validateConfirmationRequirements,
  createConfirmationConfig,
  ConfirmationDialogConfig
} from './confirmation-dialog-utils';

/**
 * Enhanced bulk operation configuration
 */
export interface BulkOperationConfig {
  /** Whether to continue on error or stop on first error */
  continueOnError: boolean;
  /** Whether to show progress indicators */
  showProgress: boolean;
  /** Whether operation can be cancelled */
  allowCancellation: boolean;
  /** Delay between operations in milliseconds */
  operationDelay?: number;
  /** Maximum number of retries for failed operations */
  maxRetries?: number;
}

/**
 * Enhanced progress tracking with cancellation support
 */
export interface EnhancedProgressTracker extends ProgressTracker {
  /** Current operation being performed */
  currentOperation?: string;
  /** Whether operation was cancelled */
  cancelled: boolean;
  /** Cancellation callback */
  cancel: () => void;
  /** Whether operation can be cancelled */
  canCancel: boolean;
  /** Estimated time remaining in milliseconds */
  estimatedTimeRemaining?: number;
  /** Start time of operation */
  startTime: Date;
  /** Detailed results for each operation */
  operationResults: Array<{
    changeId: string;
    change: SchemaAlignmentChangeDetail;
    success: boolean;
    error?: Error;
    retryCount: number;
    duration: number;
  }>;
}

/**
 * Confidence distribution for bulk operations
 */
export interface ConfidenceDistribution {
  /** Number of high confidence operations (≥ 0.8) */
  high: number;
  /** Number of medium confidence operations (0.5 - 0.79) */
  medium: number;
  /** Number of low confidence operations (< 0.5) */
  low: number;
  /** Average confidence score across all operations */
  averageScore: number;
  /** Minimum confidence score */
  minScore: number;
  /** Maximum confidence score */
  maxScore: number;
}

/**
 * Bulk operation result with detailed reporting and confidence information
 */
export interface BulkOperationResult {
  /** Overall success status */
  success: boolean;
  /** Progress tracker with detailed results */
  progress: EnhancedProgressTracker;
  /** Summary statistics */
  summary: {
    totalOperations: number;
    successfulOperations: number;
    failedOperations: number;
    cancelledOperations: number;
    totalDuration: number;
    averageOperationTime: number;
  };
  /** Confidence distribution of applied changes */
  confidenceDistribution: ConfidenceDistribution;
  /** Detailed error report */
  errorReport?: {
    errors: Array<{
      changeId: string;
      change: SchemaAlignmentChangeDetail;
      error: Error;
      retryCount: number;
    }>;
    recoveryOptions: string[];
  };
}

/**
 * Selective bulk operation configuration
 */
export interface SelectiveBulkConfig {
  /** Selected change IDs to include in bulk operation */
  selectedChangeIds: Set<string>;
  /** Operation type */
  operationType: 'apply' | 'revert';
  /** Bulk operation configuration */
  config: BulkOperationConfig;
}

/**
 * Bulk operation preview with confidence information
 */
export interface BulkOperationPreview {
  /** Changes that will be affected */
  affectedChanges: SchemaAlignmentChangeDetail[];
  /** Estimated impact */
  impact: {
    totalRowsAffected: number;
    columnsAffected: number;
    destructiveOperations: number;
    estimatedDuration: number;
  };
  /** Confidence distribution of changes to be applied */
  confidenceDistribution: ConfidenceDistribution;
  /** Potential conflicts */
  conflicts: string[];
  /** Warnings for user */
  warnings: string[];
  /** Whether operation is safe to proceed */
  safeToExecute: boolean;
}

/**
 * Calculate confidence distribution from a list of changes
 */
export const calculateConfidenceDistribution = (changes: SchemaAlignmentChangeDetail[]): ConfidenceDistribution => {
  if (changes.length === 0) {
    return {
      high: 0,
      medium: 0,
      low: 0,
      averageScore: 0,
      minScore: 0,
      maxScore: 0
    };
  }

  let high = 0;
  let medium = 0;
  let low = 0;
  let totalScore = 0;
  let minScore = 1;
  let maxScore = 0;

  changes.forEach(change => {
    const score = change.confidenceScore || 0;
    totalScore += score;
    minScore = Math.min(minScore, score);
    maxScore = Math.max(maxScore, score);

    if (score >= 0.8) {
      high++;
    } else if (score >= 0.5) {
      medium++;
    } else {
      low++;
    }
  });

  return {
    high,
    medium,
    low,
    averageScore: totalScore / changes.length,
    minScore,
    maxScore
  };
};

/**
 * Get confidence level from numerical score
 */
export const getConfidenceLevelFromScore = (score: number): 'High' | 'Medium' | 'Low' => {
  if (score >= 0.8) return 'High';
  if (score >= 0.5) return 'Medium';
  return 'Low';
};

/**
 * Get confidence color for UI display
 */
export const getConfidenceColor = (level: string): string => {
  switch (level) {
    case 'High': return '#4caf50';  // Green
    case 'Medium': return '#ff9800'; // Orange
    case 'Low': return '#f44336';   // Red
    default: return '#757575';      // Gray
  }
};

/**
 * Shared transformation operations that can be used by both individual and bulk operations
 * This module provides a unified interface for executing schema transformations
 */
export interface TransformationManager {
  // Individual operations
  applyChange: (change: SchemaAlignmentChangeDetail, index: number) => Promise<{ success: boolean; error?: Error }>;
  revertChange: (changeId: string) => { success: boolean; error?: Error };

  // Enhanced bulk operations
  applyAllChanges: (changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>) => Promise<ProgressTracker & { appliedChanges?: Array<{ change: SchemaAlignmentChangeDetail; index: number; columnIndex?: number }> }>;
  revertAllChanges: (changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>) => ProgressTracker;

  // New enhanced bulk operations
  executeSelectiveBulkOperation: (config: SelectiveBulkConfig, changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>) => Promise<BulkOperationResult>;
  previewBulkOperation: (config: SelectiveBulkConfig, changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>) => BulkOperationPreview;

  // Confirmation handling
  checkConfirmationNeeded: (operationType: 'apply' | 'revert' | 'remove', changes: SchemaAlignmentChangeDetail[]) => ConfirmationDialogConfig | null;

  // State management
  getAppliedChanges: () => Set<string>;
  isChangeApplied: (changeId: string) => boolean;
}

/**
 * Creates an enhanced progress tracker with cancellation support
 */
export const createEnhancedProgressTracker = (
  total: number,
  config: BulkOperationConfig
): EnhancedProgressTracker => {
  let isCancelled = false;

  return {
    total,
    completed: 0,
    failed: 0,
    errors: [],
    canCancel: config.allowCancellation,
    startTime: new Date(),
    operationResults: [],
    cancel: () => {
      isCancelled = true;
    },
    get cancelled() {
      return isCancelled;
    }
  };
};

/**
 * Executes a selective bulk operation with enhanced progress tracking and error recovery
 */
export const executeSelectiveBulkOperation = async (
  config: SelectiveBulkConfig,
  changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>,
  currentColumns: string[],
  callbacks: TransformationCallbacks,
  state: TransformationState,
  onProgress?: (progress: EnhancedProgressTracker) => void
): Promise<BulkOperationResult> => {
  // Filter changes based on selection
  const selectedChanges = changes.filter(({ change, index }) => {
    const changeId = generateChangeId(change, index);
    return config.selectedChangeIds.has(changeId);
  });

  const progress = createEnhancedProgressTracker(selectedChanges.length, config.config);
  const startTime = Date.now();

  // Order changes for optimal execution
  const orderedSequence = orderChangesForExecution(selectedChanges);
  const orderedChanges = [
    ...orderedSequence.renames,
    ...orderedSequence.additions,
    ...orderedSequence.removals
  ];

  let workingColumns = [...currentColumns];

  for (const { change, index } of orderedChanges) {
    // Check for cancellation
    if (progress.cancelled) {
      break;
    }

    const changeId = generateChangeId(change, index);
    const changeDescription = formatChangeDescription(change);
    progress.currentOperation = changeDescription;

    const operationStartTime = Date.now();
    let retryCount = 0;
    let operationResult: { success: boolean; error?: Error } = { success: false };

    // Retry logic
    while (retryCount <= (config.config.maxRetries || 0)) {
      try {
        if (config.operationType === 'apply') {
          operationResult = await executeSingleTransformation(
            change,
            index,
            workingColumns,
            callbacks,
            state
          );
        } else {
          operationResult = revertSingleTransformation(changeId, callbacks, state);
        }

        if (operationResult.success) {
          // Update working columns for next iteration
          if (config.operationType === 'apply') {
            workingColumns = updateColumnsAfterChange(workingColumns, change);
          }
          break;
        } else if (!config.config.continueOnError && retryCount >= (config.config.maxRetries || 0)) {
          // Stop on error if configured to do so
          break;
        }
      } catch (error) {
        operationResult = {
          success: false,
          error: error instanceof Error ? error : new Error('Unknown error')
        };
      }

      retryCount++;

      // Add delay between retries
      if (retryCount <= (config.config.maxRetries || 0) && config.config.operationDelay) {
        await new Promise(resolve => setTimeout(resolve, config.config.operationDelay));
      }
    }

    const operationDuration = Date.now() - operationStartTime;

    // Record operation result
    progress.operationResults.push({
      changeId,
      change,
      success: operationResult.success,
      error: operationResult.error,
      retryCount,
      duration: operationDuration
    });

    // Update progress
    if (operationResult.success) {
      progress.completed++;
    } else {
      progress.failed++;
      if (operationResult.error) {
        progress.errors.push(operationResult.error as any);
      }
    }

    // Calculate estimated time remaining
    const elapsed = Date.now() - startTime;
    const averageTimePerOperation = elapsed / (progress.completed + progress.failed);
    const remaining = progress.total - progress.completed - progress.failed;
    progress.estimatedTimeRemaining = remaining * averageTimePerOperation;

    // Call progress callback
    if (onProgress) {
      onProgress(progress);
    }

    // Add delay between operations if configured
    if (config.config.operationDelay && !progress.cancelled) {
      await new Promise(resolve => setTimeout(resolve, config.config.operationDelay));
    }

    // Stop on error if configured to do so
    if (!operationResult.success && !config.config.continueOnError) {
      break;
    }
  }

  const totalDuration = Date.now() - startTime;
  const successfulOps = progress.operationResults.filter(r => r.success).length;
  const failedOps = progress.operationResults.filter(r => !r.success).length;
  const cancelledOps = progress.cancelled ? progress.total - progress.completed - progress.failed : 0;

  // Calculate confidence distribution for successful operations
  const successfulChanges = progress.operationResults
    .filter(r => r.success)
    .map(r => r.change);
  const confidenceDistribution = calculateConfidenceDistribution(successfulChanges);

  const result: BulkOperationResult = {
    success: progress.failed === 0 && !progress.cancelled,
    progress,
    summary: {
      totalOperations: progress.total,
      successfulOperations: successfulOps,
      failedOperations: failedOps,
      cancelledOperations: cancelledOps,
      totalDuration,
      averageOperationTime: progress.operationResults.length > 0
        ? progress.operationResults.reduce((sum, r) => sum + r.duration, 0) / progress.operationResults.length
        : 0
    },
    confidenceDistribution
  };

  // Add error report if there were failures
  if (progress.failed > 0) {
    const failedOperations = progress.operationResults.filter(r => !r.success);
    result.errorReport = {
      errors: failedOperations.map(op => ({
        changeId: op.changeId,
        change: op.change,
        error: op.error || new Error('Unknown error'),
        retryCount: op.retryCount
      })),
      recoveryOptions: [
        'Retry failed operations individually',
        'Review and fix data conflicts',
        'Revert successful operations and try again',
        'Contact support if errors persist'
      ]
    };
  }

  return result;
};

/**
 * Generates a preview of what a bulk operation will do
 */
export const previewBulkOperation = (
  config: SelectiveBulkConfig,
  changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>,
  currentColumns: string[]
): BulkOperationPreview => {
  // Filter changes based on selection
  const selectedChanges = changes.filter(({ change, index }) => {
    const changeId = generateChangeId(change, index);
    return config.selectedChangeIds.has(changeId);
  });

  const affectedChanges = selectedChanges.map(({ change }) => change);

  // Calculate impact
  const totalRowsAffected = affectedChanges.reduce((sum, change) =>
    sum + (change.rowCountAffected || 0), 0
  );

  const columnsAffected = affectedChanges.length;
  const destructiveOperations = affectedChanges.filter(change =>
    change.changeType.toLowerCase() === 'remove'
  ).length;

  // Estimate duration (100ms per operation + 10ms per 1000 rows)
  const estimatedDuration = (affectedChanges.length * 100) + (totalRowsAffected / 1000 * 10);

  // Detect conflicts
  const conflicts = detectChangeConflicts(affectedChanges, currentColumns);

  // Generate warnings
  const warnings: string[] = [];
  if (destructiveOperations > 0) {
    warnings.push(`${destructiveOperations} operations will permanently remove data`);
  }
  if (conflicts.length > 0) {
    warnings.push(`${conflicts.length} potential conflicts detected`);
  }
  if (totalRowsAffected > 10000) {
    warnings.push('Large dataset - operation may take several minutes');
  }

  // Calculate confidence distribution
  const confidenceDistribution = calculateConfidenceDistribution(affectedChanges);

  return {
    affectedChanges,
    impact: {
      totalRowsAffected,
      columnsAffected,
      destructiveOperations,
      estimatedDuration
    },
    confidenceDistribution,
    conflicts,
    warnings,
    safeToExecute: conflicts.length === 0
  };
};

/**
 * Creates a transformation manager with shared operations
 */
export const createTransformationManager = (
  currentData: string[][],
  callbacks: TransformationCallbacks,
  state: TransformationState,
  onProgress?: (progress: ProgressTracker) => void,
  onFinalDataUpdate?: (finalData: string[][]) => void,
  onAppliedChanges?: (appliedChanges: Array<{ change: SchemaAlignmentChangeDetail; index: number; columnIndex?: number }>) => void
): TransformationManager => {

  const applyChange = async (
    change: SchemaAlignmentChangeDetail,
    index: number
  ): Promise<{ success: boolean; error?: Error }> => {
    console.log('🔧 TransformationManager: Applying individual change:', { change, index });

    const result = await executeSingleTransformation(
      change,
      index,
      currentData[0] || [],
      callbacks,
      state
    );

    console.log('🔧 TransformationManager: Individual change result:', {
      success: result.success,
      error: result.error?.message
    });

    // Update progress for individual operations too
    if (onProgress) {
      const progress = createProgressTracker(1);
      const updatedProgress = updateProgress(progress, result.success, undefined, result.error);
      onProgress(updatedProgress);
    }

    return result;
  };

  const revertChange = (changeId: string): { success: boolean; error?: Error } => {
    console.log('🔄 TransformationManager: Reverting individual change:', changeId);

    const result = revertSingleTransformation(changeId, callbacks, state);

    console.log('🔄 TransformationManager: Individual revert result:', {
      success: result.success,
      error: result.error?.message
    });

    // Update progress for individual operations too
    if (onProgress) {
      const progress = createProgressTracker(1);
      const updatedProgress = updateProgress(progress, result.success, undefined, result.error);
      onProgress(updatedProgress);
    }

    return result;
  };

  const applyAllChanges = async (
    changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>
  ): Promise<ProgressTracker & { appliedChanges?: Array<{ change: SchemaAlignmentChangeDetail; index: number; columnIndex?: number }> }> => {
    const result = await executeBulkTransformations(
      changes,
      currentData,
      callbacks,
      state,
      onProgress
    );

    // If we have final data and a callback, update the parent component
    if (result.finalData && onFinalDataUpdate) {
      console.log('🔧 TransformationManager: Triggering final data update:', {
        rows: result.finalData.length,
        columns: result.finalData[0]?.length || 0,
        appliedChanges: result.appliedChanges?.length || 0
      });
      onFinalDataUpdate(result.finalData);
    }

    // If we have applied changes and a callback, notify about changes for UI tracking
    if (result.appliedChanges && result.appliedChanges.length > 0 && onAppliedChanges) {
      console.log('🔧 TransformationManager: Triggering applied changes callback:', result.appliedChanges.length);
      onAppliedChanges(result.appliedChanges);
    }

    return result;
  };

  const revertAllChanges = (
    changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>
  ): ProgressTracker => {
    return revertBulkTransformations(changes, callbacks, state, onProgress);
  };

  const executeSelectiveBulkOperationWrapper = async (
    config: SelectiveBulkConfig,
    changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>
  ): Promise<BulkOperationResult> => {
    return await executeSelectiveBulkOperation(
      config,
      changes,
      currentData[0] || [],
      callbacks,
      state,
      onProgress as any
    );
  };

  const previewBulkOperationWrapper = (
    config: SelectiveBulkConfig,
    changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>
  ): BulkOperationPreview => {
    return previewBulkOperation(config, changes, currentData[0] || []);
  };

  const checkConfirmationNeeded = (
    operationType: 'apply' | 'revert' | 'remove',
    changes: SchemaAlignmentChangeDetail[]
  ): ConfirmationDialogConfig | null => {
    const validation = validateConfirmationRequirements(
      operationType,
      changes,
      state.appliedChangeIds
    );

    if (!validation.requiresConfirmation) {
      return null;
    }

    return createConfirmationConfig(
      operationType,
      validation.affectedCount,
      operationType === 'remove' ? changes[0] : undefined,
      operationType === 'remove' ? 0 : undefined
    );
  };

  const getAppliedChanges = (): Set<string> => {
    return new Set(state.appliedChangeIds);
  };

  const isChangeApplied = (changeId: string): boolean => {
    return state.isApplied(changeId);
  };

  return {
    applyChange,
    revertChange,
    applyAllChanges,
    revertAllChanges,
    executeSelectiveBulkOperation: executeSelectiveBulkOperationWrapper,
    previewBulkOperation: previewBulkOperationWrapper,
    checkConfirmationNeeded,
    getAppliedChanges,
    isChangeApplied
  };
};

/**
 * Shared undo/redo functionality for transformations
 */
export interface UndoRedoManager {
  canUndo: () => boolean;
  canRedo: () => boolean;
  undo: () => Promise<{ success: boolean; error?: Error }>;
  redo: () => Promise<{ success: boolean; error?: Error }>;
  clearHistory: () => void;
  getHistorySize: () => { undoCount: number; redoCount: number };
}

interface TransformationHistoryEntry {
  type: 'apply' | 'revert';
  changeId: string;
  change: SchemaAlignmentChangeDetail;
  index: number;
  timestamp: Date;
}

/**
 * Creates an undo/redo manager for transformations
 */
export const createUndoRedoManager = (
  transformationManager: TransformationManager
): UndoRedoManager => {
  const undoStack: TransformationHistoryEntry[] = [];
  const redoStack: TransformationHistoryEntry[] = [];

  const canUndo = (): boolean => undoStack.length > 0;
  const canRedo = (): boolean => redoStack.length > 0;

  const undo = async (): Promise<{ success: boolean; error?: Error }> => {
    if (!canUndo()) {
      return { success: false, error: new Error('Nothing to undo') };
    }

    const entry = undoStack.pop()!;

    try {
      let result: { success: boolean; error?: Error };

      if (entry.type === 'apply') {
        // Undo an apply operation by reverting
        result = transformationManager.revertChange(entry.changeId);
      } else {
        // Undo a revert operation by re-applying
        result = await transformationManager.applyChange(entry.change, entry.index);
      }

      if (result.success) {
        // Add to redo stack with opposite operation
        redoStack.push({
          ...entry,
          type: entry.type === 'apply' ? 'revert' : 'apply'
        });
      }

      return result;
    } catch (error) {
      // Put the entry back if operation failed
      undoStack.push(entry);
      return { success: false, error: error instanceof Error ? error : new Error('Undo failed') };
    }
  };

  const redo = async (): Promise<{ success: boolean; error?: Error }> => {
    if (!canRedo()) {
      return { success: false, error: new Error('Nothing to redo') };
    }

    const entry = redoStack.pop()!;

    try {
      let result: { success: boolean; error?: Error };

      if (entry.type === 'apply') {
        // Redo an apply operation
        result = await transformationManager.applyChange(entry.change, entry.index);
      } else {
        // Redo a revert operation
        result = transformationManager.revertChange(entry.changeId);
      }

      if (result.success) {
        // Add to undo stack with opposite operation
        undoStack.push({
          ...entry,
          type: entry.type === 'apply' ? 'revert' : 'apply'
        });
      }

      return result;
    } catch (error) {
      // Put the entry back if operation failed
      redoStack.push(entry);
      return { success: false, error: error instanceof Error ? error : new Error('Redo failed') };
    }
  };

  const clearHistory = (): void => {
    undoStack.length = 0;
    redoStack.length = 0;
  };

  const getHistorySize = (): { undoCount: number; redoCount: number } => ({
    undoCount: undoStack.length,
    redoCount: redoStack.length
  });

  // Internal method to record operations (would be called by transformation manager)
  const recordOperation = (
    type: 'apply' | 'revert',
    changeId: string,
    change: SchemaAlignmentChangeDetail,
    index: number
  ): void => {
    undoStack.push({
      type,
      changeId,
      change,
      index,
      timestamp: new Date()
    });

    // Clear redo stack when new operation is performed
    redoStack.length = 0;
  };

  return {
    canUndo,
    canRedo,
    undo,
    redo,
    clearHistory,
    getHistorySize
  };
};

/**
 * Shared sequencing utilities for transformations
 */
export interface SequencingManager {
  validateSequence: (changes: SchemaAlignmentChangeDetail[]) => { isValid: boolean; conflicts: string[] };
  optimizeSequence: (changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>) => Array<{ change: SchemaAlignmentChangeDetail; index: number }>;
  estimateImpact: (changes: SchemaAlignmentChangeDetail[]) => {
    totalRowsAffected: number;
    columnsAffected: number;
    destructiveOperations: number;
    estimatedDuration: number;
  };
}

/**
 * Creates a sequencing manager for optimizing transformation order
 */
export const createSequencingManager = (): SequencingManager => {
  const validateSequence = (changes: SchemaAlignmentChangeDetail[]): { isValid: boolean; conflicts: string[] } => {
    const conflicts: string[] = [];
    const columnNames = new Set<string>();
    const pendingRenames = new Map<string, string>();
    const pendingAdds = new Set<string>();

    changes.forEach((change, index) => {
      switch (change.changeType.toLowerCase()) {
        case 'rename':
          if (change.originalColumn && change.newColumn) {
            if (pendingAdds.has(change.newColumn)) {
              conflicts.push(`Rename conflict at index ${index}: "${change.newColumn}" conflicts with pending addition`);
            }
            pendingRenames.set(change.originalColumn, change.newColumn);
          }
          break;

        case 'add':
          if (change.newColumn) {
            if (columnNames.has(change.newColumn) || pendingAdds.has(change.newColumn)) {
              conflicts.push(`Addition conflict at index ${index}: "${change.newColumn}" already exists`);
            } else if (Array.from(pendingRenames.values()).includes(change.newColumn)) {
              conflicts.push(`Addition conflict at index ${index}: "${change.newColumn}" conflicts with pending rename`);
            }
            pendingAdds.add(change.newColumn);
          }
          break;
      }
    });

    return {
      isValid: conflicts.length === 0,
      conflicts
    };
  };

  const optimizeSequence = (
    changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>
  ): Array<{ change: SchemaAlignmentChangeDetail; index: number }> => {
    // Group by operation type for optimal ordering
    const renames = changes.filter(({ change }) => change.changeType.toLowerCase() === 'rename');
    const additions = changes.filter(({ change }) => change.changeType.toLowerCase() === 'add');
    const removals = changes.filter(({ change }) => change.changeType.toLowerCase() === 'remove');

    // Optimal order: renames first (no conflicts), then additions, then removals
    return [...renames, ...additions, ...removals];
  };

  const estimateImpact = (changes: SchemaAlignmentChangeDetail[]): {
    totalRowsAffected: number;
    columnsAffected: number;
    destructiveOperations: number;
    estimatedDuration: number;
  } => {
    const totalRowsAffected = changes.reduce((sum, change) => sum + (change.rowCountAffected || 0), 0);
    const columnsAffected = changes.length;
    const destructiveOperations = changes.filter(change => change.changeType.toLowerCase() === 'remove').length;

    // Rough estimation: 100ms per change + 10ms per 1000 rows
    const estimatedDuration = (changes.length * 100) + (totalRowsAffected / 1000 * 10);

    return {
      totalRowsAffected,
      columnsAffected,
      destructiveOperations,
      estimatedDuration
    };
  };

  return {
    validateSequence,
    optimizeSequence,
    estimateImpact
  };
};
