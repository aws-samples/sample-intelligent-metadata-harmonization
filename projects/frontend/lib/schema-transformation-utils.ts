/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import { SchemaAlignmentChangeDetail } from './types';

/**
 * Utility functions for schema transformation operations
 * Provides shared logic for both individual and bulk operations
 */

export interface TransformationResult {
  success: boolean;
  error?: string;
  changeId?: string;
}

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

export interface TransformationSequence {
  renames: Array<{ change: SchemaAlignmentChangeDetail; index: number }>;
  additions: Array<{ change: SchemaAlignmentChangeDetail; index: number }>;
  removals: Array<{ change: SchemaAlignmentChangeDetail; index: number }>;
}

export interface TransformationStats {
  total: number;
  applied: number;
  pending: number;
  failed: number;
}

/**
 * Validates a schema change before applying it
 */
export const validateSchemaChange = (
  change: SchemaAlignmentChangeDetail,
  currentColumns: string[]
): ValidationResult => {
  const changeType = change.changeType.toLowerCase();

  switch (changeType) {
    case 'rename':
      if (!change.originalColumn || !change.newColumn) {
        return { isValid: false, error: 'Invalid rename change - missing column names' };
      }

      // Check if original column exists
      if (!currentColumns.includes(change.originalColumn)) {
        return { isValid: false, error: `Original column "${change.originalColumn}" not found` };
      }

      // Check if new column name already exists (and it's not the same column)
      if (currentColumns.includes(change.newColumn) && change.newColumn !== change.originalColumn) {
        return { isValid: false, error: `Target column name "${change.newColumn}" already exists` };
      }

      return { isValid: true };

    case 'add':
      if (!change.newColumn) {
        return { isValid: false, error: 'Invalid add change - missing column name' };
      }

      // Check if column name already exists
      if (currentColumns.includes(change.newColumn)) {
        return { isValid: false, error: `Column "${change.newColumn}" already exists` };
      }

      return { isValid: true };

    case 'remove':
      if (!change.originalColumn) {
        return { isValid: false, error: 'Invalid remove change - missing column name' };
      }

      // Check if column exists
      if (!currentColumns.includes(change.originalColumn)) {
        return { isValid: false, error: `Column "${change.originalColumn}" not found` };
      }

      // Check if this is the last column
      if (currentColumns.length <= 1) {
        return { isValid: false, error: 'Cannot remove last column' };
      }

      return { isValid: true };

    default:
      return { isValid: false, error: `Unknown change type: ${changeType}` };
  }
};

/**
 * Generates a consistent change ID for tracking
 */
export const generateChangeId = (
  change: SchemaAlignmentChangeDetail,
  index: number
): string => {
  return `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`;
};

/**
 * Orders changes for optimal execution sequence
 * Returns changes grouped by type in the correct order: renames, additions, removals
 */
export const orderChangesForExecution = (
  changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>
): TransformationSequence => {
  const renames = changes.filter(({ change }) => change.changeType.toLowerCase() === 'rename');
  const additions = changes.filter(({ change }) => change.changeType.toLowerCase() === 'add');
  const removals = changes.filter(({ change }) => change.changeType.toLowerCase() === 'remove');

  return { renames, additions, removals };
};

/**
 * Detects conflicts between pending changes
 */
export const detectChangeConflicts = (
  changes: SchemaAlignmentChangeDetail[],
  currentColumns: string[]
): string[] => {
  const conflicts: string[] = [];
  const columnNames = new Set(currentColumns);
  const pendingRenames = new Map<string, string>();
  const pendingAdds = new Set<string>();

  changes.forEach((change, index) => {
    switch (change.changeType.toLowerCase()) {
      case 'rename':
        if (change.originalColumn && change.newColumn) {
          // Check if target name conflicts with existing columns or other renames
          if (columnNames.has(change.newColumn) && change.newColumn !== change.originalColumn) {
            conflicts.push(`Rename conflict: "${change.newColumn}" already exists`);
          } else if (pendingAdds.has(change.newColumn)) {
            conflicts.push(`Rename conflict: "${change.newColumn}" conflicts with pending addition`);
          } else {
            pendingRenames.set(change.originalColumn, change.newColumn);
          }
        }
        break;

      case 'add':
        if (change.newColumn) {
          // Check if column name conflicts with existing columns or other operations
          if (columnNames.has(change.newColumn) || pendingAdds.has(change.newColumn)) {
            conflicts.push(`Addition conflict: "${change.newColumn}" already exists`);
          } else if (Array.from(pendingRenames.values()).includes(change.newColumn)) {
            conflicts.push(`Addition conflict: "${change.newColumn}" conflicts with pending rename`);
          } else {
            pendingAdds.add(change.newColumn);
          }
        }
        break;

      case 'remove':
        // Remove operations don't typically conflict with others
        break;
    }
  });

  return conflicts;
};

