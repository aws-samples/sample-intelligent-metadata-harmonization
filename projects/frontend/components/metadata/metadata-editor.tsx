/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState, useEffect } from 'react';
import { Box, Snackbar, Alert } from '@mui/material';
import { SpreadsheetEditorComponent, Change } from './spreadsheet-editor';
import {
  ValidationError,
  ValidationStatusResponse,
  SchemaAlignmentResults,
  SchemaAlignmentChangeDetail,
  TransformationSummary,
  SchemaAlignmentChange,
  ManualDataChange,
  ManualChangeValidationResult,
  ValidationErrorPositionUpdate,
  ChangeHistoryEntry,
  ChangeTrackingResults
} from '../../lib/types';
import { ValidationErrorManager, ValidationErrorUtils } from '../../lib/validation-error-manager';
import { ValidationSidebarComponent } from './validation-sidebar';
import { ErrorCardComponent } from './error-card';
import { ChangeHistoryPanel } from './change-history-panel';
import { parseCSV } from '../../lib/csv-utils';
import { generateSchemaAlignmentChangesFromDetails } from '../../lib/utils';

interface MetadataEditorProps {
  csvData: string[][];
  validationErrors?: ValidationError[] | null;
  jobId?: string;
  coreSchemaId?: string;
  programSchemaId?: string;
  schemaAlignmentResults?: SchemaAlignmentResults;
  onValidationComplete: (jobId?: string, changeTracking?: ChangeTrackingResults) => void;
  onValidationErrors: (errors: ValidationError[], jobId?: string, schemaAlignmentResults?: SchemaAlignmentResults) => void;
}

