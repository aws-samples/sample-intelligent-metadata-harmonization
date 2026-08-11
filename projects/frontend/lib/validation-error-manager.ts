/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Validation Error Manager
 *
 * Handles validation error tracking and updates when manual data structure changes occur.
 * Provides functionality to re-evaluate validation errors after column/row operations.
 */

import {
  ValidationError,
  ValidationErrorPositionUpdate,
  ManualDataChange,
  ManualChangeValidationResult,
  ChangeHistoryEntry,
  ColumnOperation,
  RowOperation,
  ColumnContextMenuAction,
  RowContextMenuAction
} from './types';

export class ValidationErrorManager {
  private validationErrors: ValidationError[];
  private changeHistory: ChangeHistoryEntry[];
  private maxHistorySize: number;

  constructor(initialErrors: ValidationError[] = [], maxHistorySize: number = 50) {
    this.validationErrors = [...initialErrors];
    this.changeHistory = [];
    this.maxHistorySize = maxHistorySize;
  }

  /**
   * Update validation errors after a column rename operation
   */
  updateErrorsAfterColumnRename(
    originalColumnName: string,
    newColumnName: string,
    data: string[][]
  ): ValidationErrorPositionUpdate[] {
    const updates: ValidationErrorPositionUpdate[] = [];

    this.validationErrors.forEach(error => {
      if (error.column === originalColumnName) {
        // Update the column reference
        const updatedError: ValidationError = {
          ...error,
          column: newColumnName
        };

        updates.push({
          originalError: error,
          updatedError,
          wasAffected: true,
          updateReason: `Column renamed from "${originalColumnName}" to "${newColumnName}"`
        });
      } else {
        // Error not affected by this rename
        updates.push({
          originalError: error,
          updatedError: error,
          wasAffected: false,
          updateReason: 'Column not affected by rename'
        });
      }
    });

    // Apply updates
    this.validationErrors = updates
      .map(update => update.updatedError)
      .filter((error): error is ValidationError => error !== null);

    return updates;
  }

  /**
   * Update validation errors after a column addition operation
   */
  updateErrorsAfterColumnAdd(
    newColumnName: string,
    insertIndex: number,
    data: string[][]
  ): ValidationErrorPositionUpdate[] {
    const updates: ValidationErrorPositionUpdate[] = [];
    const columnNames = data[0] || [];

    this.validationErrors.forEach(error => {
      const errorColumnIndex = columnNames.indexOf(error.column);

      if (errorColumnIndex >= insertIndex) {
        // Column positions shifted, but error references remain the same
        // (since we reference by column name, not index)
        updates.push({
          originalError: error,
          updatedError: error,
          wasAffected: false,
          updateReason: 'Column position shifted but error reference unchanged'
        });
      } else {
        // Error not affected
        updates.push({
          originalError: error,
          updatedError: error,
          wasAffected: false,
          updateReason: 'Column not affected by addition'
        });
      }
    });

    return updates;
  }

  /**
   * Update validation errors after a column removal operation
   */
  updateErrorsAfterColumnRemove(
    removedColumnName: string,
    removedIndex: number,
    data: string[][]
  ): ValidationErrorPositionUpdate[] {
    const updates: ValidationErrorPositionUpdate[] = [];

    this.validationErrors.forEach(error => {
      if (error.column === removedColumnName) {
        // Remove errors for the deleted column
        updates.push({
          originalError: error,
          updatedError: null,
          wasAffected: true,
          updateReason: `Column "${removedColumnName}" was removed`
        });
      } else {
        // Error not affected by removal
        updates.push({
          originalError: error,
          updatedError: error,
          wasAffected: false,
          updateReason: 'Column not affected by removal'
        });
      }
    });

    // Apply updates - remove null errors
    this.validationErrors = updates
      .map(update => update.updatedError)
      .filter((error): error is ValidationError => error !== null);

    return updates;
  }