/**
 * Calculates transformation statistics
 */
export const calculateTransformationStats = (
  changes: SchemaAlignmentChangeDetail[],
  appliedChangeIds: Set<string>
): TransformationStats => {
  const total = changes.length;
  const applied = changes.filter((change, index) =>
    appliedChangeIds.has(generateChangeId(change, index))
  ).length;
  const pending = total - applied;

  return { total, applied, pending, failed: 0 };
};

/**
 * Checks if a change has destructive effects (data loss)
 */
export const isDestructiveChange = (change: SchemaAlignmentChangeDetail): boolean => {
  return change.changeType.toLowerCase() === 'remove';
};

/**
 * Checks if any changes in the list are destructive
 */
export const hasDestructiveChanges = (changes: SchemaAlignmentChangeDetail[]): boolean => {
  return changes.some(isDestructiveChange);
};

/**
 * Formats change description for user display
 */
export const formatChangeDescription = (change: SchemaAlignmentChangeDetail): string => {
  const changeType = change.changeType.toLowerCase();

  switch (changeType) {
    case 'rename':
      return `Rename "${change.originalColumn}" to "${change.newColumn}"`;
    case 'add':
      return `Add column "${change.newColumn}"`;
    case 'remove':
      return `Remove column "${change.originalColumn}"`;
    default:
      return `${change.changeType} transformation`;
  }
};

/**
 * Creates a preview of what will happen when changes are applied
 */
export const generateTransformationPreview = (
  changes: SchemaAlignmentChangeDetail[],
  appliedChangeIds: Set<string>
): {
  pendingChanges: SchemaAlignmentChangeDetail[];
  renameCount: number;
  addCount: number;
  removeCount: number;
  totalRowsAffected: number;
  hasDestructive: boolean;
} => {
  const pendingChanges = changes.filter((change, index) =>
    !appliedChangeIds.has(generateChangeId(change, index))
  );

  const renameCount = pendingChanges.filter(c => c.changeType.toLowerCase() === 'rename').length;
  const addCount = pendingChanges.filter(c => c.changeType.toLowerCase() === 'add').length;
  const removeCount = pendingChanges.filter(c => c.changeType.toLowerCase() === 'remove').length;

  const totalRowsAffected = pendingChanges.reduce((sum, change) =>
    sum + (change.rowCountAffected || 0), 0
  );

  const hasDestructive = hasDestructiveChanges(pendingChanges);

  return {
    pendingChanges,
    renameCount,
    addCount,
    removeCount,
    totalRowsAffected,
    hasDestructive
  };
};

/**
 * Error handling utilities
 */
export class TransformationError extends Error {
  constructor(
    message: string,
    public changeType: string,
    public columnName: string,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'TransformationError';
  }
}

/**
 * Wraps transformation operations with consistent error handling
 */
export const withErrorHandling = async <T>(
  operation: () => Promise<T> | T,
  changeType: string,
  columnName: string
): Promise<{ success: boolean; result?: T; error?: TransformationError }> => {
  try {
    const result = await operation();
    return { success: true, result };
  } catch (error) {
    const transformationError = new TransformationError(
      `Failed to ${changeType} column "${columnName}": ${error instanceof Error ? error.message : 'Unknown error'}`,
      changeType,
      columnName,
      error instanceof Error ? error : undefined
    );
    return { success: false, error: transformationError };
  }
};

/**
 * Progress tracking utilities for both individual and bulk operations
 */
export interface ProgressTracker {
  total: number;
  completed: number;
  failed: number;
  current?: string;
  errors: TransformationError[];
}

export const createProgressTracker = (total: number): ProgressTracker => ({
  total,
  completed: 0,
  failed: 0,
  errors: []
});

export const updateProgress = (
  tracker: ProgressTracker,
  success: boolean,
  current?: string,
  error?: TransformationError
): ProgressTracker => ({
  ...tracker,
  completed: tracker.completed + (success ? 1 : 0),
  failed: tracker.failed + (success ? 0 : 1),
  current,
  errors: error ? [...tracker.errors, error] : tracker.errors
});

/**
 * Shared transformation operation interface
 */
export interface TransformationOperation {
  changeType: string;
  originalColumn?: string;
  newColumn?: string;
  execute: () => void | Promise<void>;
}

/**
 * Shared transformation callbacks interface
 * Supports both individual operations (return void/boolean) and bulk operations (return updated data)
 */