export const MetadataEditorComponent: React.FC<MetadataEditorProps> = ({
  csvData,
  validationErrors = null,
  jobId,
  coreSchemaId,
  programSchemaId,
  schemaAlignmentResults,
  onValidationComplete,
  onValidationErrors
}) => {
  console.log('🏗️ MetadataEditor: Component initialized with props:', {
    csvDataLength: csvData?.length || 0,
    csvDataPreview: csvData?.slice(0, 3) || [],
    validationErrorsCount: validationErrors?.length || 0,
    jobId,
    coreSchemaId,
    programSchemaId,
    hasOnValidationComplete: !!onValidationComplete,
    hasOnValidationErrors: !!onValidationErrors
  });

  // State management for single data view with schema changes applied directly
  const [currentData, setCurrentData] = useState<string[][]>(csvData);
  const [originalData, setOriginalData] = useState<string[][]>(csvData);
  const [transformationSummary, setTransformationSummary] = useState<TransformationSummary | undefined>();

  const [changes, setChanges] = useState<Change[]>([]);
  const [currentErrors, setCurrentErrors] = useState<ValidationError[]>(validationErrors || []);
  const [schemaAlignmentChanges, setSchemaAlignmentChanges] = useState<SchemaAlignmentChangeDetail[]>([]);
  const [appliedSchemaChanges, setAppliedSchemaChanges] = useState<Set<string>>(new Set());
  const [spreadsheetDisabled, setSpreadsheetDisabled] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [showErrorSnackbar, setShowErrorSnackbar] = useState(false);
  const [manualChanges, setManualChanges] = useState<ManualDataChange[]>([]);
  const [validationErrorUpdates, setValidationErrorUpdates] = useState<ValidationErrorPositionUpdate[]>([]);
  const [validationErrorManager, setValidationErrorManager] = useState<ValidationErrorManager | null>(null);
  const [changeHistory, setChangeHistory] = useState<ChangeHistoryEntry[]>([]);
  const [schemaConflictWarnings, setSchemaConflictWarnings] = useState<string[]>([]);

  // Initialize validation error manager
  useEffect(() => {
    const manager = new ValidationErrorManager(currentErrors);
    setValidationErrorManager(manager);
  }, []);

  // Monitor data changes to ensure UI updates properly
  useEffect(() => {
    console.log('🔄 MetadataEditor: currentData changed, rows:', currentData.length, 'columns:', currentData[0]?.length);

    // Log column headers for debugging schema changes
    if (currentData.length > 0) {
      console.log('📋 MetadataEditor: Current column headers:', currentData[0]);
    }
  }, [currentData]);


  // Update validation error manager when errors change
  useEffect(() => {
    if (validationErrorManager) {
      // Create a new manager with updated errors
      const updatedManager = new ValidationErrorManager(currentErrors);
      setValidationErrorManager(updatedManager);
    }
  }, [currentErrors]);

  // Enhanced validation error re-evaluation after manual changes
  // Enhanced validation error re-evaluation after manual changes
  // NOTE: This function is kept for backward compatibility but should not be used for structural changes
  // Use specific update methods (updateErrorsAfterColumnRename, etc.) instead
  const reEvaluateValidationErrors = (
    updatedData: string[][],
    changeDescription: string,
    affectedColumns?: string[],
    affectedRows?: number[]
  ) => {
    if (!validationErrorManager) return;

    console.log('🔄 MetadataEditor: Re-evaluating validation errors after change:', changeDescription);
    console.warn('⚠️ MetadataEditor: Using generic reEvaluateValidationErrors - consider using specific update methods');

    // For generic re-evaluation, be very conservative and don't remove errors
    // unless we're absolutely sure they're invalid
    const currentValidationErrors = validationErrorManager.getValidationErrors();

    console.log('✅ MetadataEditor: Validation errors preserved (no changes made):', {
      currentCount: currentValidationErrors.length,
      changeDescription
    });

    // Just update the state without removing any errors
    setCurrentErrors(currentValidationErrors);

    // Notify parent component about validation error updates
    onValidationErrors(currentValidationErrors, jobId, schemaAlignmentResults);
  };

  // Check for schema conflicts before applying manual changes
  const checkSchemaConflicts = (operation: any, description: string): boolean => {
    if (!validationErrorManager) return false;

    const conflictCheck = validationErrorManager.checkSchemaConflicts(operation, currentData);

    if (conflictCheck.hasConflicts || conflictCheck.warnings.length > 0) {
      const allMessages = [...conflictCheck.conflicts, ...conflictCheck.warnings];
      setSchemaConflictWarnings(allMessages);

      console.log('⚠️ MetadataEditor: Schema conflicts detected for change:', description, allMessages);

      // Show warning but allow user to proceed
      showError(`Warning: ${allMessages.join('; ')}. You can proceed but this may affect validation.`);

      return conflictCheck.hasConflicts;
    }

    return false;
  };

  // Record manual change in history with validation integration
  const recordManualChange = (
    change: ManualDataChange,
    beforeData: string[][],
    afterData: string[][],
    beforeErrors: ValidationError[],
    afterErrors: ValidationError[]
  ) => {
    if (!validationErrorManager) return;

    // Record in validation error manager
    validationErrorManager.recordChange(change, beforeData, afterData, beforeErrors, afterErrors);

    // Update local change history state
    const updatedHistory = validationErrorManager.getChangeHistory();
    setChangeHistory(updatedHistory);

    // Update manual changes state
    setManualChanges(prev => [...prev, change]);

    console.log('📝 MetadataEditor: Manual change recorded:', {
      changeId: change.id,
      type: change.type,
      description: change.description,
      hasConflict: change.hasSchemaConflict,
      affectedErrors: change.affectedValidationErrors?.length || 0
    });
  };

  // Rollback manual change with validation restoration
  const rollbackManualChange = (changeId: string) => {
    if (!validationErrorManager) {
      showError('Cannot rollback: validation error manager not available');
      return;
    }

    console.log('🔄 MetadataEditor: Rolling back manual change:', changeId);

    const rollbackResult = validationErrorManager.rollbackToHistoryEntry(changeId);

    if (rollbackResult.success && rollbackResult.restoredData && rollbackResult.restoredValidationErrors) {
      // Restore data state
      setCurrentData(rollbackResult.restoredData);

      // Restore validation errors
      setCurrentErrors(rollbackResult.restoredValidationErrors);

      // Update change history
      const updatedHistory = validationErrorManager.getChangeHistory();
      setChangeHistory(updatedHistory);

      // Notify parent component
      onValidationErrors(rollbackResult.restoredValidationErrors, jobId, schemaAlignmentResults);

      console.log('✅ MetadataEditor: Manual change rolled back successfully');
      showError('Change rolled back successfully');
    } else {
      console.error('❌ MetadataEditor: Failed to rollback change:', rollbackResult.error);
      showError(rollbackResult.error || 'Failed to rollback change');
    }
  };

  // Schema transformation methods with enhanced validation and error handling
  const applyColumnRename = (originalColumn: string, newColumn: string, workingData?: string[][]): boolean | string[][] => {
    console.log('🔧 MetadataEditor: Applying column rename:', { originalColumn, newColumn, isBulkMode: !!workingData });

    // Validation checks
    if (!originalColumn || !newColumn) {
      const errorMsg = 'Cannot rename column: both original and new column names are required';
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return false; // Fail individual operation
    }

    if (originalColumn === newColumn) {
      console.log('ℹ️ MetadataEditor: Column names are identical, no change needed');
      return workingData || true; // Return data in bulk mode, boolean in individual mode
    }

    // Choose data source: workingData for bulk operations, currentData for individual
    const sourceData = workingData || currentData;
    const newData = sourceData.map(row => [...row]);
    const headerRow = newData[0];
    const columnIndex = headerRow.findIndex(header => header === originalColumn);

    if (columnIndex === -1) {
      const errorMsg = `Cannot find column "${originalColumn}" to rename`;
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return false; // Fail individual operation
    }

    // Check if new column name already exists (and it's not the same column)
    const existingIndex = headerRow.findIndex(header => header === newColumn);
    if (existingIndex !== -1 && existingIndex !== columnIndex) {
      const errorMsg = `Cannot rename column: "${newColumn}" already exists`;
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return false; // Fail individual operation
    }

    // Apply the rename
    headerRow[columnIndex] = newColumn;

    if (workingData) {
      // BULK MODE: Return updated data without side effects
      console.log('✅ MetadataEditor: Column rename applied in bulk mode');
      return newData;
    } else {
      // INDIVIDUAL MODE: Update React state and perform side effects
      // Create manual change object for validation tracking
      const manualChange = ValidationErrorUtils.createManualChange(
        'column_rename',
        `Renamed column "${originalColumn}" to "${newColumn}"`,
        true
      );

      // Check for schema conflicts
      const operation = {
        action: 'rename' as any,
        columnIndex,
        columnName: originalColumn,
        newColumnName: newColumn
      };

      const hasConflicts = checkSchemaConflicts(operation, manualChange.description);
      manualChange.hasSchemaConflict = hasConflicts;

      if (hasConflicts && schemaConflictWarnings.length > 0) {
        manualChange.schemaConflictWarning = schemaConflictWarnings.join('; ');
      }

      // Store before state for rollback
      const beforeData = currentData.map(row => [...row]);
      const beforeErrors = [...currentErrors];

      // Update React state
      setCurrentData(newData);

      // Note: Validation errors are preserved as-is during schema changes
      // No automatic error removal or position updates are performed

      // Record the manual change in history
      recordManualChange(manualChange, beforeData, newData, beforeErrors, currentErrors);

      // Mark this change as applied - find the change index to generate consistent ID
      const changeIndex = schemaAlignmentChanges.findIndex(change =>
        change.changeType === 'rename' &&
        change.originalColumn === originalColumn &&
        change.newColumn === newColumn
      );

      if (changeIndex !== -1) {
        const changeId = `rename-${originalColumn}-${changeIndex}`;
        setAppliedSchemaChanges(prev => new Set([...prev, changeId]));
        console.log('🔧 MetadataEditor: Marked rename change as applied:', changeId);
      } else {
        console.warn('⚠️ MetadataEditor: Could not find matching schema change for rename');
      }

      // Add to changes history for tracking
      const change: Change = {
        row: 0, // Header row
        column: columnIndex,
        oldValue: originalColumn,
        newValue: newColumn,
        timestamp: new Date()
      };
      setChanges(prev => [...prev, change]);

      console.log('✅ MetadataEditor: Column rename applied successfully with validation integration');
      return true;
    }
  };

  const applyColumnAddition = (newColumn: string, workingData?: string[][]): boolean | string[][] => {
    console.log('🔧 MetadataEditor: Applying column addition:', { newColumn, isBulkMode: !!workingData });

    // Validation checks
    if (!newColumn || newColumn.trim() === '') {
      const errorMsg = 'Cannot add column: column name is required';
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return false; // Fail individual operation
    }

    // Choose data source: workingData for bulk operations, currentData for individual
    const sourceData = workingData || currentData;
    const headerRow = sourceData[0];
    if (headerRow.includes(newColumn)) {
      const errorMsg = `Cannot add column: "${newColumn}" already exists`;
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return false; // Fail individual operation
    }

    // Apply the addition
    const newData = sourceData.map((row, index) => {
      if (index === 0) {
        // Header row - add new column name
        return [...row, newColumn];
      } else {
        // Data rows - add empty value
        return [...row, ''];
      }
    });

    if (workingData) {
      // BULK MODE: Return updated data without side effects
      console.log('✅ MetadataEditor: Column addition applied in bulk mode');
      return newData;
    }

    // INDIVIDUAL MODE: Update React state and perform side effects
    // Create manual change object for validation tracking
    const manualChange = ValidationErrorUtils.createManualChange(
      'column_add',
      `Added column "${newColumn}"`,
      true
    );

    // Check for schema conflicts
    const operation = {
      action: 'add_after' as any,
      columnIndex: headerRow.length,
      columnName: '',
      newColumnName: newColumn
    };

    const hasConflicts = checkSchemaConflicts(operation, manualChange.description);
    manualChange.hasSchemaConflict = hasConflicts;

    if (hasConflicts && schemaConflictWarnings.length > 0) {
      manualChange.schemaConflictWarning = schemaConflictWarnings.join('; ');
    }

    // Store before state for rollback
    const beforeData = currentData.map(row => [...row]);
    const beforeErrors = [...currentErrors];

    setCurrentData(newData);

    // Note: Validation errors are preserved as-is during schema changes
    // No automatic error removal or position updates are performed

    // Record the manual change in history
    recordManualChange(manualChange, beforeData, newData, beforeErrors, currentErrors);

    // Mark this change as applied - find the change index to generate consistent ID
    const changeIndex = schemaAlignmentChanges.findIndex(change =>
      change.changeType === 'add' &&
      change.newColumn === newColumn
    );

    if (changeIndex !== -1) {
      const changeId = `add-${newColumn}-${changeIndex}`;
      setAppliedSchemaChanges(prev => new Set([...prev, changeId]));
      console.log('🔧 MetadataEditor: Marked addition change as applied:', changeId);
    } else {
      console.warn('⚠️ MetadataEditor: Could not find matching schema change for addition');
    }

    // Add to changes history for tracking
    const change: Change = {
      row: 0, // Header row
      column: headerRow.length, // New column index
      oldValue: '',
      newValue: newColumn,
      timestamp: new Date()
    };
    setChanges(prev => [...prev, change]);

    console.log('✅ MetadataEditor: Column addition applied successfully');
    return true;
  };

  const applyColumnRemoval = (columnName: string, workingData?: string[][]): boolean | string[][] => {
    console.log('🔧 MetadataEditor: Applying column removal:', { columnName, isBulkMode: !!workingData });

    // Validation checks
    if (!columnName) {
      const errorMsg = 'Cannot remove column: column name is required';
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return false; // Fail individual operation
    }

    // Choose data source: workingData for bulk operations, currentData for individual
    const sourceData = workingData || currentData;
    const headerRow = sourceData[0];
    const columnIndex = headerRow.findIndex(header => header === columnName);

    if (columnIndex === -1) {
      const errorMsg = `Cannot find column "${columnName}" to remove`;
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return false; // Fail individual operation
    }

    // Check if this is the last column
    if (headerRow.length <= 1) {
      const errorMsg = 'Cannot remove column: at least one column must remain';
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return false; // Fail individual operation
    }

    // Apply the removal
    const newData = sourceData.map(row => {
      const newRow = [...row];
      newRow.splice(columnIndex, 1);
      return newRow;
    });

    if (workingData) {
      // BULK MODE: Return updated data without side effects
      console.log('✅ MetadataEditor: Column removal applied in bulk mode');
      return newData;
    }

    // INDIVIDUAL MODE: Update React state and perform side effects
    // Create manual change object for validation tracking
    const manualChange = ValidationErrorUtils.createManualChange(
      'column_remove',
      `Removed column "${columnName}"`,
      true
    );

    // Check for schema conflicts
    const operation = {
      action: 'remove' as any,
      columnIndex,
      columnName
    };

    const hasConflicts = checkSchemaConflicts(operation, manualChange.description);
    manualChange.hasSchemaConflict = hasConflicts;

    if (hasConflicts && schemaConflictWarnings.length > 0) {
      manualChange.schemaConflictWarning = schemaConflictWarnings.join('; ');
    }

    // Store before state for rollback
    const beforeData = currentData.map(row => [...row]);
    const beforeErrors = [...currentErrors];

    setCurrentData(newData);

    // Note: Validation errors are preserved as-is during schema changes
    // No automatic error removal or position updates are performed

    // Record the manual change in history
    recordManualChange(manualChange, beforeData, newData, beforeErrors, currentErrors);

    // Mark this change as applied - find the change index to generate consistent ID
    const changeIndex = schemaAlignmentChanges.findIndex(change =>
      change.changeType === 'remove' &&
      change.originalColumn === columnName
    );

    if (changeIndex !== -1) {
      const changeId = `remove-${columnName}-${changeIndex}`;
      setAppliedSchemaChanges(prev => new Set([...prev, changeId]));
      console.log('🔧 MetadataEditor: Marked removal change as applied:', changeId);
    } else {
      console.warn('⚠️ MetadataEditor: Could not find matching schema change for removal');
    }

    // Add to changes history for tracking
    const change: Change = {
      row: 0, // Header row
      column: columnIndex,
      oldValue: columnName,
      newValue: '',
      timestamp: new Date()
    };
    setChanges(prev => [...prev, change]);

    console.log('✅ MetadataEditor: Column removal applied successfully');
    return true;
  };

  const revertSchemaChange = (changeId: string, workingData?: string[][]): void | string[][] => {
    console.log('🔄 MetadataEditor: Reverting schema change with ID:', changeId, 'isBulkMode:', !!workingData);

    // Parse changeId to understand what to reverse
    // Format: "changeType-columnInfo-index"
    const parts = changeId.split('-');
    if (parts.length < 3) {
      const errorMsg = `Invalid change ID format: ${changeId}`;
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return; // Fail individual operation
    }

    const changeType = parts[0];
    const changeIndex = parseInt(parts[parts.length - 1], 10);

    // Find the change detail
    const changeDetail = schemaAlignmentChanges[changeIndex];
    if (!changeDetail) {
      const errorMsg = `Could not find change detail for ID: ${changeId}`;
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw new Error(errorMsg); // Stop bulk operation
      }
      return; // Fail individual operation
    }

    // For individual mode, check if change is currently applied
    if (!workingData && !appliedSchemaChanges.has(changeId)) {
      console.log('ℹ️ MetadataEditor: Change is not currently applied, nothing to revert');
      showError('Change is not currently applied');
      return;
    }

    // Apply reverse transformation based on the change type
    console.log('🔄 MetadataEditor: Applying reverse transformation for:', changeType, changeDetail);

    try {
      switch (changeType.toLowerCase()) {
        case 'rename':
          // Reverse a rename: rename back from new column to original column
          if (changeDetail.newColumn && changeDetail.originalColumn) {
            return applyColumnRename(changeDetail.newColumn, changeDetail.originalColumn, workingData) as any;
          }
          break;

        case 'add':
          // Reverse an addition: remove the added column
          if (changeDetail.newColumn) {
            return applyColumnRemoval(changeDetail.newColumn, workingData) as any;
          }
          break;

        case 'remove':
          // Reverse a removal: add the removed column back (with empty values)
          if (changeDetail.originalColumn) {
            return applyColumnAddition(changeDetail.originalColumn, workingData) as any;
          }
          break;

        default:
          const errorMsg = `Unknown change type for revert: ${changeType}`;
          showError(errorMsg); // Always show user feedback

          if (workingData) {
            throw new Error(errorMsg); // Stop bulk operation
          }
          return; // Fail individual operation
      }
    } catch (error) {
      const errorMsg = `Failed to revert ${changeType}: ${error instanceof Error ? error.message : 'Unknown error'}`;
      showError(errorMsg); // Always show user feedback

      if (workingData) {
        throw error; // Re-throw for bulk operation
      }
      return; // Fail individual operation
    }

    // For individual mode only: Remove from applied changes and update tracking
    if (!workingData) {
      // Remove this change from applied changes
      setAppliedSchemaChanges(prev => {
        const newSet = new Set(prev);
        newSet.delete(changeId);
        return newSet;
      });

      console.log('✅ MetadataEditor: Schema change reverted successfully:', changeId);
    }
  };

  // Manual row operations with validation integration
  const applyRowAddition = (insertIndex: number, position: 'above' | 'below' = 'below') => {
    console.log('🔧 MetadataEditor: Applying row addition:', { insertIndex, position });

    // Validation checks
    if (insertIndex < 0 || insertIndex >= currentData.length - 1) {
      showError('Cannot add row: invalid row position');
      return;
    }

    // Create manual change object for validation tracking
    const manualChange = ValidationErrorUtils.createManualChange(
      'row_add',
      `Added row ${position} row ${insertIndex + 1}`,
      true
    );

    // Check for schema conflicts (minimal for row operations)
    const operation = {
      action: position === 'above' ? 'add_above' as any : 'add_below' as any,
      rowIndex: insertIndex,
      insertPosition: position
    };

    const hasConflicts = checkSchemaConflicts(operation, manualChange.description);
    manualChange.hasSchemaConflict = hasConflicts;

    // Store before state for rollback
    const beforeData = currentData.map(row => [...row]);
    const beforeErrors = [...currentErrors];

    // Calculate actual insertion index (accounting for header row)
    const actualInsertIndex = position === 'above' ? insertIndex + 1 : insertIndex + 2;

    // Create new empty row with same number of columns
    const newRow = new Array(currentData[0].length).fill('');

    // Apply the addition
    const newData = [...currentData];
    newData.splice(actualInsertIndex, 0, newRow);

    setCurrentData(newData);

    // Note: Validation errors are preserved as-is during schema changes
    // No automatic error removal or position updates are performed

    // Record the manual change in history
    recordManualChange(manualChange, beforeData, newData, beforeErrors, currentErrors);

    // Add to changes history for tracking
    const change: Change = {
      row: actualInsertIndex - 1, // Convert to 0-based data row index
      column: 0,
      oldValue: '',
      newValue: 'New row added',
      timestamp: new Date()
    };
    setChanges(prev => [...prev, change]);

    console.log('✅ MetadataEditor: Row addition applied successfully');
  };

  const applyRowRemoval = (rowIndex: number) => {
    console.log('🔧 MetadataEditor: Applying row removal:', { rowIndex });

    // Validation checks
    if (rowIndex < 0 || rowIndex >= currentData.length - 1) {
      showError('Cannot remove row: invalid row position');
      return;
    }

    // Check if this is the last data row
    if (currentData.length <= 2) { // Header + 1 data row
      showError('Cannot remove row: at least one data row must remain');
      return;
    }

    // Create manual change object for validation tracking
    const rowData = currentData[rowIndex + 1]; // Account for header row
    const affectedCells = rowData.filter(cell => cell && cell.trim() !== '').length;

    const manualChange = ValidationErrorUtils.createManualChange(
      'row_remove',
      `Removed row ${rowIndex + 1} (${affectedCells} cells affected)`,
      true
    );

    // Check for schema conflicts and affected validation errors
    const operation = {
      action: 'remove' as any,
      rowIndex
    };

    const hasConflicts = checkSchemaConflicts(operation, manualChange.description);
    manualChange.hasSchemaConflict = hasConflicts;

    // Store before state for rollback
    const beforeData = currentData.map(row => [...row]);
    const beforeErrors = [...currentErrors];

    // Apply the removal (add 1 to account for header row)
    const newData = [...currentData];
    newData.splice(rowIndex + 1, 1);

    setCurrentData(newData);

    // Note: Validation errors are preserved as-is during schema changes
    // No automatic error removal or position updates are performed

    // Record the manual change in history
    recordManualChange(manualChange, beforeData, newData, beforeErrors, currentErrors);

    // Add to changes history for tracking
    const change: Change = {
      row: rowIndex,
      column: 0,
      oldValue: 'Row data',
      newValue: '',
      timestamp: new Date()
    };
    setChanges(prev => [...prev, change]);

    console.log('✅ MetadataEditor: Row removal applied successfully');
  };

  // Helper method to check if a schema change is applied
  const isSchemaChangeApplied = (changeDetail: SchemaAlignmentChangeDetail, changeIndex: number): boolean => {
    const changeId = `${changeDetail.changeType}-${changeDetail.originalColumn || changeDetail.newColumn}-${changeIndex}`;
    return appliedSchemaChanges.has(changeId);
  };

  // Helper method to get change status for UI display
  const getSchemaChangeStatus = (changeDetail: SchemaAlignmentChangeDetail, changeIndex: number): 'pending' | 'applied' | 'reverted' => {
    const changeId = `${changeDetail.changeType}-${changeDetail.originalColumn || changeDetail.newColumn}-${changeIndex}`;

    if (appliedSchemaChanges.has(changeId)) {
      return 'applied';
    }

    // Check if this change was originally applied but then reverted
    // (This would require more sophisticated tracking in a full implementation)
    return 'pending';
  };



  // Helper to check if any schema changes are pending
  const hasPendingSchemaChanges = (): boolean => {
    return schemaAlignmentChanges.some((change, index) => !isSchemaChangeApplied(change, index));
  };

  // Helper to check if any schema changes are applied
  const hasAppliedSchemaChanges = (): boolean => {
    return appliedSchemaChanges.size > 0;
  };

  // Helper to get schema change statistics
  const getSchemaChangeStats = () => {
    const total = schemaAlignmentChanges.length;
    const applied = schemaAlignmentChanges.filter((change, index) => isSchemaChangeApplied(change, index)).length;
    const pending = total - applied;

    return { total, applied, pending };
  };



  const validateSchemaChangeOnData = (changeDetail: SchemaAlignmentChangeDetail, data: string[][]): boolean => {
    const headerRow = data[0];

    switch (changeDetail.changeType) {
      case 'rename':
        if (!changeDetail.originalColumn || !changeDetail.newColumn) {
          return false;
        }

        const originalIndex = headerRow.findIndex(header => header === changeDetail.originalColumn);
        if (originalIndex === -1) {
          return false;
        }

        const existingIndex = headerRow.findIndex(header => header === changeDetail.newColumn);
        if (existingIndex !== -1 && existingIndex !== originalIndex) {
          return false;
        }

        return true;

      case 'add':
        if (!changeDetail.newColumn) {
          return false;
        }

        if (headerRow.includes(changeDetail.newColumn)) {
          return false;
        }

        return true;

      case 'remove':
        if (!changeDetail.originalColumn) {
          return false;
        }

        const columnIndex = headerRow.findIndex(header => header === changeDetail.originalColumn);
        if (columnIndex === -1) {
          return false;
        }

        if (headerRow.length <= 1) {
          return false;
        }

        return true;

      default:
        return false;
    }
  };

  // Validation helper to check if a schema change can be applied safely
  const validateSchemaChange = (changeDetail: SchemaAlignmentChangeDetail): boolean => {
    const headerRow = currentData[0];

    switch (changeDetail.changeType) {
      case 'rename':
        if (!changeDetail.originalColumn || !changeDetail.newColumn) {
          console.warn('⚠️ MetadataEditor: Invalid rename change - missing column names:', changeDetail);
          return false;
        }

        // Check if original column exists
        const originalIndex = headerRow.findIndex(header => header === changeDetail.originalColumn);
        if (originalIndex === -1) {
          console.warn('⚠️ MetadataEditor: Original column not found for rename:', changeDetail.originalColumn);
          return false;
        }

        // Check if new column name already exists (and it's not the same column)
        const existingIndex = headerRow.findIndex(header => header === changeDetail.newColumn);
        if (existingIndex !== -1 && existingIndex !== originalIndex) {
          console.warn('⚠️ MetadataEditor: Target column name already exists:', changeDetail.newColumn);
          return false;
        }

        return true;

      case 'add':
        if (!changeDetail.newColumn) {
          console.warn('⚠️ MetadataEditor: Invalid add change - missing column name:', changeDetail);
          return false;
        }

        // Check if column name already exists
        if (headerRow.includes(changeDetail.newColumn)) {
          console.warn('⚠️ MetadataEditor: Column already exists for add:', changeDetail.newColumn);
          return false;
        }

        return true;

      case 'remove':
        if (!changeDetail.originalColumn) {
          console.warn('⚠️ MetadataEditor: Invalid remove change - missing column name:', changeDetail);
          return false;
        }

        // Check if column exists
        const columnIndex = headerRow.findIndex(header => header === changeDetail.originalColumn);
        if (columnIndex === -1) {
          console.warn('⚠️ MetadataEditor: Column not found for remove:', changeDetail.originalColumn);
          return false;
        }

        // Check if this is the last column
        if (headerRow.length <= 1) {
          console.warn('⚠️ MetadataEditor: Cannot remove last column');
          return false;
        }

        return true;

      default:
        console.warn('⚠️ MetadataEditor: Unknown change type:', changeDetail.changeType);
        return false;
    }
  };

  // Preview method to show users what a transformation will do before applying
  const previewSchemaChange = (changeDetail: SchemaAlignmentChangeDetail): {
    success: boolean;
    preview?: string;
    error?: string;
    affectedRows?: number;
  } => {
    console.log('👁️ MetadataEditor: Previewing schema change:', changeDetail);

    if (!validateSchemaChange(changeDetail)) {
      return {
        success: false,
        error: 'Change validation failed - see console for details'
      };
    }

    const headerRow = currentData[0];
    const dataRowCount = currentData.length - 1; // Exclude header row

    switch (changeDetail.changeType) {
      case 'rename':
        return {
          success: true,
          preview: `Column "${changeDetail.originalColumn}" will be renamed to "${changeDetail.newColumn}". All ${dataRowCount} data rows will be preserved with the new column name.`,
          affectedRows: dataRowCount
        };

      case 'add':
        return {
          success: true,
          preview: `New column "${changeDetail.newColumn}" will be added to the dataset. All ${dataRowCount} data rows will get an empty value for this column initially.`,
          affectedRows: dataRowCount
        };

      case 'remove':
        const columnIndex = headerRow.findIndex(header => header === changeDetail.originalColumn);
        const nonEmptyValues = currentData.slice(1).filter(row => row[columnIndex] && row[columnIndex].trim() !== '').length;

        return {
          success: true,
          preview: `Column "${changeDetail.originalColumn}" will be removed from the dataset. This will delete ${nonEmptyValues} non-empty values across ${dataRowCount} rows. This action cannot be undone without reverting.`,
          affectedRows: dataRowCount
        };

      default:
        return {
          success: false,
          error: `Unknown change type: ${changeDetail.changeType}`
        };
    }
  };

  // Handle validation status updates with schema alignment results
  const handleValidationStatusUpdate = (statusResponse: ValidationStatusResponse) => {
    console.log('📊 MetadataEditor: Processing validation status update:', {
      hasSchemaAlignmentResults: !!statusResponse.latestResults?.schemaAlignmentResults,
      hasLatestResults: !!statusResponse.latestResults,
      status: statusResponse.status
    });

    if (statusResponse.latestResults) {
      // Update validation errors
      setCurrentErrors(statusResponse.latestResults.validationResults?.validationResults || []);

      // Extract schema alignment changes from the new structure
      if (statusResponse.latestResults.schemaAlignmentResults) {
        const { schemaAlignmentResults } = statusResponse.latestResults.schemaAlignmentResults;
        console.log('📊 MetadataEditor: Extracted schema alignment changes:', schemaAlignmentResults);
        setSchemaAlignmentChanges(schemaAlignmentResults || []);
      }
    }
  };

  // Update current data when csvData prop changes
  useEffect(() => {
    console.log('🔄 MetadataEditor: csvData prop changed, updating currentData:', {
      oldDataLength: currentData.length,
      newDataLength: csvData.length,
      newDataPreview: csvData.slice(0, 3)
    });
    setCurrentData(csvData);
    setOriginalData(csvData);
  }, [csvData]);

  // Update current errors when validationErrors prop changes
  useEffect(() => {
    console.log('🔄 MetadataEditor: validationErrors prop changed:', {
      oldErrorsCount: currentErrors.length,
      newErrorsCount: validationErrors?.length || 0,
      newErrors: validationErrors?.slice(0, 3) || []
    });
    setCurrentErrors(validationErrors || []);
  }, [validationErrors]);

  // Update data when schemaAlignmentResults prop changes - keep original data, don't auto-apply changes
  useEffect(() => {
    if (schemaAlignmentResults) {
      console.log('🔄 MetadataEditor: schemaAlignmentResults prop changed:', {
        hasOriginalData: !!schemaAlignmentResults.summary.originalDataCsv,
        hasAlignedData: !!schemaAlignmentResults.summary.alignedDataCsv,
        changesCount: schemaAlignmentResults.schemaAlignmentResults.length
      });

      const { summary, schemaAlignmentResults: changes } = schemaAlignmentResults;

      // Store original data for reference
      if (summary.originalDataCsv) {
        const originalParsedData = parseCSV(summary.originalDataCsv);
        setOriginalData(originalParsedData);

        // IMPORTANT: Use original data as current data, not aligned data
        // Schema changes should only be applied when user manually accepts them
        setCurrentData(originalParsedData);
      }

      // Store aligned data for reference but don't use it as current data
      if (summary.alignedDataCsv) {
        // We can store this for preview purposes if needed
        console.log('📋 MetadataEditor: Aligned data available for preview (not auto-applied)');
      }

      // Create transformation summary from the new structure
      const transformationSummary = {
        columnsRenamed: summary.columnsRenamed,
        columnsAdded: summary.columnsAdded,
        columnsRemoved: summary.columnsRemoved,
        rowsOriginal: summary.rowsOriginal,
        rowsAligned: summary.rowsAligned,
        totalChanges: summary.totalChanges
      };
      setTransformationSummary(transformationSummary);

      // Store schema alignment changes directly from the detailed changes
      if (changes && changes.length > 0) {
        console.log('🔧 MetadataEditor: Schema alignment changes received:', changes);
        setSchemaAlignmentChanges(changes);

        // IMPORTANT: Only reset applied changes if this is the first time receiving schema results
        // or if the current data matches the original data (indicating no manual changes have been applied)
        setAppliedSchemaChanges(prevApplied => {
          // Check if current data structure matches original data structure
          const currentDataMatches = originalData.length > 0 &&
            currentData.length === originalData.length &&
            currentData[0]?.length === originalData[0]?.length &&
            JSON.stringify(currentData[0]) === JSON.stringify(originalData[0]);

          if (currentDataMatches || prevApplied.size === 0) {
            // Reset to empty - no changes have been manually applied yet
            console.log('📋 MetadataEditor: Schema changes are pending manual user action');
            return new Set();
          } else {
            // Preserve existing applied changes to maintain undo functionality
            console.log('📋 MetadataEditor: Preserving applied changes for undo functionality:', prevApplied.size);
            return prevApplied;
          }
        });
      }
    }
  }, [schemaAlignmentResults]);

  const handleSpreadsheetChange = (newData: string[][], change: Change) => {
    console.log('📝 MetadataEditor: Spreadsheet change received:', {
      change,
      newDataLength: newData.length,
      newDataPreview: newData.slice(0, 3)
    });

    // Update the current data with schema changes applied
    setCurrentData(newData);

    setChanges((prev: Change[]) => [...prev, change]);
  };

  const showError = (message: string) => {
    setErrorMessage(message);
    setShowErrorSnackbar(true);
  };

  const handleCloseErrorSnackbar = () => {
    setShowErrorSnackbar(false);
  };

  // Handle validation error updates from manual changes
  const handleValidationErrorsUpdated = (
    updatedErrors: ValidationError[],
    updates: ValidationErrorPositionUpdate[]
  ) => {
    console.log('🔄 MetadataEditor: Validation errors updated:', {
      newErrorCount: updatedErrors.length,
      updateCount: updates.length,
      affectedUpdates: updates.filter(u => u.wasAffected).length
    });

    setCurrentErrors(updatedErrors);
    setValidationErrorUpdates(updates);

    // Notify parent component about the updated errors
    onValidationErrors(updatedErrors, jobId, schemaAlignmentResults);
  };

  // Handle manual change validation results
  const handleManualChangeValidation = (
    change: ManualDataChange,
    validation: ManualChangeValidationResult
  ) => {
    console.log('⚠️ MetadataEditor: Manual change validation:', {
      changeType: change.type,
      hasConflict: validation.hasSchemaConflict,
      warningCount: validation.warnings.length,
      errorCount: validation.errors.length,
      affectedErrorCount: validation.affectedValidationErrors.length
    });

    // Add to manual changes history
    setManualChanges(prev => [...prev, change]);

    // Show warnings or errors to user
    if (validation.errors.length > 0) {
      showError(`Cannot perform ${change.type}: ${validation.errors.join(', ')}`);
    } else if (validation.warnings.length > 0) {
      console.warn('Manual change warnings:', validation.warnings);
      // Warnings are shown by the spreadsheet component
    }
  };

  const applyChangeToData = (data: string[][], error: ValidationError, workingData?: string[][]): { success: boolean; data: string[][] } => {
    if (!error.recommendedValue) {
      console.warn('⚠️ MetadataEditor: Cannot apply change - no recommended value provided:', error);
      showError('Cannot apply change: No suggested value available.');
      return { success: false, data: workingData || data };
    }

    // Use working data if provided (bulk mode), otherwise use the passed data (individual mode)
    const sourceData = workingData || data;
    const newData = sourceData.map(row => [...row]);

    // Find column index using findIndex for more robust matching
    const columnIndex = sourceData[0]?.findIndex(header => header === error.column);

    console.log('🔧 MetadataEditor: Applying change to data:', {
      errorColumn: error.column,
      errorRow: error.row,
      columnIndex,
      headers: sourceData[0],
      isBulkMode: !!workingData,
      currentValue: error.currentValue,
      recommendedValue: error.recommendedValue,
      dataRowExists: !!newData[error.row],
      dataRowLength: newData[error.row]?.length || 0
    });

    if (columnIndex !== -1 && columnIndex !== undefined && newData[error.row]) {
      const oldValue = newData[error.row][columnIndex];
      newData[error.row][columnIndex] = error.recommendedValue;

      console.log('✅ MetadataEditor: Change applied successfully:', {
        row: error.row,
        column: error.column,
        columnIndex,
        oldValue,
        newValue: error.recommendedValue
      });
      return { success: true, data: newData };
    } else {
      console.error('❌ MetadataEditor: Failed to apply change - invalid column or row:', {
        columnIndex,
        rowExists: !!newData[error.row],
        error
      });

      // Show user-friendly error message
      if (columnIndex === -1 || columnIndex === undefined) {
        showError(`Cannot find column "${error.column}" in the spreadsheet. The data structure may have changed.`);
      } else if (!newData[error.row]) {
        showError(`Cannot find row ${error.row} in the spreadsheet. The data may have been modified.`);
      } else {
        showError(`Unable to apply change to row ${error.row}, column "${error.column}". Please try refreshing the data.`);
      }

      return { success: false, data: workingData || data }; // Return appropriate data unchanged
    }
  };



  const handleApplyChange = (error: ValidationError, workingData?: string[][]): { success: boolean; data?: string[][] } => {
    console.log('🎯 MetadataEditor: Handling apply change for error:', { error: { row: error.row, column: error.column }, isBulkMode: !!workingData });

    if (!error.recommendedValue) {
      console.warn('⚠️ MetadataEditor: Cannot apply change - no recommended value');
      showError('Cannot apply change: No suggested value available.');
      return { success: false };
    }

    const result = applyChangeToData(currentData, error, workingData);

    if (!result.success) {
      // Error message already shown by applyChangeToData
      return { success: false, data: workingData };
    }

    if (workingData) {
      // BULK MODE: Return updated data without side effects
      console.log('✅ MetadataEditor: Validation change applied in bulk mode');
      return { success: true, data: result.data };
    } else {
      // INDIVIDUAL MODE: Update React state and perform side effects
      // Update the current data
      setCurrentData(result.data);

      // Remove this error from the current errors list
      setCurrentErrors((prev: ValidationError[]) => {
        const filtered = prev.filter((e: ValidationError) =>
          !(e.row === error.row && e.column === error.column)
        );
        console.log('📝 MetadataEditor: Removed error from list:', {
          originalCount: prev.length,
          newCount: filtered.length,
          removedError: { row: error.row, column: error.column }
        });
        return filtered;
      });

    // Add a change record with proper column index resolution
    const columnIndex = currentData[0]?.findIndex(header => header === error.column);
    if (columnIndex !== -1 && columnIndex !== undefined) {
      const change: Change = {
        row: error.row,
        column: columnIndex,
        oldValue: error.currentValue,
        newValue: error.recommendedValue,
        timestamp: new Date()
      };

      setChanges((prev: Change[]) => {
        const newChanges = [...prev, change];
        console.log('📋 MetadataEditor: Added change record:', {
          change,
          totalChanges: newChanges.length
        });
        return newChanges;
      });
      } else {
        console.error('❌ MetadataEditor: Failed to create change record - invalid column index:', {
          column: error.column,
          columnIndex,
          headers: currentData[0]
        });
        showError(`Failed to record change for column "${error.column}". The change was applied but may not be tracked properly.`);
      }

      console.log('✅ MetadataEditor: Individual validation change applied successfully');
      return { success: true };
    }
  };

  const handleApplyAllChanges = (error: ValidationError) => {
    console.log('🎯 MetadataEditor: Handling apply all changes for error using data accumulation:', error);

    // Find all similar errors for the same column and error type that have recommended values
    const similarErrors = currentErrors.filter((e: ValidationError) =>
      e.column === error.column &&
      e.errorType === error.errorType &&
      e.recommendedValue // Only include errors with recommended values
    );

    console.log('🔍 MetadataEditor: Found similar errors for batch processing:', {
      originalError: { row: error.row, column: error.column, errorType: error.errorType },
      similarErrorsCount: similarErrors.length,
      similarErrors: similarErrors.map(e => ({ row: e.row, recommended: e.recommendedValue }))
    });

    if (similarErrors.length === 0) {
      console.warn('⚠️ MetadataEditor: No similar errors with recommended values found');
      showError(`No similar errors found for column "${error.column}" with error type "${error.errorType}".`);
      return;
    }

    // Data accumulation pattern - create working copies
    let workingData = currentData.map(row => [...row]);
    let workingErrors = [...currentErrors];
    let successCount = 0;
    let errorCount = 0;
    const errors: string[] = [];
    const bulkChanges: Change[] = [];
    const appliedErrors: ValidationError[] = [];

    console.log('🔧 MetadataEditor: Starting bulk validation correction with data accumulation and change tracking');

    // Apply each error using bulk mode (data accumulation)
    similarErrors.forEach((e: ValidationError) => {
      try {
        console.log('🔧 MetadataEditor: Applying bulk validation change for row:', e.row);
        const result = handleApplyChange(e, workingData);

        if (result.success && result.data) {
          // Accumulate the data changes
          workingData = result.data;

          // Remove the successfully applied error from working errors
          workingErrors = workingErrors.filter((err: ValidationError) =>
            !(err.row === e.row && err.column === e.column)
          );

          // Track this change for Recent Changes display
          const columnIndex = currentData[0]?.findIndex(header => header === e.column);
          if (columnIndex !== -1 && columnIndex !== undefined) {
            const change: Change = {
              row: e.row,
              column: columnIndex,
              oldValue: e.currentValue,
              newValue: e.recommendedValue || '',
              timestamp: new Date()
            };
            bulkChanges.push(change);
            appliedErrors.push(e);
            console.log('📝 MetadataEditor: Recorded bulk change for tracking:', {
              row: e.row,
              column: e.column,
              oldValue: e.currentValue,
              newValue: e.recommendedValue
            });
          }

          successCount++;
          console.log('✅ MetadataEditor: Bulk validation change applied successfully for row:', e.row);
        } else {
          throw new Error('Validation change failed');
        }
      } catch (error) {
        errorCount++;
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        errors.push(`Row ${e.row}: ${errorMessage}`);
        console.error('❌ MetadataEditor: Error applying bulk validation change:', error, e);
      }
    });

    // Single React state updates at the end
    if (successCount > 0) {
      console.log('🔧 MetadataEditor: Applying final data and error state updates');
      setCurrentData(workingData);
      setCurrentErrors(workingErrors);

      // Add bulk changes to Recent Changes tracking
      if (bulkChanges.length > 0) {
        console.log('📋 MetadataEditor: Adding bulk changes to Recent Changes:', bulkChanges.length);
        setChanges((prev: Change[]) => [...prev, ...bulkChanges]);
      }

      // Record bulk operation in Change History for rollback capability
      if (validationErrorManager && appliedErrors.length > 0) {
        const bulkManualChange = ValidationErrorUtils.createManualChange(
          'bulk_validation_fix',
          `Bulk applied ${appliedErrors.length} validation corrections for column "${error.column}" (${error.errorType})`,
          false // Not a schema conflict
        );

        // Record the bulk change with before/after states
        const beforeData = currentData.map(row => [...row]);
        const beforeErrors = [...currentErrors];
        recordManualChange(bulkManualChange, beforeData, workingData, beforeErrors, workingErrors);

        console.log('🏛️ MetadataEditor: Recorded bulk operation in Change History for rollback');
      }
    }

    // Show summary message
    if (successCount > 0 && errorCount === 0) {
      console.log(`✅ MetadataEditor: Applied all ${successCount} validation changes successfully`);
    } else if (successCount > 0 && errorCount > 0) {
      showError(`Applied ${successCount} changes, but ${errorCount} failed: ${errors.slice(0, 3).join(', ')}${errors.length > 3 ? '...' : ''}`);
    } else if (errorCount > 0) {
      showError(`Failed to apply ${errorCount} changes: ${errors.slice(0, 3).join(', ')}${errors.length > 3 ? '...' : ''}`);
    }
  };

  const handleDismissError = (error: ValidationError) => {
    // Remove this error from the current errors list
    setCurrentErrors((prev: ValidationError[]) => prev.filter((e: ValidationError) =>
      !(e.row === error.row && e.column === error.column)
    ));
  };

  // Individual schema change application methods with proper change ID tracking
  const applySchemaChangeById = (changeId: string) => {
    console.log('🎯 MetadataEditor: Applying schema change by ID:', changeId);

    // Find the change detail by parsing the changeId
    const changeIndex = schemaAlignmentChanges.findIndex((change, index) => {
      const id = `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`;
      return id === changeId;
    });

    if (changeIndex === -1) {
      console.error('❌ MetadataEditor: Could not find change detail for ID:', changeId);
      showError('Could not find change to apply');
      return;
    }

    const changeDetail = schemaAlignmentChanges[changeIndex];

    // Check if already applied
    if (isSchemaChangeApplied(changeDetail, changeIndex)) {
      console.log('ℹ️ MetadataEditor: Change is already applied:', changeId);
      return;
    }

    // Validate the change
    if (!validateSchemaChange(changeDetail)) {
      showError('Cannot apply change: validation failed');
      return;
    }

    // Apply the change
    try {
      switch (changeDetail.changeType) {
        case 'rename':
          if (changeDetail.originalColumn && changeDetail.newColumn) {
            applyColumnRename(changeDetail.originalColumn, changeDetail.newColumn);
          }
          break;
        case 'add':
          if (changeDetail.newColumn) {
            applyColumnAddition(changeDetail.newColumn);
          }
          break;
        case 'remove':
          if (changeDetail.originalColumn) {
            applyColumnRemoval(changeDetail.originalColumn);
          }
          break;
        default:
          showError(`Unknown change type: ${changeDetail.changeType}`);
          return;
      }

      console.log('✅ MetadataEditor: Schema change applied successfully:', changeId);
    } catch (error) {
      console.error('❌ MetadataEditor: Error applying schema change:', error, changeDetail);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      showError(`Failed to apply change: ${errorMessage}`);
    }
  };

  // Schema change handlers with enhanced validation and conflict detection
  const handleAcceptSchemaChange = (changeId: string) => {
    console.log('🎯 MetadataEditor: Handling accept schema change:', changeId);
    applySchemaChangeById(changeId);
  };

  const handleRejectSchemaChange = (changeId: string) => {
    console.log('🎯 MetadataEditor: Handling reject schema change:', changeId);

    // For now, rejecting a change means reverting it if it's applied
    if (appliedSchemaChanges.has(changeId)) {
      revertSchemaChange(changeId);
    } else {
      console.log('ℹ️ MetadataEditor: Change is not applied, marking as rejected');
      // In a more sophisticated implementation, we would track rejected changes
      // For now, we just log the rejection
    }
  };

  // Legacy handler for backward compatibility
  const handleAcceptSchemaChangeOld = (changeId: string) => {
    console.log('🎯 MetadataEditor: Handling accept schema change (legacy):', changeId);

    // Find the change detail by parsing the changeId
    const changeIndex = schemaAlignmentChanges.findIndex((change, index) => {
      const id = `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`;
      return id === changeId;
    });

    if (changeIndex === -1) {
      showError('Cannot find schema change to apply');
      return;
    }

    const changeDetail = schemaAlignmentChanges[changeIndex];

    // Check if change is already applied
    if (isSchemaChangeApplied(changeDetail, changeIndex)) {
      console.log('ℹ️ MetadataEditor: Change is already applied');
      return;
    }

    // Validate change can be applied safely
    if (!validateSchemaChange(changeDetail)) {
      return; // Error message already shown by validateSchemaChange
    }

    // Apply the change based on type
    switch (changeDetail.changeType) {
      case 'rename':
        if (changeDetail.originalColumn && changeDetail.newColumn) {
          applyColumnRename(changeDetail.originalColumn, changeDetail.newColumn);
        } else {
          showError('Cannot apply rename: missing column names');
        }
        break;
      case 'add':
        if (changeDetail.newColumn) {
          applyColumnAddition(changeDetail.newColumn);
        } else {
          showError('Cannot apply addition: missing new column name');
        }
        break;
      case 'remove':
        if (changeDetail.originalColumn) {
          applyColumnRemoval(changeDetail.originalColumn);
        } else {
          showError('Cannot apply removal: missing original column name');
        }
        break;
      default:
        showError(`Unknown change type: ${changeDetail.changeType}`);
    }
  };

  const handleRevertSchemaChange = (changeId: string) => {
    console.log('🔄 MetadataEditor: Handling revert schema change:', changeId);

    // Find the change detail by parsing the changeId
    const changeIndex = schemaAlignmentChanges.findIndex((change, index) => {
      const id = `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`;
      return id === changeId;
    });

    if (changeIndex === -1) {
      showError('Cannot find schema change to revert');
      return;
    }

    const changeDetail = schemaAlignmentChanges[changeIndex];

    // Check if change is currently applied
    if (!isSchemaChangeApplied(changeDetail, changeIndex)) {
      console.log('ℹ️ MetadataEditor: Change is not currently applied, nothing to revert');
      return;
    }

    revertSchemaChange(changeId);
  };

  // Handle applied changes updates from bulk operations
  const handleAppliedChangesUpdate = (changeId: string, isApplied: boolean) => {
    console.log('🔧 MetadataEditor: Handling applied changes update:', { changeId, isApplied });

    if (isApplied) {
      // Mark change as applied
      setAppliedSchemaChanges(prev => {
        const newSet = new Set([...prev, changeId]);
        console.log('🔧 MetadataEditor: Added to applied changes:', changeId, 'Total applied:', newSet.size);
        return newSet;
      });
    } else {
      // Mark change as reverted
      setAppliedSchemaChanges(prev => {
        const newSet = new Set(prev);
        const wasDeleted = newSet.delete(changeId);
        console.log('🔄 MetadataEditor: Removed from applied changes:', changeId, 'Was applied:', wasDeleted, 'Total applied:', newSet.size);
        return newSet;
      });
    }
  };

  // Handle bulk schema changes applied for UI change tracking
  const handleBulkSchemaChangesApplied = (appliedChanges: Array<{ change: SchemaAlignmentChangeDetail; index: number; columnIndex?: number }>) => {
    console.log('📝 MetadataEditor: Handling bulk schema changes applied for UI tracking:', appliedChanges.length);

    // Add changes to Recent Changes for display
    const bulkChanges: Change[] = appliedChanges.map(({ change, index, columnIndex }) => {
      let oldValue = '';
      let newValue = '';
      let row = 0; // Header row for schema changes
      let column = columnIndex || 0;

      switch (change.changeType.toLowerCase()) {
        case 'rename':
          oldValue = change.originalColumn || '';
          newValue = change.newColumn || '';
          break;
        case 'add':
          oldValue = '';
          newValue = `+${change.newColumn}`;
          column = currentData[0]?.length || 0; // New column at end
          break;
        case 'remove':
          oldValue = `-${change.originalColumn}`;
          newValue = '';
          break;
        default:
          oldValue = change.originalColumn || '';
          newValue = change.newColumn || '';
      }

      return {
        row,
        column,
        oldValue,
        newValue,
        timestamp: new Date()
      };
    });

    // Add bulk changes to Recent Changes tracking
    if (bulkChanges.length > 0) {
      console.log('📋 MetadataEditor: Adding bulk schema changes to Recent Changes:', bulkChanges.length);
      setChanges((prev: Change[]) => [...prev, ...bulkChanges]);
    }

    // Record bulk operation in Change History for rollback capability
    if (validationErrorManager && appliedChanges.length > 0) {
      const bulkManualChange = ValidationErrorUtils.createManualChange(
        'bulk_schema_change',
        `Bulk applied ${appliedChanges.length} schema transformations`,
        false // Not a schema conflict since these are intentional schema changes
      );

      // Record the bulk change with before/after states
      const beforeData = currentData.map(row => [...row]);
      const beforeErrors = [...currentErrors];
      recordManualChange(bulkManualChange, beforeData, currentData, beforeErrors, currentErrors);

      console.log('🏛️ MetadataEditor: Recorded bulk schema changes in Change History for rollback');
    }
  };

  return (
    <>
      <Box sx={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
        {/* Main Editor Layout */}
        <Box sx={{ display: 'flex', flexGrow: 1 }}>
          {/* Spreadsheet Area - 70% */}
          <Box sx={{ width: '70%', borderRight: 1, borderColor: 'divider' }}>
            <SpreadsheetEditorComponent
              key={`spreadsheet-${currentData.length}-${currentData[0]?.length || 0}`}
              data={currentData}
              validationErrors={currentErrors}
              disabled={spreadsheetDisabled}
              onChange={handleSpreadsheetChange}
              onValidationErrorsUpdated={handleValidationErrorsUpdated}
              onManualChangeValidation={handleManualChangeValidation}
              schemaRequirements={undefined} // TODO: Pass actual schema requirements when available
            />
          </Box>

          {/* Sidebar - 30% */}
          <Box sx={{ width: '30%', display: 'flex', flexDirection: 'column' }}>
            {/* Change History Panel */}
            {changeHistory.length > 0 && (
              <Box sx={{ flexShrink: 0, borderBottom: 1, borderColor: 'divider' }}>
                <ChangeHistoryPanel
                  changeHistory={changeHistory}
                  onRollbackChange={rollbackManualChange}
                  disabled={spreadsheetDisabled}
                />
              </Box>
            )}

            {/* Validation Sidebar */}
            <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
              <ValidationSidebarComponent
                data={currentData}
                changes={changes}
                validationErrors={currentErrors}
                schemaAlignmentResults={schemaAlignmentResults}
                jobId={jobId}
                coreSchemaId={coreSchemaId}
                programSchemaId={programSchemaId}
                onValidationComplete={onValidationComplete}
                onValidationErrors={onValidationErrors}
                onDisableSpreadsheet={setSpreadsheetDisabled}
                onAcceptSchemaChange={handleAcceptSchemaChange}
                onRevertSchemaChange={handleRevertSchemaChange}
                onApplyColumnRename={applyColumnRename}
                onApplyColumnAddition={applyColumnAddition}
                onApplyColumnRemoval={applyColumnRemoval}
                appliedSchemaChangeIds={appliedSchemaChanges}
                getSchemaChangeId={(change, index) => `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`}
                onFinalDataUpdate={setCurrentData}
                onAppliedChangesUpdate={handleAppliedChangesUpdate}
                onBulkSchemaChangesApplied={handleBulkSchemaChangesApplied}
              >
                {/* Error Cards */}
                {currentErrors.map((error: ValidationError, index: number) => (
                  <ErrorCardComponent
                    key={`${error.row}-${error.column}-${error.errorType}-${index}`}
                    error={error}
                    onAccept={() => handleApplyChange(error)}
                    onAcceptAll={() => handleApplyAllChanges(error)}
                    onDismiss={() => handleDismissError(error)}
                  />
                ))}
              </ValidationSidebarComponent>
            </Box>
          </Box>
        </Box>
      </Box>

      {/* Error Snackbar */}
      <Snackbar
        open={showErrorSnackbar}
        autoHideDuration={6000}
        onClose={handleCloseErrorSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleCloseErrorSnackbar}
          severity="error"
          sx={{ width: '100%' }}
          variant="filled"
        >
          {errorMessage}
        </Alert>
      </Snackbar>
    </>
  );
};