  /**
   * Update validation errors after a row addition operation
   */
  updateErrorsAfterRowAdd(
    insertRowIndex: number,
    data: string[][]
  ): ValidationErrorPositionUpdate[] {
    const updates: ValidationErrorPositionUpdate[] = [];

    this.validationErrors.forEach(error => {
      // Convert to 0-based data row index (error.row is 1-based including header)
      const errorDataRowIndex = error.row - 1;

      if (errorDataRowIndex >= insertRowIndex) {
        // Row numbers need to be shifted up
        const updatedError: ValidationError = {
          ...error,
          row: error.row + 1
        };

        updates.push({
          originalError: error,
          updatedError,
          wasAffected: true,
          updateReason: `Row number shifted from ${error.row} to ${error.row + 1} due to row insertion`
        });
      } else {
        // Error not affected
        updates.push({
          originalError: error,
          updatedError: error,
          wasAffected: false,
          updateReason: 'Row not affected by addition'
        });
      }
    });

    // Apply updates
    this.validationErrors = updates
      .map(update => update.updatedError)
      .filter((error): error is ValidationError => error !== null);

    return updates;
  }

  /**
   * Update validation errors after a row removal operation
   */
  updateErrorsAfterRowRemove(
    removedRowIndex: number,
    data: string[][]
  ): ValidationErrorPositionUpdate[] {
    const updates: ValidationErrorPositionUpdate[] = [];

    this.validationErrors.forEach(error => {
      // Convert to 0-based data row index (error.row is 1-based including header)
      // removedRowIndex is 0-based data row index
      const errorDataRowIndex = error.row - 1;

      if (errorDataRowIndex === removedRowIndex) {
        // Remove errors for the deleted row
        updates.push({
          originalError: error,
          updatedError: null,
          wasAffected: true,
          updateReason: `Row ${error.row} was removed`
        });
      } else if (errorDataRowIndex > removedRowIndex) {
        // Row numbers need to be shifted down
        const updatedError: ValidationError = {
          ...error,
          row: error.row - 1
        };

        updates.push({
          originalError: error,
          updatedError,
          wasAffected: true,
          updateReason: `Row number shifted from ${error.row} to ${error.row - 1} due to row removal`
        });
      } else {
        // Error not affected
        updates.push({
          originalError: error,
          updatedError: error,
          wasAffected: false,
          updateReason: 'Row not affected by removal'
        });
      }
    });

    // Apply updates - remove null errors
    this.validationErrors = updates
      .map(update => update.updatedError)
      .filter((error): error is ValidationError => error !== null);

    return updates;
  }

  /**
   * Validate a manual change before applying it
   */
  validateManualChange(
    operation: ColumnOperation | RowOperation,
    data: string[][],
    schemaRequirements?: any
  ): ManualChangeValidationResult {
    const result: ManualChangeValidationResult = {
      isValid: true,
      hasSchemaConflict: false,
      warnings: [],
      errors: [],
      affectedValidationErrors: [],
      suggestions: []
    };

    if ('columnIndex' in operation) {
      // Column operation
      return this.validateColumnOperation(operation, data, schemaRequirements);
    } else {
      // Row operation
      return this.validateRowOperation(operation, data, schemaRequirements);
    }
  }