export interface TransformationCallbacks {
  onApplyColumnRename?: (originalColumn: string, newColumn: string, workingData?: string[][]) => void | string[][];
  onApplyColumnAddition?: (newColumn: string, workingData?: string[][]) => void | string[][];
  onApplyColumnRemoval?: (columnName: string, workingData?: string[][]) => void | string[][];
  onRevertChange?: (changeId: string, workingData?: string[][]) => void | string[][];
}

/**
 * Shared state management interface
 */
export interface TransformationState {
  appliedChangeIds: Set<string>;
  markAsApplied: (changeId: string) => void;
  markAsReverted: (changeId: string) => void;
  isApplied: (changeId: string) => boolean;
}

/**
 * Creates a transformation operation from a schema change
 */
export const createTransformationOperation = (
  change: SchemaAlignmentChangeDetail,
  callbacks: TransformationCallbacks
): TransformationOperation => {
  const changeType = change.changeType.toLowerCase();
  const columnName = change.originalColumn || change.newColumn || 'unknown';

  console.log('🔧 createTransformationOperation: Creating operation for:', {
    changeType,
    originalColumn: change.originalColumn,
    newColumn: change.newColumn,
    columnName,
    availableCallbacks: {
      onApplyColumnRename: !!callbacks.onApplyColumnRename,
      onApplyColumnAddition: !!callbacks.onApplyColumnAddition,
      onApplyColumnRemoval: !!callbacks.onApplyColumnRemoval,
      onRevertChange: !!callbacks.onRevertChange
    }
  });

  return {
    changeType,
    originalColumn: change.originalColumn,
    newColumn: change.newColumn,
    execute: () => {
      console.log(`🔧 TransformationOperation: Executing ${changeType} operation`);

      switch (changeType) {
        case 'rename':
          if (!change.originalColumn || !change.newColumn) {
            console.error('❌ TransformationOperation: Invalid rename change - missing column names');
            throw new TransformationError(
              'Invalid rename change - missing column names',
              changeType,
              columnName
            );
          }
          if (!callbacks.onApplyColumnRename) {
            console.error('❌ TransformationOperation: onApplyColumnRename callback is missing');
            throw new TransformationError(
              'onApplyColumnRename callback is required for rename operations',
              changeType,
              columnName
            );
          }
          console.log(`🔧 TransformationOperation: Calling onApplyColumnRename(${change.originalColumn}, ${change.newColumn})`);
          callbacks.onApplyColumnRename(change.originalColumn, change.newColumn);
          console.log('✅ TransformationOperation: onApplyColumnRename completed');
          break;

        case 'add':
          if (!change.newColumn) {
            console.error('❌ TransformationOperation: Invalid add change - missing column name');
            throw new TransformationError(
              'Invalid add change - missing column name',
              changeType,
              columnName
            );
          }
          if (!callbacks.onApplyColumnAddition) {
            console.error('❌ TransformationOperation: onApplyColumnAddition callback is missing');
            throw new TransformationError(
              'onApplyColumnAddition callback is required for add operations',
              changeType,
              columnName
            );
          }
          console.log(`🔧 TransformationOperation: Calling onApplyColumnAddition(${change.newColumn})`);
          callbacks.onApplyColumnAddition(change.newColumn);
          console.log('✅ TransformationOperation: onApplyColumnAddition completed');
          break;

        case 'remove':
          if (!change.originalColumn) {
            console.error('❌ TransformationOperation: Invalid remove change - missing column name');
            throw new TransformationError(
              'Invalid remove change - missing column name',
              changeType,
              columnName
            );
          }
          if (!callbacks.onApplyColumnRemoval) {
            console.error('❌ TransformationOperation: onApplyColumnRemoval callback is missing');
            throw new TransformationError(
              'onApplyColumnRemoval callback is required for remove operations',
              changeType,
              columnName
            );
          }
          console.log(`🔧 TransformationOperation: Calling onApplyColumnRemoval(${change.originalColumn})`);
          callbacks.onApplyColumnRemoval(change.originalColumn);
          console.log('✅ TransformationOperation: onApplyColumnRemoval completed');
          break;

        default:
          console.error(`❌ TransformationOperation: Unknown change type: ${changeType}`);
          throw new TransformationError(
            `Unknown change type: ${changeType}`,
            changeType,
            columnName
          );
      }
    }
  };
};

/**
 * Executes a single transformation with comprehensive error handling and validation
 */