  /**
   * Validate a column operation
   */
  private validateColumnOperation(
    operation: ColumnOperation,
    data: string[][],
    schemaRequirements?: any
  ): ManualChangeValidationResult {
    const result: ManualChangeValidationResult = {
      isValid: true,
      hasSchemaConflict: false,
      warnings: [],
      errors: [],
      affectedValidationErrors: [],
      suggestions: []
    };

    const columnNames = data[0] || [];
    const columnName = operation.columnName;

    switch (operation.action) {
      case ColumnContextMenuAction.RENAME:
        if (operation.newColumnName) {
          // Check for duplicate names
          if (columnNames.includes(operation.newColumnName) &&
              operation.newColumnName !== columnName) {
            result.isValid = false;
            result.errors.push(`Column name "${operation.newColumnName}" already exists`);
          }

          // Check schema conflicts
          if (schemaRequirements && this.checkSchemaConflict(operation.newColumnName, schemaRequirements)) {
            result.hasSchemaConflict = true;
            result.warnings.push(`Column name "${operation.newColumnName}" may not match schema requirements`);
          }

          // Find affected validation errors
          result.affectedValidationErrors = this.validationErrors.filter(
            error => error.column === columnName
          );
        }
        break;

      case ColumnContextMenuAction.REMOVE:
        // Check if removing this column will affect validation
        result.affectedValidationErrors = this.validationErrors.filter(
          error => error.column === columnName
        );

        if (result.affectedValidationErrors.length > 0) {
          result.warnings.push(
            `Removing this column will remove ${result.affectedValidationErrors.length} validation error(s)`
          );
        }

        // Check schema requirements
        if (schemaRequirements && this.isRequiredBySchema(columnName, schemaRequirements)) {
          result.hasSchemaConflict = true;
          result.warnings.push(`Column "${columnName}" may be required by the schema`);
          result.suggestions?.push('Consider renaming instead of removing this column');
        }
        break;

      case ColumnContextMenuAction.ADD_BEFORE:
      case ColumnContextMenuAction.ADD_AFTER:
        // Column addition is generally safe but may create schema conflicts
        if (schemaRequirements) {
          result.warnings.push('New column may need to match schema requirements');
          result.suggestions?.push('Ensure the new column name matches expected schema fields');
        }
        break;
    }

    return result;
  }

  /**
   * Validate a row operation
   */
  private validateRowOperation(
    operation: RowOperation,
    data: string[][],
    schemaRequirements?: any
  ): ManualChangeValidationResult {
    const result: ManualChangeValidationResult = {
      isValid: true,
      hasSchemaConflict: false,
      warnings: [],
      errors: [],
      affectedValidationErrors: [],
      suggestions: []
    };

    switch (operation.action) {
      case RowContextMenuAction.REMOVE:
        // Find affected validation errors
        result.affectedValidationErrors = this.validationErrors.filter(
          error => error.row === operation.rowIndex + 1 // Convert to 1-based
        );

        if (result.affectedValidationErrors.length > 0) {
          result.warnings.push(
            `Removing this row will remove ${result.affectedValidationErrors.length} validation error(s)`
          );
        }

        // Check if this is the last row
        if (data.length <= 2) { // Header + 1 data row
          result.warnings.push('Removing the last data row will leave the dataset empty');
        }
        break;

      case RowContextMenuAction.ADD_ABOVE:
      case RowContextMenuAction.ADD_BELOW:
        // Row addition is generally safe
        result.warnings.push('New row will need to be populated with valid data');
        break;
    }

    return result;
  }

  /**
   * Record a manual change in history for rollback functionality
   */
  recordChange(
    change: ManualDataChange,
    beforeState: string[][],
    afterState: string[][],
    beforeValidationErrors: ValidationError[],
    afterValidationErrors: ValidationError[]
  ): void {
    const historyEntry: ChangeHistoryEntry = {
      id: `history_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      change,
      beforeState: beforeState.map(row => [...row]),
      afterState: afterState.map(row => [...row]),
      beforeValidationErrors: [...beforeValidationErrors],
      afterValidationErrors: [...afterValidationErrors],
      canRollback: true
    };

    this.changeHistory.push(historyEntry);

    // Limit history size
    if (this.changeHistory.length > this.maxHistorySize) {
      this.changeHistory.shift();
    }
  }

  /**
   * Rollback to a previous state
   */
  rollbackToHistoryEntry(historyId: string): {
    success: boolean;
    restoredData?: string[][];
    restoredValidationErrors?: ValidationError[];
    error?: string;
  } {
    const historyEntry = this.changeHistory.find(entry => entry.id === historyId);

    if (!historyEntry) {
      return {
        success: false,
        error: 'History entry not found'
      };
    }

    if (!historyEntry.canRollback) {
      return {
        success: false,
        error: 'This change cannot be rolled back'
      };
    }

    // Restore validation errors
    this.validationErrors = [...historyEntry.beforeValidationErrors];

    return {
      success: true,
      restoredData: historyEntry.beforeState.map(row => [...row]),
      restoredValidationErrors: [...historyEntry.beforeValidationErrors]
    };
  }

  /**
   * Get current validation errors
   */
  getValidationErrors(): ValidationError[] {
    return [...this.validationErrors];
  }

  /**
   * Get change history
   */
  getChangeHistory(): ChangeHistoryEntry[] {
    return [...this.changeHistory];
  }

  /**
   * Clear change history
   */
  clearHistory(): void {
    this.changeHistory = [];
  }

  /**
   * Check if a column name conflicts with schema requirements
   */
  private checkSchemaConflict(columnName: string, schemaRequirements: any): boolean {
    // This would be implemented based on actual schema structure
    // For now, return false as a placeholder
    return false;
  }

  /**
   * Check if a column is required by the schema
   */
  private isRequiredBySchema(columnName: string, schemaRequirements: any): boolean {
    // This would be implemented based on actual schema structure
    // For now, return false as a placeholder
    return false;
  }

  /**
   * Re-evaluate all validation errors after manual data structure changes
   * This method should be called after any manual column or row operations
   */
  reEvaluateValidationErrors(
    updatedData: string[][],
    schemaRequirements?: any,
    affectedColumns?: string[],
    affectedRows?: number[]
  ): {
    updatedErrors: ValidationError[];
    removedErrors: ValidationError[];
    newErrors: ValidationError[];
    positionUpdates: ValidationErrorPositionUpdate[];
  } {
    const originalErrors = [...this.validationErrors];
    const positionUpdates: ValidationErrorPositionUpdate[] = [];
    const removedErrors: ValidationError[] = [];
    const newErrors: ValidationError[] = [];

    // Only re-evaluate errors that might be affected by the changes
    const updatedErrors = originalErrors.filter(error => {
      const columnExists = updatedData[0]?.includes(error.column);
      const rowExists = error.row <= updatedData.length;

      // If specific columns/rows were affected, only check those
      const isColumnAffected = !affectedColumns || affectedColumns.includes(error.column);
      const isRowAffected = !affectedRows || affectedRows.includes(error.row);

      // Only remove errors if they're in affected areas AND the column/row no longer exists
      if ((isColumnAffected || isRowAffected) && (!columnExists || !rowExists)) {
        removedErrors.push(error);
        positionUpdates.push({
          originalError: error,
          updatedError: null,
          wasAffected: true,
          updateReason: !columnExists ? 'Column no longer exists' : 'Row no longer exists'
        });
        return false;
      }

      // Error still valid, add to position updates as unchanged
      positionUpdates.push({
        originalError: error,
        updatedError: error,
        wasAffected: isColumnAffected || isRowAffected,
        updateReason: (isColumnAffected || isRowAffected) ? 'Error in affected area but still valid' : 'Error position unchanged'
      });
      return true;
    });

    // Update internal state
    this.validationErrors = updatedErrors;

    return {
      updatedErrors,
      removedErrors,
      newErrors, // Empty for now - would be populated by actual validation
      positionUpdates
    };
  }

  /**
   * Check if manual changes would create conflicts with schema requirements
   */
  checkSchemaConflicts(
    operation: ColumnOperation | RowOperation,
    data: string[][],
    schemaRequirements?: any
  ): {
    hasConflicts: boolean;
    conflicts: string[];
    warnings: string[];
    suggestions: string[];
  } {
    const result = {
      hasConflicts: false,
      conflicts: [] as string[],
      warnings: [] as string[],
      suggestions: [] as string[]
    };

    if (!schemaRequirements) {
      return result;
    }

    if ('columnIndex' in operation) {
      // Column operation
      switch (operation.action) {
        case 'rename':
          if (operation.newColumnName) {
            // Check if new name matches schema expectations
            if (this.isRequiredBySchema(operation.newColumnName, schemaRequirements)) {
              result.warnings.push(`Column "${operation.newColumnName}" matches a schema requirement`);
            } else {
              result.warnings.push(`Column "${operation.newColumnName}" may not match schema requirements`);
            }
          }
          break;
        case 'remove':
          if (this.isRequiredBySchema(operation.columnName, schemaRequirements)) {
            result.hasConflicts = true;
            result.conflicts.push(`Column "${operation.columnName}" is required by the schema`);
            result.suggestions.push('Consider renaming instead of removing this column');
          }
          break;
        case 'add_before':
        case 'add_after':
          result.warnings.push('New column should match schema field requirements');
          result.suggestions.push('Ensure the new column name matches expected schema fields');
          break;
      }
    } else {
      // Row operation - generally less likely to conflict with schema
      switch (operation.action) {
        case 'remove':
          const affectedErrors = this.validationErrors.filter(
            error => error.row === operation.rowIndex + 1
          );
          if (affectedErrors.length > 0) {
            result.warnings.push(
              `Removing this row will remove ${affectedErrors.length} validation error(s)`
            );
          }
          break;
      }
    }

    return result;
  }

  /**
   * Get manual changes that can be rolled back
   */
  getRollbackableChanges(): ChangeHistoryEntry[] {
    return this.changeHistory.filter(entry => entry.canRollback);
  }

  /**
   * Get manual changes with schema conflicts
   */
  getChangesWithConflicts(): ChangeHistoryEntry[] {
    return this.changeHistory.filter(entry => entry.change.hasSchemaConflict);
  }

  /**
   * Track manual vs automatic schema changes
   */
  markChangeAsManual(changeId: string, isManual: boolean = true): void {
    const historyEntry = this.changeHistory.find(entry => entry.id === changeId);
    if (historyEntry) {
      historyEntry.change.isManualChange = isManual;
    }
  }

  /**
   * Get change indicators for UI display
   */
  getChangeIndicators(): {
    totalChanges: number;
    manualChanges: number;
    automaticChanges: number;
    conflictingChanges: number;
    rollbackableChanges: number;
  } {
    const manualChanges = this.changeHistory.filter(entry => entry.change.isManualChange).length;
    const conflictingChanges = this.changeHistory.filter(entry => entry.change.hasSchemaConflict).length;
    const rollbackableChanges = this.changeHistory.filter(entry => entry.canRollback).length;

    return {
      totalChanges: this.changeHistory.length,
      manualChanges,
      automaticChanges: this.changeHistory.length - manualChanges,
      conflictingChanges,
      rollbackableChanges
    };
  }

  /**
   * Get statistics about validation errors and changes
   */
  getStatistics(): {
    totalValidationErrors: number;
    errorsByColumn: Record<string, number>;
    errorsByRow: Record<number, number>;
    totalChanges: number;
    manualChanges: number;
    changesWithConflicts: number;
  } {
    const errorsByColumn: Record<string, number> = {};
    const errorsByRow: Record<number, number> = {};

    this.validationErrors.forEach(error => {
      errorsByColumn[error.column] = (errorsByColumn[error.column] || 0) + 1;
      errorsByRow[error.row] = (errorsByRow[error.row] || 0) + 1;
    });

    const manualChanges = this.changeHistory.filter(entry => entry.change.isManualChange).length;
    const changesWithConflicts = this.changeHistory.filter(
      entry => entry.change.hasSchemaConflict
    ).length;

    return {
      totalValidationErrors: this.validationErrors.length,
      errorsByColumn,
      errorsByRow,
      totalChanges: this.changeHistory.length,
      manualChanges,
      changesWithConflicts
    };
  }
}

/**
 * Utility functions for validation error management
 */
export const ValidationErrorUtils = {
  /**
   * Create a manual data change object
   */
  createManualChange(
    type: ManualDataChange['type'],
    description: string,
    isManualChange: boolean = true,
    hasSchemaConflict: boolean = false,
    schemaConflictWarning?: string
  ): ManualDataChange {
    return {
      id: `manual_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      timestamp: new Date(),
      description,
      canUndo: true,
      hasSchemaConflict,
      schemaConflictWarning,
      affectedValidationErrors: [],
      isManualChange
    };
  },