export const executeSingleTransformation = async (
  change: SchemaAlignmentChangeDetail,
  index: number,
  currentColumns: string[],
  callbacks: TransformationCallbacks,
  state: TransformationState
): Promise<{ success: boolean; error?: TransformationError }> => {
  const changeId = generateChangeId(change, index);
  const columnName = change.originalColumn || change.newColumn || 'unknown';

  console.log('🔧 executeSingleTransformation: Starting transformation:', {
    changeId,
    changeType: change.changeType,
    originalColumn: change.originalColumn,
    newColumn: change.newColumn,
    columnName
  });

  try {
    // Validate the change before applying
    const validation = validateSchemaChange(change, currentColumns);
    if (!validation.isValid) {
      console.error('❌ executeSingleTransformation: Validation failed:', validation.error);
      throw new TransformationError(
        validation.error || 'Validation failed',
        change.changeType,
        columnName
      );
    }

    console.log('✅ executeSingleTransformation: Validation passed, executing transformation');

    // Create and execute the transformation operation
    const operation = createTransformationOperation(change, callbacks);
    await operation.execute();

    console.log('✅ executeSingleTransformation: Transformation executed successfully');

    // Mark as applied on success
    state.markAsApplied(changeId);

    console.log('✅ executeSingleTransformation: Change marked as applied:', changeId);

    return { success: true };
  } catch (error) {
    console.error('❌ executeSingleTransformation: Transformation failed:', error);

    const transformationError = error instanceof TransformationError
      ? error
      : new TransformationError(
          `Failed to ${change.changeType} column "${columnName}": ${error instanceof Error ? error.message : 'Unknown error'}`,
          change.changeType,
          columnName,
          error instanceof Error ? error : undefined
        );

    return { success: false, error: transformationError };
  }
};

/**
 * Executes multiple transformations in sequence with progress tracking
 */
export const executeBulkTransformations = async (
  changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>,
  currentData: string[][],
  callbacks: TransformationCallbacks,
  state: TransformationState,
  onProgress?: (progress: ProgressTracker) => void
): Promise<ProgressTracker & { finalData?: string[][]; appliedChanges?: Array<{ change: SchemaAlignmentChangeDetail; index: number; columnIndex?: number }> }> => {
  // Order changes for optimal execution
  const orderedSequence = orderChangesForExecution(changes);
  const orderedChanges = [
    ...orderedSequence.renames,
    ...orderedSequence.additions,
    ...orderedSequence.removals
  ];

  let progress = createProgressTracker(orderedChanges.length);
  let workingColumns = currentData.length > 0 ? [...currentData[0]] : [];
  let workingData: string[][] = currentData.map(row => [...row]); // Start with full current data
  const appliedChanges: Array<{ change: SchemaAlignmentChangeDetail; index: number; columnIndex?: number }> = [];

  for (const { change, index } of orderedChanges) {
    const changeDescription = formatChangeDescription(change);
    const changeId = generateChangeId(change, index);

    console.log('🔧 executeBulkTransformations: Processing change with data accumulation:', {
      changeDescription,
      changeId,
      workingColumns
    });

    try {
      // Validate the change before applying
      const validation = validateSchemaChange(change, workingColumns);
      if (!validation.isValid) {
        console.error('❌ executeBulkTransformations: Validation failed:', validation.error);
        const error = new TransformationError(
          validation.error || 'Validation failed',
          change.changeType,
          change.originalColumn || change.newColumn || 'unknown'
        );
        progress = updateProgress(progress, false, changeDescription, error);
        continue;
      }

      // Apply transformation using bulk mode (with workingData parameter)
      let transformationResult: string[][] | void = undefined;

      switch (change.changeType.toLowerCase()) {
        case 'rename':
          if (change.originalColumn && change.newColumn && callbacks.onApplyColumnRename) {
            transformationResult = callbacks.onApplyColumnRename(
              change.originalColumn,
              change.newColumn,
              workingData
            ) as string[][];
          }
          break;
        case 'add':
          if (change.newColumn && callbacks.onApplyColumnAddition) {
            transformationResult = callbacks.onApplyColumnAddition(
              change.newColumn,
              workingData
            ) as string[][];
          }
          break;
        case 'remove':
          if (change.originalColumn && callbacks.onApplyColumnRemoval) {
            transformationResult = callbacks.onApplyColumnRemoval(
              change.originalColumn,
              workingData
            ) as string[][];
          }
          break;
        default:
          throw new TransformationError(
            `Unknown change type: ${change.changeType}`,
            change.changeType,
            change.originalColumn || change.newColumn || 'unknown'
          );
      }

      if (transformationResult && Array.isArray(transformationResult)) {
        // Update working data and columns for next iteration
        workingData = transformationResult;
        workingColumns = transformationResult[0];

        // Track applied change for UI change history
        const columnIndex = change.changeType.toLowerCase() === 'rename' && change.originalColumn
          ? currentData[0]?.findIndex(header => header === change.originalColumn)
          : change.changeType.toLowerCase() === 'remove' && change.originalColumn
          ? currentData[0]?.findIndex(header => header === change.originalColumn)
          : undefined;

        appliedChanges.push({
          change,
          index,
          columnIndex
        });

        console.log('📝 executeBulkTransformations: Tracked applied change for UI:', {
          changeType: change.changeType,
          originalColumn: change.originalColumn,
          newColumn: change.newColumn,
          columnIndex
        });

        // Mark as applied
        state.markAsApplied(changeId);

        progress = updateProgress(progress, true, changeDescription);
        console.log('✅ executeBulkTransformations: Change applied successfully:', {
          changeId,
          newColumns: workingColumns
        });
      } else {
        throw new TransformationError(
          `Transformation callback did not return data for bulk operation`,
          change.changeType,
          change.originalColumn || change.newColumn || 'unknown'
        );
      }
    } catch (error) {
      console.error('❌ executeBulkTransformations: Transformation failed:', error);

      const transformationError = error instanceof TransformationError
        ? error
        : new TransformationError(
            `Failed to ${change.changeType}: ${error instanceof Error ? error.message : 'Unknown error'}`,
            change.changeType,
            change.originalColumn || change.newColumn || 'unknown',
            error instanceof Error ? error : undefined
          );

      progress = updateProgress(progress, false, changeDescription, transformationError);
    }

    // Call progress callback if provided
    if (onProgress) {
      onProgress(progress);
    }
  }

  return { ...progress, finalData: workingData, appliedChanges };
};