  /**
   * Format validation error position updates for user display
   */
  formatPositionUpdates(updates: ValidationErrorPositionUpdate[]): string[] {
    return updates
      .filter(update => update.wasAffected)
      .map(update => {
        if (update.updatedError === null) {
          return `Removed error: ${update.originalError.column} (${update.updateReason})`;
        } else {
          return `Updated error: ${update.updateReason}`;
        }
      });
  },

  /**
   * Check if a manual change would create validation conflicts
   */
  wouldCreateConflicts(
    change: ManualDataChange,
    currentErrors: ValidationError[]
  ): boolean {
    return Boolean(change.affectedValidationErrors && change.affectedValidationErrors.length > 0);
  },

  /**
   * Create change indicators for UI display
   */
  createChangeIndicator(
    change: ManualDataChange,
    isApplied: boolean = false
  ): {
    type: 'manual' | 'automatic';
    status: 'pending' | 'applied' | 'conflict';
    icon: string;
    color: string;
    tooltip: string;
  } {
    const type = change.isManualChange ? 'manual' : 'automatic';
    let status: 'pending' | 'applied' | 'conflict' = isApplied ? 'applied' : 'pending';

    if (change.hasSchemaConflict) {
      status = 'conflict';
    }

    const indicators = {
      manual: {
        pending: { icon: '👤', color: '#1976d2', tooltip: 'Manual change pending' },
        applied: { icon: '✅', color: '#2e7d32', tooltip: 'Manual change applied' },
        conflict: { icon: '⚠️', color: '#ed6c02', tooltip: 'Manual change with schema conflict' }
      },
      automatic: {
        pending: { icon: '🤖', color: '#9c27b0', tooltip: 'Automatic change pending' },
        applied: { icon: '✅', color: '#2e7d32', tooltip: 'Automatic change applied' },
        conflict: { icon: '⚠️', color: '#ed6c02', tooltip: 'Automatic change with schema conflict' }
      }
    };

    return {
      type,
      status,
      ...indicators[type][status]
    };
  },