/**
 * Updates column list after a successful transformation
 */
export const updateColumnsAfterChange = (
  columns: string[],
  change: SchemaAlignmentChangeDetail
): string[] => {
  const changeType = change.changeType.toLowerCase();

  switch (changeType) {
    case 'rename':
      if (change.originalColumn && change.newColumn) {
        return columns.map(col => col === change.originalColumn ? change.newColumn! : col);
      }
      break;
    case 'add':
      if (change.newColumn) {
        return [...columns, change.newColumn];
      }
      break;
    case 'remove':
      if (change.originalColumn) {
        return columns.filter(col => col !== change.originalColumn);
      }
      break;
  }

  return columns;
};

/**
 * Reverts a single transformation
 */
export const revertSingleTransformation = (
  changeId: string,
  callbacks: TransformationCallbacks,
  state: TransformationState
): { success: boolean; error?: TransformationError } => {
  console.log('🔄 revertSingleTransformation: Starting revert for changeId:', changeId);

  try {
    if (!callbacks.onRevertChange) {
      console.error('❌ revertSingleTransformation: onRevertChange callback is missing');
      throw new TransformationError(
        'onRevertChange callback is required for revert operations',
        'revert',
        changeId
      );
    }

    console.log('🔄 revertSingleTransformation: Calling onRevertChange callback');
    callbacks.onRevertChange(changeId);

    console.log('🔄 revertSingleTransformation: Marking change as reverted');
    state.markAsReverted(changeId);

    console.log('✅ revertSingleTransformation: Revert completed successfully');
    return { success: true };
  } catch (error) {
    console.error('❌ revertSingleTransformation: Revert failed:', error);

    const transformationError = error instanceof TransformationError
      ? error
      : new TransformationError(
          `Failed to revert change "${changeId}": ${error instanceof Error ? error.message : 'Unknown error'}`,
          'revert',
          changeId,
          error instanceof Error ? error : undefined
        );

    return { success: false, error: transformationError };
  }
};

/**
 * Reverts multiple transformations with progress tracking
 */
export const revertBulkTransformations = (
  changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>,
  callbacks: TransformationCallbacks,
  state: TransformationState,
  onProgress?: (progress: ProgressTracker) => void
): ProgressTracker => {
  // Filter to only applied changes
  const appliedChanges = changes.filter(({ change, index }) =>
    state.isApplied(generateChangeId(change, index))
  );

  let progress = createProgressTracker(appliedChanges.length);

  appliedChanges.forEach(({ change, index }) => {
    const changeId = generateChangeId(change, index);
    const changeDescription = formatChangeDescription(change);

    const result = revertSingleTransformation(changeId, callbacks, state);
    progress = updateProgress(progress, result.success, changeDescription, result.error);

    // Call progress callback if provided
    if (onProgress) {
      onProgress(progress);
    }
  });

  return progress;
};