  /**
   * Format change history for user display
   */
  formatChangeHistory(history: ChangeHistoryEntry[]): Array<{
    id: string;
    description: string;
    timestamp: string;
    type: string;
    canRollback: boolean;
    hasConflict: boolean;
    affectedErrors: number;
  }> {
    return history.map(entry => ({
      id: entry.id,
      description: entry.change.description,
      timestamp: entry.change.timestamp.toLocaleString(),
      type: entry.change.isManualChange ? 'Manual' : 'Automatic',
      canRollback: entry.canRollback,
      hasConflict: entry.change.hasSchemaConflict || false,
      affectedErrors: entry.change.affectedValidationErrors?.length || 0
    }));
  },

  /**
   * Generate rollback confirmation message
   */
  generateRollbackMessage(
    change: ManualDataChange,
    affectedErrors: number
  ): {
    title: string;
    message: string;
    warnings: string[];
  } {
    const warnings: string[] = [];

    if (affectedErrors > 0) {
      warnings.push(`This will restore ${affectedErrors} validation error(s)`);
    }

    if (change.hasSchemaConflict) {
      warnings.push('This change had schema conflicts');
    }

    return {
      title: `Rollback ${change.type.replace('_', ' ')}?`,
      message: `Are you sure you want to rollback: ${change.description}`,
      warnings
    };
  },

  /**
   * Validate manual change against current data state
   */
  validateManualChangeAgainstData(
    change: ManualDataChange,
    currentData: string[][],
    validationErrors: ValidationError[]
  ): {
    isValid: boolean;
    canApply: boolean;
    warnings: string[];
    errors: string[];
  } {
    const result = {
      isValid: true,
      canApply: true,
      warnings: [] as string[],
      errors: [] as string[]
    };

    // Check if the change is still applicable to current data state
    switch (change.type) {
      case 'column_rename':
        // Check if original column still exists
        // This would require more metadata about the change
        break;
      case 'column_add':
        // Check if column name would conflict
        break;
      case 'column_remove':
        // Check if column still exists
        break;
      case 'row_add':
      case 'row_remove':
        // Check row bounds
        break;
    }

    // Check for validation error impacts
    if (change.affectedValidationErrors && change.affectedValidationErrors.length > 0) {
      const stillRelevantErrors = change.affectedValidationErrors.filter(error =>
        validationErrors.some(currentError =>
          currentError.row === error.row && currentError.column === error.column
        )
      );

      if (stillRelevantErrors.length > 0) {
        result.warnings.push(
          `This change will affect ${stillRelevantErrors.length} current validation error(s)`
        );
      }
    }

    return result;
  }
};
