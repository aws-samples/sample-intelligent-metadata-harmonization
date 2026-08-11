/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useMemo, useEffect, useRef, useState } from 'react';
import { Box, Typography, Snackbar, Alert } from '@mui/material';
import Spreadsheet from 'react-spreadsheet';
import {
  ValidationError,
  ContextMenuState,
  ColumnOperation,
  RowOperation,
  ColumnRenameResult,
  UndoRedoOperation,
  UndoRedoState,
  ManualDataChange,
  ManualChangeValidationResult,
  ValidationErrorPositionUpdate
} from '../../lib/types';
import { ValidationErrorManager, ValidationErrorUtils } from '../../lib/validation-error-manager';
import { ContextMenuComponent } from './context-menu';
import { ColumnRenameDialog } from './column-rename-dialog';
import { AddColumnDialog } from './add-column-dialog';
import { RemoveColumnDialog } from './remove-column-dialog';
import { AddRowDialog } from './add-row-dialog';
import { RemoveRowDialog } from './remove-row-dialog';
import { DataStructureToolbar } from './data-structure-toolbar';

export interface Change {
  row: number;
  column: number;
  oldValue: string;
  newValue: string;
  timestamp: Date;
}

interface SpreadsheetEditorProps {
  data: string[][];
  validationErrors?: ValidationError[] | null;
  disabled?: boolean;
  onChange?: (newData: string[][], change: Change) => void;
  onColumnOperation?: (operation: ColumnOperation) => void;
  onRowOperation?: (operation: RowOperation) => void;
  onColumnRename?: (result: ColumnRenameResult) => void;
  onUndo?: () => void;
  onRedo?: () => void;
  onValidationErrorsUpdated?: (errors: ValidationError[], updates: ValidationErrorPositionUpdate[]) => void;
  onManualChangeValidation?: (change: ManualDataChange, validation: ManualChangeValidationResult) => void;
  schemaRequirements?: any; // Schema requirements for validation conflict detection
}

/**
 * SpreadsheetEditorComponent provides an editable spreadsheet interface with:
 * - Horizontal and vertical scrolling for large datasets
 * - Sticky column headers that remain visible during scrolling
 * - Validation error highlighting
 * - Change tracking and event handling
 * - Responsive design that prevents cramped layouts
 */





export const SpreadsheetEditorComponent: React.FC<SpreadsheetEditorProps> = ({
  data,
  validationErrors = null,
  disabled = false,
  onChange,
  onColumnOperation,
  onRowOperation,
  onColumnRename,
  onUndo,
  onRedo,
  onValidationErrorsUpdated,
  onManualChangeValidation,
  schemaRequirements
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Validation error manager
  const validationErrorManagerRef = useRef<ValidationErrorManager | null>(null);

  // Initialize validation error manager
  useEffect(() => {
    validationErrorManagerRef.current = new ValidationErrorManager(validationErrors || []);
  }, [validationErrors]);

  // Context menu state
  const [contextMenuState, setContextMenuState] = useState<ContextMenuState>({
    isOpen: false,
    anchorX: 0,
    anchorY: 0,
    menuType: 'column',
    targetIndex: 0,
    targetColumnName: undefined
  });

  // Column rename dialog state
  const [renameDialogState, setRenameDialogState] = useState<{
    isOpen: boolean;
    columnIndex: number;
    currentColumnName: string;
    loading: boolean;
  }>({
    isOpen: false,
    columnIndex: -1,
    currentColumnName: '',
    loading: false
  });

  // Add column dialog state
  const [addColumnDialogState, setAddColumnDialogState] = useState<{
    isOpen: boolean;
    referenceColumnIndex: number;
    referenceColumnName: string;
    insertPosition: 'before' | 'after';
    loading: boolean;
  }>({
    isOpen: false,
    referenceColumnIndex: -1,
    referenceColumnName: '',
    insertPosition: 'after',
    loading: false
  });

  // Remove column dialog state
  const [removeColumnDialogState, setRemoveColumnDialogState] = useState<{
    isOpen: boolean;
    columnIndex: number;
    columnName: string;
    columnData: string[];
    totalRows: number;
    loading: boolean;
  }>({
    isOpen: false,
    columnIndex: -1,
    columnName: '',
    columnData: [],
    totalRows: 0,
    loading: false
  });

  // Add row dialog state
  const [addRowDialogState, setAddRowDialogState] = useState<{
    isOpen: boolean;
    referenceRowIndex: number;
    insertPosition: 'above' | 'below';
    loading: boolean;
  }>({
    isOpen: false,
    referenceRowIndex: -1,
    insertPosition: 'below',
    loading: false
  });

  // Refs to track if operations should proceed (to handle cancellation during async operations)
  const addRowOperationRef = useRef<boolean>(false);
  const removeRowOperationRef = useRef<boolean>(false);
  const addColumnOperationRef = useRef<boolean>(false);
  const removeColumnOperationRef = useRef<boolean>(false);
  const renameColumnOperationRef = useRef<boolean>(false);

  // Remove row dialog state
  const [removeRowDialogState, setRemoveRowDialogState] = useState<{
    isOpen: boolean;
    rowIndex: number;
    rowData: string[];
    affectedCells: number;
    affectedValidationErrors?: Array<{
      column: string;
      errorType: string;
      currentValue: string;
    }>;
    loading: boolean;
  }>({
    isOpen: false,
    rowIndex: -1,
    rowData: [],
    affectedCells: 0,
    affectedValidationErrors: [],
    loading: false
  });

  // Undo/Redo state
  const [undoRedoState, setUndoRedoState] = useState<UndoRedoState>({
    undoStack: [],
    redoStack: [],
    maxHistorySize: 50,
    canUndo: false,
    canRedo: false
  });

  // Feedback state
  const [feedbackState, setFeedbackState] = useState<{
    isOpen: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    isOpen: false,
    message: '',
    severity: 'success'
  });

  // Toolbar state
  const [selectedColumns, setSelectedColumns] = useState<number[]>([]);
  const [selectedRows, setSelectedRows] = useState<number[]>([]);
  const [modifiedColumns, setModifiedColumns] = useState<number[]>([]);
  const [modifiedRows, setModifiedRows] = useState<number[]>([]);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [isDragMode, setIsDragMode] = useState(false);

  // Debug logging for data propagation (can be removed in production)
  if (process.env.NODE_ENV === 'development') {
    console.log('🔍 SpreadsheetEditor: Component rendered with props:', {
      dataLength: data?.length || 0,
      dataPreview: data?.slice(0, 3) || [], // Show first 3 rows
      validationErrorsCount: validationErrors?.length || 0,
      disabled,
      hasOnChange: !!onChange
    });
  }



  // Remove debug elements after component mounts and updates
  useEffect(() => {
    const removeDebugElements = () => {
      if (containerRef.current) {
        // Remove any elements containing debug text
        const debugElements = containerRef.current.querySelectorAll('*');
        debugElements.forEach(element => {
          const textContent = element.textContent || '';
          if (textContent.includes('Debug:') ||
            textContent.includes('Raw Data Table') ||
            textContent.includes('rows × columns') ||
            textContent.match(/\d+\s+rows\s+×\s+\d+\s+columns/)) {
            element.remove();
          }
        });
      }
    };

    // Run immediately
    removeDebugElements();

    // Run after a short delay to catch dynamically added elements
    const timeoutId = setTimeout(removeDebugElements, 100);

    return () => clearTimeout(timeoutId);
  });

  // Ensure we have valid data
  if (!data || data.length === 0) {
    console.log('⚠️ SpreadsheetEditor: No data provided, showing empty state');
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No data to display
        </Typography>
      </Box>
    );
  }

  // Separate header row from data rows
  const columnLabels = useMemo(() => {
    const labels = data.length > 0 ? data[0] : [];
    console.log('📊 SpreadsheetEditor: Column labels extracted:', labels);
    return labels;
  }, [data]);

  const dataRows = useMemo(() => {
    const rows = data.length > 1 ? data.slice(1) : [];
    console.log('📋 SpreadsheetEditor: Data rows extracted:', {
      rowCount: rows.length,
      preview: rows.slice(0, 2) // Show first 2 data rows
    });
    return rows;
  }, [data]);

  // Convert data rows to spreadsheet format
  const spreadsheetData = useMemo(() => {
    const formatted = dataRows.map(row =>
      row.map(cell => ({
        value: cell || '' // Ensure we have a string value
      }))
    );
    console.log('🔄 SpreadsheetEditor: Converted to spreadsheet format:', {
      rowCount: formatted.length,
      preview: formatted.slice(0, 2)
    });
    return formatted;
  }, [dataRows]);

  // Create row labels (1-based indexing for data rows)
  const rowLabels = useMemo(() => {
    return dataRows.map((_, index) => (index + 1).toString());
  }, [dataRows]);

  // Create error map for quick lookup (currently unused but kept for future validation error highlighting)
  const errorMap = useMemo(() => {
    if (!validationErrors) return new Map();

    const map = new Map<string, ValidationError>();
    validationErrors.forEach(error => {
      // Convert column name to column index
      const columnIndex = columnLabels.indexOf(error.column);
      if (columnIndex !== -1) {
        // Adjust row index since we're displaying data rows only (error.row is 1-based, includes header)
        const displayRowIndex = error.row - 1; // Convert to 0-based data row index
        const key = `${displayRowIndex}-${columnIndex}`;
        map.set(key, error);
      }
    });
    return map;
  }, [validationErrors, columnLabels]);

  // Suppress unused variable warning - errorMap will be used for validation error highlighting in future updates
  void errorMap;

  // Update undo/redo state when stacks change
  useEffect(() => {
    setUndoRedoState(prev => ({
      ...prev,
      canUndo: prev.undoStack.length > 0,
      canRedo: prev.redoStack.length > 0
    }));
  }, [undoRedoState.undoStack.length, undoRedoState.redoStack.length]);

  // Helper function to add operation to undo stack
  const addToUndoStack = (operation: UndoRedoOperation) => {
    setUndoRedoState(prev => {
      const newUndoStack = [...prev.undoStack, operation];

      // Limit stack size
      if (newUndoStack.length > prev.maxHistorySize) {
        newUndoStack.shift(); // Remove oldest operation
      }

      return {
        ...prev,
        undoStack: newUndoStack,
        redoStack: [], // Clear redo stack when new operation is added
        canUndo: true,
        canRedo: false
      };
    });
  };

  // Helper function to show feedback message
  const showFeedback = (message: string, severity: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setFeedbackState({
      isOpen: true,
      message,
      severity
    });
  };

  // Helper function to get validation errors for a specific row
  const getValidationErrorsForRow = (rowIndex: number) => {
    if (!validationErrors) return [];

    // Convert 0-based row index to 1-based for validation error matching
    const validationRowNumber = rowIndex + 1;

    return validationErrors
      .filter(error => error.row === validationRowNumber)
      .map(error => ({
        column: error.column,
        errorType: error.errorType,
        currentValue: error.currentValue
      }));
  };

  // Helper function to perform column addition
  const performColumnAdd = (
    referenceColumnIndex: number,
    newColumnName: string,
    insertPosition: 'before' | 'after'
  ): { success: boolean; updatedData: string[][]; error?: string; insertedColumnIndex: number } => {
    try {
      // Validate new column name
      if (!newColumnName.trim()) {
        return {
          success: false,
          updatedData: data,
          insertedColumnIndex: -1,
          error: 'Column name cannot be empty'
        };
      }

      // Check for duplicate names
      if (columnLabels.includes(newColumnName.trim())) {
        return {
          success: false,
          updatedData: data,
          insertedColumnIndex: -1,
          error: 'A column with this name already exists'
        };
      }

      // Calculate the insertion index
      const insertIndex = insertPosition === 'before' ? referenceColumnIndex : referenceColumnIndex + 1;

      // Create updated data with new column
      const updatedData = data.map((row, rowIndex) => {
        const newRow = [...row];
        if (rowIndex === 0) {
          // Insert column header
          newRow.splice(insertIndex, 0, newColumnName.trim());
        } else {
          // Insert empty cell for data rows
          newRow.splice(insertIndex, 0, '');
        }
        return newRow;
      });

      return {
        success: true,
        updatedData,
        insertedColumnIndex: insertIndex
      };
    } catch (error) {
      return {
        success: false,
        updatedData: data,
        insertedColumnIndex: -1,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  };

  // Helper function to perform column removal
  const performColumnRemove = (
    columnIndex: number
  ): { success: boolean; updatedData: string[][]; error?: string; removedColumnName: string; affectedRows: number } => {
    try {
      // Validate column index
      if (columnIndex < 0 || columnIndex >= columnLabels.length) {
        return {
          success: false,
          updatedData: data,
          removedColumnName: '',
          affectedRows: 0,
          error: 'Invalid column index'
        };
      }

      const removedColumnName = columnLabels[columnIndex];

      // Create updated data with column removed
      const updatedData = data.map(row => {
        const newRow = [...row];
        newRow.splice(columnIndex, 1); // Remove the column at the specified index
        return newRow;
      });

      // Count affected rows (rows that had data in the removed column)
      const affectedRows = data.slice(1).filter(row => row[columnIndex] && row[columnIndex].trim() !== '').length;

      return {
        success: true,
        updatedData,
        removedColumnName,
        affectedRows
      };
    } catch (error) {
      return {
        success: false,
        updatedData: data,
        removedColumnName: '',
        affectedRows: 0,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  };

  // Helper function to perform row addition
  const performRowAdd = (
    referenceRowIndex: number,
    insertPosition: 'above' | 'below'
  ): { success: boolean; updatedData: string[][]; error?: string; insertedRowIndex: number } => {
    try {
      // Validate reference row index (0-based, excluding header)
      if (referenceRowIndex < 0 || referenceRowIndex >= dataRows.length) {
        return {
          success: false,
          updatedData: data,
          insertedRowIndex: -1,
          error: 'Invalid row index'
        };
      }

      // Calculate the insertion index (1-based to account for header row)
      const insertIndex = insertPosition === 'above' ? referenceRowIndex + 1 : referenceRowIndex + 2;

      // Create new empty row with same number of columns as existing data
      const newRow = new Array(columnLabels.length).fill('');

      // Create updated data with new row inserted
      const updatedData = [...data];
      updatedData.splice(insertIndex, 0, newRow);

      return {
        success: true,
        updatedData,
        insertedRowIndex: insertIndex - 1 // Convert back to 0-based data row index
      };
    } catch (error) {
      return {
        success: false,
        updatedData: data,
        insertedRowIndex: -1,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  };

  // Helper function to perform row removal
  const performRowRemove = (
    rowIndex: number
  ): { success: boolean; updatedData: string[][]; error?: string; removedRowData: string[]; affectedCells: number } => {
    try {
      // Validate row index (0-based, excluding header)
      if (rowIndex < 0 || rowIndex >= dataRows.length) {
        return {
          success: false,
          updatedData: data,
          removedRowData: [],
          affectedCells: 0,
          error: 'Invalid row index'
        };
      }

      // Get the row data that will be removed
      const removedRowData = dataRows[rowIndex];

      // Count affected cells (cells that have data)
      const affectedCells = removedRowData.filter(cell => cell && cell.trim() !== '').length;

      // Create updated data with row removed (add 1 to account for header row)
      const updatedData = [...data];
      updatedData.splice(rowIndex + 1, 1);

      return {
        success: true,
        updatedData,
        removedRowData,
        affectedCells
      };
    } catch (error) {
      return {
        success: false,
        updatedData: data,
        removedRowData: [],
        affectedCells: 0,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  };

  // Helper function to perform column rename
  const performColumnRename = (columnIndex: number, newColumnName: string): ColumnRenameResult => {
    try {
      const originalColumnName = columnLabels[columnIndex];

      // Validate new column name
      if (!newColumnName.trim()) {
        return {
          success: false,
          originalColumnName,
          newColumnName,
          columnIndex,
          updatedData: data,
          error: 'Column name cannot be empty'
        };
      }

      // Check for duplicate names
      const otherColumnNames = columnLabels.filter((_, index) => index !== columnIndex);
      if (otherColumnNames.includes(newColumnName.trim())) {
        return {
          success: false,
          originalColumnName,
          newColumnName,
          columnIndex,
          updatedData: data,
          error: 'A column with this name already exists'
        };
      }

      // Create updated data with renamed column
      const updatedData = data.map((row, rowIndex) => {
        if (rowIndex === 0) {
          // Update header row
          const newRow = [...row];
          newRow[columnIndex] = newColumnName.trim();
          return newRow;
        }
        return row; // Data rows remain unchanged
      });

      return {
        success: true,
        originalColumnName,
        newColumnName: newColumnName.trim(),
        columnIndex,
        updatedData
      };
    } catch (error) {
      return {
        success: false,
        originalColumnName: columnLabels[columnIndex] || '',
        newColumnName,
        columnIndex,
        updatedData: data,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  };

  // Handle column rename confirmation
  const handleColumnRenameConfirm = (newColumnName: string) => {
    renameColumnOperationRef.current = true;
    setRenameDialogState(prev => ({ ...prev, loading: true }));

    // Simulate async operation (in real app, this might involve API calls)
    setTimeout(() => {
      // Check if operation should proceed (user might have cancelled)
      if (!renameColumnOperationRef.current) {
        return;
      }

      const result = performColumnRename(renameDialogState.columnIndex, newColumnName);

      if (result.success) {
        // Create manual change for validation tracking
        const manualChange = ValidationErrorUtils.createManualChange(
          'column_rename',
          `Renamed column "${result.originalColumnName}" to "${result.newColumnName}"`,
          true
        );

        // Validate the change for schema conflicts
        if (validationErrorManagerRef.current) {
          const operation: ColumnOperation = {
            action: 'rename' as any,
            columnIndex: result.columnIndex,
            columnName: result.originalColumnName,
            newColumnName: result.newColumnName
          };

          const validationResult = validationErrorManagerRef.current.validateManualChange(
            operation,
            data,
            schemaRequirements
          );

          // Update manual change with validation results
          manualChange.hasSchemaConflict = validationResult.hasSchemaConflict;
          manualChange.schemaConflictWarning = validationResult.warnings.join('; ');
          manualChange.affectedValidationErrors = validationResult.affectedValidationErrors;

          // Notify parent about validation results
          onManualChangeValidation?.(manualChange, validationResult);

          // Update validation errors
          const errorUpdates = validationErrorManagerRef.current.updateErrorsAfterColumnRename(
            result.originalColumnName,
            result.newColumnName,
            result.updatedData
          );

          // Record the change in history
          validationErrorManagerRef.current.recordChange(
            manualChange,
            data,
            result.updatedData,
            validationErrors || [],
            validationErrorManagerRef.current.getValidationErrors()
          );

          // Notify parent about validation error updates
          onValidationErrorsUpdated?.(
            validationErrorManagerRef.current.getValidationErrors(),
            errorUpdates
          );

          // Show warnings if there are schema conflicts
          if (validationResult.hasSchemaConflict && validationResult.warnings.length > 0) {
            showFeedback(
              `Column renamed with warnings: ${validationResult.warnings.join(', ')}`,
              'warning'
            );
          }
        }

        // Create undo operation
        const undoOperation: UndoRedoOperation = {
          id: `column_rename_${Date.now()}`,
          type: 'column_rename',
          description: `Renamed column "${result.originalColumnName}" to "${result.newColumnName}"`,
          timestamp: new Date(),
          beforeState: data,
          afterState: result.updatedData,
          metadata: {
            columnIndex: result.columnIndex,
            originalColumnName: result.originalColumnName,
            newColumnName: result.newColumnName
          }
        };

        // Add to undo stack
        addToUndoStack(undoOperation);

        // Update data
        onChange?.(result.updatedData, {
          row: 0, // Header row
          column: result.columnIndex,
          oldValue: result.originalColumnName,
          newValue: result.newColumnName,
          timestamp: new Date()
        });

        // Notify parent component
        onColumnRename?.(result);

        // Show success feedback
        if (!manualChange.hasSchemaConflict) {
          showFeedback(`Column renamed from "${result.originalColumnName}" to "${result.newColumnName}"`, 'success');
        }
      } else {
        // Show error feedback
        showFeedback(result.error || 'Failed to rename column', 'error');
      }

      // Close dialog
      renameColumnOperationRef.current = false;
      setRenameDialogState({
        isOpen: false,
        columnIndex: -1,
        currentColumnName: '',
        loading: false
      });
    }, 500); // Simulate processing time
  };

  // Handle column rename cancellation
  const handleColumnRenameCancel = () => {
    renameColumnOperationRef.current = false;
    setRenameDialogState({
      isOpen: false,
      columnIndex: -1,
      currentColumnName: '',
      loading: false
    });
  };

  // Handle add column confirmation
  const handleAddColumnConfirm = (newColumnName: string, insertPosition: 'before' | 'after') => {
    addColumnOperationRef.current = true;
    setAddColumnDialogState(prev => ({ ...prev, loading: true }));

    // Simulate async operation (in real app, this might involve API calls)
    setTimeout(() => {
      // Check if operation should proceed (user might have cancelled)
      if (!addColumnOperationRef.current) {
        return;
      }

      const result = performColumnAdd(
        addColumnDialogState.referenceColumnIndex,
        newColumnName,
        insertPosition
      );

      if (result.success) {
        // Create manual change for validation tracking
        const manualChange = ValidationErrorUtils.createManualChange(
          'column_add',
          `Added column "${newColumnName}" ${insertPosition} "${addColumnDialogState.referenceColumnName}"`,
          true
        );

        // Validate the change for schema conflicts
        if (validationErrorManagerRef.current) {
          const operation: ColumnOperation = {
            action: insertPosition === 'before' ? 'add_before' as any : 'add_after' as any,
            columnIndex: addColumnDialogState.referenceColumnIndex,
            columnName: addColumnDialogState.referenceColumnName,
            newColumnName: newColumnName,
            insertPosition: insertPosition
          };

          const validationResult = validationErrorManagerRef.current.validateManualChange(
            operation,
            data,
            schemaRequirements
          );

          // Update manual change with validation results
          manualChange.hasSchemaConflict = validationResult.hasSchemaConflict;
          manualChange.schemaConflictWarning = validationResult.warnings.join('; ');
          manualChange.affectedValidationErrors = validationResult.affectedValidationErrors;

          // Notify parent about validation results
          onManualChangeValidation?.(manualChange, validationResult);

          // Update validation errors
          const errorUpdates = validationErrorManagerRef.current.updateErrorsAfterColumnAdd(
            newColumnName,
            result.insertedColumnIndex,
            result.updatedData
          );

          // Record the change in history
          validationErrorManagerRef.current.recordChange(
            manualChange,
            data,
            result.updatedData,
            validationErrors || [],
            validationErrorManagerRef.current.getValidationErrors()
          );

          // Notify parent about validation error updates
          onValidationErrorsUpdated?.(
            validationErrorManagerRef.current.getValidationErrors(),
            errorUpdates
          );

          // Show warnings if there are schema conflicts
          if (validationResult.warnings.length > 0) {
            showFeedback(
              `Column added with notes: ${validationResult.warnings.join(', ')}`,
              'info'
            );
          }
        }

        // Create undo operation
        const undoOperation: UndoRedoOperation = {
          id: `column_add_${Date.now()}`,
          type: 'column_add',
          description: `Added column "${newColumnName}" ${insertPosition} "${addColumnDialogState.referenceColumnName}"`,
          timestamp: new Date(),
          beforeState: data,
          afterState: result.updatedData,
          metadata: {
            columnIndex: result.insertedColumnIndex,
            newColumnName: newColumnName,
            insertPosition: insertPosition
          }
        };

        // Add to undo stack
        addToUndoStack(undoOperation);

        // Update data
        onChange?.(result.updatedData, {
          row: 0, // Header row
          column: result.insertedColumnIndex,
          oldValue: '', // New column, so no old value
          newValue: newColumnName,
          timestamp: new Date()
        });

        // Show success feedback
        if (!manualChange.hasSchemaConflict) {
          showFeedback(`Column "${newColumnName}" added successfully`, 'success');
        }
      } else {
        // Show error feedback
        showFeedback(result.error || 'Failed to add column', 'error');
      }

      // Close dialog
      addColumnOperationRef.current = false;
      setAddColumnDialogState({
        isOpen: false,
        referenceColumnIndex: -1,
        referenceColumnName: '',
        insertPosition: 'after',
        loading: false
      });
    }, 500); // Simulate processing time
  };

  // Handle add column cancellation
  const handleAddColumnCancel = () => {
    addColumnOperationRef.current = false;
    setAddColumnDialogState({
      isOpen: false,
      referenceColumnIndex: -1,
      referenceColumnName: '',
      insertPosition: 'after',
      loading: false
    });
  };

  // Handle remove column confirmation
  const handleRemoveColumnConfirm = () => {
    removeColumnOperationRef.current = true;
    setRemoveColumnDialogState(prev => ({ ...prev, loading: true }));

    // Simulate async operation (in real app, this might involve API calls)
    setTimeout(() => {
      // Check if operation should proceed (user might have cancelled)
      if (!removeColumnOperationRef.current) {
        return;
      }

      const result = performColumnRemove(removeColumnDialogState.columnIndex);

      if (result.success) {
        // Create manual change for validation tracking
        const manualChange = ValidationErrorUtils.createManualChange(
          'column_remove',
          `Removed column "${result.removedColumnName}" (${result.affectedRows} rows affected)`,
          true
        );

        // Validate the change for schema conflicts
        if (validationErrorManagerRef.current) {
          const operation: ColumnOperation = {
            action: 'remove' as any,
            columnIndex: removeColumnDialogState.columnIndex,
            columnName: result.removedColumnName
          };

          const validationResult = validationErrorManagerRef.current.validateManualChange(
            operation,
            data,
            schemaRequirements
          );

          // Update manual change with validation results
          manualChange.hasSchemaConflict = validationResult.hasSchemaConflict;
          manualChange.schemaConflictWarning = validationResult.warnings.join('; ');
          manualChange.affectedValidationErrors = validationResult.affectedValidationErrors;

          // Notify parent about validation results
          onManualChangeValidation?.(manualChange, validationResult);

          // Update validation errors
          const errorUpdates = validationErrorManagerRef.current.updateErrorsAfterColumnRemove(
            result.removedColumnName,
            removeColumnDialogState.columnIndex,
            result.updatedData
          );

          // Record the change in history
          validationErrorManagerRef.current.recordChange(
            manualChange,
            data,
            result.updatedData,
            validationErrors || [],
            validationErrorManagerRef.current.getValidationErrors()
          );

          // Notify parent about validation error updates
          onValidationErrorsUpdated?.(
            validationErrorManagerRef.current.getValidationErrors(),
            errorUpdates
          );

          // Show warnings if there are schema conflicts or affected validation errors
          if (validationResult.hasSchemaConflict && validationResult.warnings.length > 0) {
            showFeedback(
              `Column removed with warnings: ${validationResult.warnings.join(', ')}`,
              'warning'
            );
          } else if (validationResult.affectedValidationErrors.length > 0) {
            showFeedback(
              `Column removed. ${validationResult.affectedValidationErrors.length} validation error(s) were also removed.`,
              'info'
            );
          }
        }

        // Create undo operation
        const undoOperation: UndoRedoOperation = {
          id: `column_remove_${Date.now()}`,
          type: 'column_remove',
          description: `Removed column "${result.removedColumnName}" (${result.affectedRows} rows affected)`,
          timestamp: new Date(),
          beforeState: data,
          afterState: result.updatedData,
          metadata: {
            columnIndex: removeColumnDialogState.columnIndex,
            originalColumnName: result.removedColumnName
          }
        };

        // Add to undo stack
        addToUndoStack(undoOperation);

        // Update data
        onChange?.(result.updatedData, {
          row: 0, // Header row
          column: removeColumnDialogState.columnIndex,
          oldValue: result.removedColumnName,
          newValue: '', // Column removed, so no new value
          timestamp: new Date()
        });

        // Show success feedback if no warnings were shown
        if (!manualChange.hasSchemaConflict && manualChange.affectedValidationErrors?.length === 0) {
          showFeedback(
            `Column "${result.removedColumnName}" removed successfully (${result.affectedRows} rows affected)`,
            'success'
          );
        }
      } else {
        // Show error feedback
        showFeedback(result.error || 'Failed to remove column', 'error');
      }

      // Close dialog
      removeColumnOperationRef.current = false;
      setRemoveColumnDialogState({
        isOpen: false,
        columnIndex: -1,
        columnName: '',
        columnData: [],
        totalRows: 0,
        loading: false
      });
    }, 500); // Simulate processing time
  };

  // Handle remove column cancellation
  const handleRemoveColumnCancel = () => {
    removeColumnOperationRef.current = false;
    setRemoveColumnDialogState({
      isOpen: false,
      columnIndex: -1,
      columnName: '',
      columnData: [],
      totalRows: 0,
      loading: false
    });
  };

  // Handle add row confirmation
  const handleAddRowConfirm = (insertPosition: 'above' | 'below') => {
    addRowOperationRef.current = true;
    setAddRowDialogState(prev => ({ ...prev, loading: true }));

    // Simulate async operation (in real app, this might involve API calls)
    setTimeout(() => {
      // Check if operation should proceed (user might have cancelled)
      if (!addRowOperationRef.current) {
        return;
      }

      const result = performRowAdd(
        addRowDialogState.referenceRowIndex,
        insertPosition
      );

      if (result.success) {
        // Create manual change for validation tracking
        const manualChange = ValidationErrorUtils.createManualChange(
          'row_add',
          `Added row ${insertPosition} row ${addRowDialogState.referenceRowIndex + 1}`,
          true
        );

        // Validate the change for schema conflicts
        if (validationErrorManagerRef.current) {
          const operation: RowOperation = {
            action: insertPosition === 'above' ? 'add_above' as any : 'add_below' as any,
            rowIndex: addRowDialogState.referenceRowIndex,
            insertPosition: insertPosition
          };

          const validationResult = validationErrorManagerRef.current.validateManualChange(
            operation,
            data,
            schemaRequirements
          );

          // Update manual change with validation results
          manualChange.hasSchemaConflict = validationResult.hasSchemaConflict;
          manualChange.schemaConflictWarning = validationResult.warnings.join('; ');
          manualChange.affectedValidationErrors = validationResult.affectedValidationErrors;

          // Notify parent about validation results
          onManualChangeValidation?.(manualChange, validationResult);

          // Update validation errors (row numbers need to be shifted)
          const errorUpdates = validationErrorManagerRef.current.updateErrorsAfterRowAdd(
            result.insertedRowIndex,
            result.updatedData
          );

          // Record the change in history
          validationErrorManagerRef.current.recordChange(
            manualChange,
            data,
            result.updatedData,
            validationErrors || [],
            validationErrorManagerRef.current.getValidationErrors()
          );

          // Notify parent about validation error updates
          onValidationErrorsUpdated?.(
            validationErrorManagerRef.current.getValidationErrors(),
            errorUpdates
          );

          // Show info about row number updates
          const affectedErrors = errorUpdates.filter(update => update.wasAffected).length;
          if (affectedErrors > 0) {
            showFeedback(
              `Row added. ${affectedErrors} validation error row number(s) were updated.`,
              'info'
            );
          }
        }

        // Create undo operation
        const undoOperation: UndoRedoOperation = {
          id: `row_add_${Date.now()}`,
          type: 'row_add',
          description: `Added row ${insertPosition} row ${addRowDialogState.referenceRowIndex + 1}`,
          timestamp: new Date(),
          beforeState: data,
          afterState: result.updatedData,
          metadata: {
            rowIndex: result.insertedRowIndex,
            insertPosition: insertPosition
          }
        };

        // Add to undo stack
        addToUndoStack(undoOperation);

        // Update data
        onChange?.(result.updatedData, {
          row: result.insertedRowIndex + 1, // Convert to 1-based for change tracking
          column: 0,
          oldValue: '', // New row, so no old value
          newValue: '', // Empty row initially
          timestamp: new Date()
        });

        // Show success feedback if no info message was shown
        if (!manualChange.affectedValidationErrors || manualChange.affectedValidationErrors.length === 0) {
          showFeedback(`Row added ${insertPosition} row ${addRowDialogState.referenceRowIndex + 1}`, 'success');
        }
      } else {
        // Show error feedback
        showFeedback(result.error || 'Failed to add row', 'error');
      }

      // Close dialog
      addRowOperationRef.current = false;
      setAddRowDialogState({
        isOpen: false,
        referenceRowIndex: -1,
        insertPosition: 'below',
        loading: false
      });
    }, 500); // Simulate processing time
  };

  // Handle add row cancellation
  const handleAddRowCancel = () => {
    addRowOperationRef.current = false;
    setAddRowDialogState({
      isOpen: false,
      referenceRowIndex: -1,
      insertPosition: 'below',
      loading: false
    });
  };

  // Handle remove row confirmation
  const handleRemoveRowConfirm = () => {
    removeRowOperationRef.current = true;
    setRemoveRowDialogState(prev => ({ ...prev, loading: true }));

    // Simulate async operation (in real app, this might involve API calls)
    setTimeout(() => {
      // Check if operation should proceed (user might have cancelled)
      if (!removeRowOperationRef.current) {
        return;
      }

      const result = performRowRemove(removeRowDialogState.rowIndex);

      if (result.success) {
        // Create manual change for validation tracking
        const manualChange = ValidationErrorUtils.createManualChange(
          'row_remove',
          `Removed row ${removeRowDialogState.rowIndex + 1} (${result.affectedCells} cells affected)`,
          true
        );

        // Validate the change for schema conflicts
        if (validationErrorManagerRef.current) {
          const operation: RowOperation = {
            action: 'remove' as any,
            rowIndex: removeRowDialogState.rowIndex
          };

          const validationResult = validationErrorManagerRef.current.validateManualChange(
            operation,
            data,
            schemaRequirements
          );

          // Update manual change with validation results
          manualChange.hasSchemaConflict = validationResult.hasSchemaConflict;
          manualChange.schemaConflictWarning = validationResult.warnings.join('; ');
          manualChange.affectedValidationErrors = validationResult.affectedValidationErrors;

          // Notify parent about validation results
          onManualChangeValidation?.(manualChange, validationResult);

          // Update validation errors (remove errors for deleted row, shift others)
          const errorUpdates = validationErrorManagerRef.current.updateErrorsAfterRowRemove(
            removeRowDialogState.rowIndex,
            result.updatedData
          );

          // Record the change in history
          validationErrorManagerRef.current.recordChange(
            manualChange,
            data,
            result.updatedData,
            validationErrors || [],
            validationErrorManagerRef.current.getValidationErrors()
          );

          // Notify parent about validation error updates
          onValidationErrorsUpdated?.(
            validationErrorManagerRef.current.getValidationErrors(),
            errorUpdates
          );

          // Show info about affected validation errors
          const removedErrors = errorUpdates.filter(update => update.updatedError === null).length;
          const shiftedErrors = errorUpdates.filter(update =>
            update.updatedError !== null && update.wasAffected
          ).length;

          if (removedErrors > 0 || shiftedErrors > 0) {
            const messages = [];
            if (removedErrors > 0) {
              messages.push(`${removedErrors} validation error(s) removed`);
            }
            if (shiftedErrors > 0) {
              messages.push(`${shiftedErrors} validation error row number(s) updated`);
            }
            showFeedback(
              `Row removed. ${messages.join(', ')}.`,
              'info'
            );
          }
        }

        // Create undo operation with complete row data for recovery
        const undoOperation: UndoRedoOperation = {
          id: `row_remove_${Date.now()}`,
          type: 'row_remove',
          description: `Removed row ${removeRowDialogState.rowIndex + 1} (${result.affectedCells} cells affected)`,
          timestamp: new Date(),
          beforeState: data,
          afterState: result.updatedData,
          metadata: {
            rowIndex: removeRowDialogState.rowIndex,
            removedRowData: result.removedRowData, // Store complete row data for recovery
            affectedCells: result.affectedCells
          }
        };

        // Add to undo stack
        addToUndoStack(undoOperation);

        // Update data
        onChange?.(result.updatedData, {
          row: removeRowDialogState.rowIndex + 1, // Convert to 1-based for change tracking
          column: 0,
          oldValue: result.removedRowData.join(','), // Represent row data as comma-separated
          newValue: '', // Row removed, so no new value
          timestamp: new Date()
        });

        // Notify parent about row operation for validation error re-evaluation
        onRowOperation?.({
          action: 'remove' as any,
          rowIndex: removeRowDialogState.rowIndex
        });

        // Show success feedback with undo option if no info message was shown
        if (!manualChange.affectedValidationErrors || manualChange.affectedValidationErrors.length === 0) {
          showFeedback(
            `Row ${removeRowDialogState.rowIndex + 1} removed successfully (${result.affectedCells} cells affected). Press Ctrl+Z to undo.`,
            'success'
          );
        }
      } else {
        // Show error feedback
        showFeedback(result.error || 'Failed to remove row', 'error');
      }

      // Close dialog
      removeRowOperationRef.current = false;
      setRemoveRowDialogState({
        isOpen: false,
        rowIndex: -1,
        rowData: [],
        affectedCells: 0,
        affectedValidationErrors: [],
        loading: false
      });
    }, 500); // Simulate processing time
  };

  // Handle remove row cancellation
  const handleRemoveRowCancel = () => {
    removeRowOperationRef.current = false;
    setRemoveRowDialogState({
      isOpen: false,
      rowIndex: -1,
      rowData: [],
      affectedCells: 0,
      affectedValidationErrors: [],
      loading: false
    });
  };

  // Handle undo operation
  const handleUndo = () => {
    if (undoRedoState.undoStack.length === 0) return;

    const lastOperation = undoRedoState.undoStack[undoRedoState.undoStack.length - 1];

    // Move operation from undo to redo stack
    setUndoRedoState(prev => ({
      ...prev,
      undoStack: prev.undoStack.slice(0, -1),
      redoStack: [...prev.redoStack, lastOperation]
    }));

    // Restore previous state
    onChange?.(lastOperation.beforeState, {
      row: 0,
      column: lastOperation.metadata?.columnIndex || 0,
      oldValue: lastOperation.metadata?.newColumnName || '',
      newValue: lastOperation.metadata?.originalColumnName || '',
      timestamp: new Date()
    });

    // Show feedback
    showFeedback(`Undid: ${lastOperation.description}`, 'info');

    // Notify parent
    onUndo?.();
  };

  // Handle redo operation
  const handleRedo = () => {
    if (undoRedoState.redoStack.length === 0) return;

    const lastOperation = undoRedoState.redoStack[undoRedoState.redoStack.length - 1];

    // Move operation from redo to undo stack
    setUndoRedoState(prev => ({
      ...prev,
      undoStack: [...prev.undoStack, lastOperation],
      redoStack: prev.redoStack.slice(0, -1)
    }));

    // Restore next state
    onChange?.(lastOperation.afterState, {
      row: 0,
      column: lastOperation.metadata?.columnIndex || 0,
      oldValue: lastOperation.metadata?.originalColumnName || '',
      newValue: lastOperation.metadata?.newColumnName || '',
      timestamp: new Date()
    });

    // Show feedback
    showFeedback(`Redid: ${lastOperation.description}`, 'info');

    // Notify parent
    onRedo?.();
  };

  // Add keyboard event listeners for shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Handle Delete key for row deletion
      if (event.key === 'Delete' && !event.ctrlKey && !event.metaKey && !event.altKey) {
        const target = event.target as HTMLElement;

        // Check if focus is on a row header or row cell
        const rowHeader = target.closest('th[data-row-index]') ||
          target.closest('.Spreadsheet__row-header');
        const rowCell = target.closest('td[data-row-index]');

        if (rowHeader || rowCell) {
          event.preventDefault();

          // Try to get row index from data attribute or position
          let rowIndex = -1;
          const targetElement = rowHeader || rowCell;
          const dataRowIndex = targetElement?.getAttribute('data-row-index');

          if (dataRowIndex) {
            rowIndex = parseInt(dataRowIndex, 10);
          } else {
            // Fallback: find row index by position in table
            const tableRow = targetElement?.closest('tr');
            if (tableRow) {
              const tableBody = tableRow.closest('tbody');
              if (tableBody) {
                const rows = Array.from(tableBody.querySelectorAll('tr'));
                rowIndex = rows.indexOf(tableRow as HTMLTableRowElement);
              }
            }
          }

          // Validate row index and prevent header row deletion
          if (rowIndex >= 0 && rowIndex < dataRows.length) {
            const rowData = dataRows[rowIndex];
            const affectedCells = rowData.filter(cell => cell && cell.trim() !== '').length;
            const affectedValidationErrors = getValidationErrorsForRow(rowIndex);

            setRemoveRowDialogState({
              isOpen: true,
              rowIndex,
              rowData,
              affectedCells,
              affectedValidationErrors,
              loading: false
            });
          }
        }
      }

      // Handle Ctrl+Z for undo
      if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !event.shiftKey) {
        event.preventDefault();
        handleUndo();
      }

      // Handle Ctrl+Y or Ctrl+Shift+Z for redo
      if (((event.ctrlKey || event.metaKey) && event.key === 'y') ||
        ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'z')) {
        event.preventDefault();
        handleRedo();
      }

      // Handle Escape key to clear selections
      if (event.key === 'Escape') {
        console.log('🔄 Clearing selections with Escape key');
        setSelectedColumns([]);
        setSelectedRows([]);
      }
    };

    // Add event listener to document for global keyboard shortcuts
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [dataRows, undoRedoState.canUndo, undoRedoState.canRedo]);

  // Handle cell selection for toolbar functionality
  useEffect(() => {
    const handleCellClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      console.log('🖱️ Click detected on:', target.tagName, target.className, target.textContent?.slice(0, 20));

      // Ignore clicks on toolbar elements
      if (target.closest('[role="toolbar"]') || target.closest('.MuiToolbar-root') || target.closest('button')) {
        console.log('🖱️ Ignoring click on toolbar/button element');
        return;
      }

      // Check if click is on a column header
      const columnHeader = target.tagName === 'TH' ? target : target.closest('th');
      const isInTableHead = target.closest('thead');
      const headerText = columnHeader?.textContent?.trim();

      console.log('� Colulmn header detection:', {
        hasColumnHeader: !!columnHeader,
        isInTableHead: !!isInTableHead,
        headerText,
        targetTag: target.tagName,
        targetText: target.textContent?.trim()
      });

      // Check if this is a column header by matching text with columnLabels
      let columnIndex = -1;
      if (headerText && columnLabels.includes(headerText)) {
        columnIndex = columnLabels.findIndex(label => label === headerText);
        console.log('📍 Column header matched:', {
          headerText,
          columnIndex,
          columnLabels
        });
      }

      if (columnHeader && columnIndex >= 0 && columnIndex < columnLabels.length) {
        console.log('📍 Column header clicked:', columnHeader, 'Text:', headerText, 'Index:', columnIndex);
        if (event.ctrlKey || event.metaKey) {
          // Multi-select: toggle column in selection
          setSelectedColumns(prev => {
            const newSelection = prev.includes(columnIndex)
              ? prev.filter(i => i !== columnIndex)
              : [...prev, columnIndex];
            console.log('🔵 Column multi-select:', { columnIndex, newSelection });
            return newSelection;
          });
        } else {
          // Single select: select only this column
          console.log('🔵 Column single-select:', { columnIndex });
          setSelectedColumns([columnIndex]);
        }
        // Clear row selection when selecting columns
        setSelectedRows([]);
        return;
      }

      // Check if click is on a row header - look for th elements in tbody with numeric content
      const isInTableBody = target.closest('tbody');
      const rowHeader = target.tagName === 'TH' ? target : target.closest('th');
      const isNumericRowHeader = rowHeader && rowHeader.textContent?.match(/^\d+$/);

      console.log('🔍 Row header check:', {
        hasRowHeader: !!rowHeader,
        isInTableBody: !!isInTableBody,
        tagName: target.tagName,
        textContent: target.textContent,
        isNumeric: !!isNumericRowHeader
      });

      if (rowHeader && isInTableBody && isNumericRowHeader) {
        console.log('📍 Row header clicked:', rowHeader, 'Text:', rowHeader.textContent);
        // Get row index from text content
        // The displayed row number is 1-based, but we need 0-based for our data array
        // However, the visual selection needs to match what the user clicked
        let rowIndex = -1;
        const rowText = rowHeader.textContent?.trim();
        if (rowText && /^\d+$/.test(rowText)) {
          // Keep the row index as displayed (1-based becomes 0-based for data array)
          rowIndex = parseInt(rowText, 10);
          console.log('📍 Row text:', rowText, 'Calculated row index:', rowIndex, 'Data rows length:', dataRows.length);
        }

        if (rowIndex >= 0 && rowIndex < dataRows.length) {
          if (event.ctrlKey || event.metaKey) {
            // Multi-select: toggle row in selection
            setSelectedRows(prev => {
              const newSelection = prev.includes(rowIndex)
                ? prev.filter(i => i !== rowIndex)
                : [...prev, rowIndex];
              console.log('🟠 Row multi-select:', { rowIndex, newSelection });
              return newSelection;
            });
          } else {
            // Single select: select only this row
            console.log('🟠 Row single-select:', { rowIndex });
            setSelectedRows([rowIndex]);
          }
          // Clear column selection when selecting rows
          setSelectedColumns([]);
        }
        return;
      }

      // Click on data cell - clear selections unless in selection mode
      console.log('📱 Data cell clicked, clearing selections. isSelectionMode:', isSelectionMode);
      if (!isSelectionMode) {
        setSelectedColumns([]);
        setSelectedRows([]);
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('click', handleCellClick);
    }

    return () => {
      if (container) {
        container.removeEventListener('click', handleCellClick);
      }
    };
  }, [columnLabels, dataRows, isSelectionMode]);

  // Apply selection styling to DOM elements
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    console.log('🎨 Applying selection styling. Selected:', { selectedColumns, selectedRows });

    // Debug: log all row headers to see their text content
    const allRowHeaders = container.querySelectorAll('tbody tr th');
    console.log('🎨 All row headers in DOM:', Array.from(allRowHeaders).map((th, index) => ({
      index,
      text: th.textContent,
      element: th
    })));

    // Remove all existing selection classes
    const allHeaders = container.querySelectorAll('th');
    const allCells = container.querySelectorAll('td');

    allHeaders.forEach(header => {
      header.classList.remove('selected-column', 'selected-row');
    });
    allCells.forEach(cell => {
      cell.classList.remove('selected-column', 'selected-row');
    });

    // Apply column selection classes
    selectedColumns.forEach(columnIndex => {
      console.log('🎨 Styling column:', columnIndex);

      // Find column header by matching text content
      const headerRow = container.querySelector('thead tr');
      if (headerRow) {
        const headers = Array.from(headerRow.querySelectorAll('th'));
        const columnHeader = headers.find(th => th.textContent?.trim() === columnLabels[columnIndex]);
        if (columnHeader) {
          console.log('🎨 Found header to style:', columnHeader.textContent);
          columnHeader.classList.add('selected-column');

          // Get the position of this header to style corresponding cells
          const headerPosition = headers.indexOf(columnHeader);

          // Select all cells in the column at the same position
          const rows = container.querySelectorAll('tbody tr');
          rows.forEach(row => {
            const cells = row.querySelectorAll('td, th');
            const cell = cells[headerPosition];
            if (cell) {
              cell.classList.add('selected-column');
            }
          });
        } else {
          console.log('🎨 Could not find header for column:', columnIndex, columnLabels[columnIndex]);
        }
      }
    });

    // Apply row selection classes
    selectedRows.forEach(rowIndex => {
      const rows = container.querySelectorAll('tbody tr');
      console.log('🎨 Applying row selection:', {
        rowIndex,
        totalRows: rows.length,
        selectedRows
      });

      const row = rows[rowIndex];
      if (row) {
        console.log('🎨 Found row to highlight:', row, 'Row header text:', row.querySelector('th')?.textContent);
        // Select row header
        const rowHeader = row.querySelector('th');
        if (rowHeader) {
          rowHeader.classList.add('selected-row');
        }

        // Select all cells in the row
        const cells = row.querySelectorAll('td');
        cells.forEach(cell => {
          cell.classList.add('selected-row');
        });
      } else {
        console.log('🎨 Row not found for index:', rowIndex);
      }
    });
  }, [selectedColumns, selectedRows]);

  // Add context menu event listeners
  useEffect(() => {
    const handleContextMenu = (event: MouseEvent) => {
      const target = event.target as HTMLElement;

      // Check if right-click is on a column header
      const columnHeader = target.closest('th[data-column-index]') ||
        target.closest('.Spreadsheet__header th');

      if (columnHeader) {
        event.preventDefault();

        // Try to get column index from data attribute or position
        let columnIndex = -1;
        const dataColumnIndex = columnHeader.getAttribute('data-column-index');

        if (dataColumnIndex) {
          columnIndex = parseInt(dataColumnIndex, 10);
        } else {
          // Fallback: find column index by position in header row
          const headerRow = columnHeader.closest('tr');
          if (headerRow) {
            const headers = Array.from(headerRow.querySelectorAll('th'));
            columnIndex = headers.indexOf(columnHeader as HTMLTableCellElement) - 1; // -1 for row header
          }
        }

        if (columnIndex >= 0 && columnIndex < columnLabels.length) {
          // Select the column when right-clicking
          console.log('🔵 Column right-click select:', { columnIndex });
          setSelectedColumns([columnIndex]);
          setSelectedRows([]);

          setContextMenuState({
            isOpen: true,
            anchorX: event.clientX,
            anchorY: event.clientY,
            menuType: 'column',
            targetIndex: columnIndex,
            targetColumnName: columnLabels[columnIndex]
          });
        }
        return;
      }

      // Check if right-click is on a row number
      const rowHeader = target.closest('th[data-row-index]') ||
        target.closest('.Spreadsheet__row-header') ||
        (target.tagName === 'TH' && target.textContent?.match(/^\d+$/));

      if (rowHeader && rowHeader instanceof Element) {
        event.preventDefault();

        // Try to get row index from data attribute or text content
        let rowIndex = -1;
        const dataRowIndex = rowHeader.getAttribute('data-row-index');

        if (dataRowIndex) {
          rowIndex = parseInt(dataRowIndex, 10);
        } else {
          // Fallback: parse row number from text content
          const rowText = rowHeader.textContent?.trim();
          if (rowText && /^\d+$/.test(rowText)) {
            rowIndex = parseInt(rowText, 10); // Convert to 0-based index
          }
        }

        // Validate row index and ensure it's not the header row and within bounds
        if (rowIndex >= 0 && rowIndex < dataRows.length) {
          // Select the row when right-clicking
          console.log('🟠 Row right-click select:', { rowIndex });
          setSelectedRows([rowIndex]);
          setSelectedColumns([]);

          setContextMenuState({
            isOpen: true,
            anchorX: event.clientX,
            anchorY: event.clientY,
            menuType: 'row',
            targetIndex: rowIndex,
            targetColumnName: undefined
          });
        }
        return;
      }
    };

    // Handle keyboard shortcuts
    const handleKeyDown = (event: KeyboardEvent) => {
      // F2 key for column rename
      if (event.key === 'F2' && !disabled) {
        const activeElement = document.activeElement;
        if (activeElement && containerRef.current?.contains(activeElement)) {
          // Try to determine which column is focused
          const cellElement = activeElement.closest('td, th');
          if (cellElement) {
            const headerRow = cellElement.closest('thead tr');
            if (headerRow) {
              // This is a header cell - get column index
              const headers = Array.from(headerRow.querySelectorAll('th'));
              const columnIndex = headers.indexOf(cellElement as HTMLTableCellElement) - 1; // -1 for row header

              if (columnIndex >= 0 && columnIndex < columnLabels.length) {
                event.preventDefault();
                setRenameDialogState({
                  isOpen: true,
                  columnIndex,
                  currentColumnName: columnLabels[columnIndex],
                  loading: false
                });
              }
            } else {
              // This is a data cell - get column index and show rename for that column
              const row = cellElement.closest('tr');
              if (row) {
                const cells = Array.from(row.querySelectorAll('td'));
                const columnIndex = cells.indexOf(cellElement as HTMLTableCellElement) - 1; // -1 for row header

                if (columnIndex >= 0 && columnIndex < columnLabels.length) {
                  event.preventDefault();
                  setRenameDialogState({
                    isOpen: true,
                    columnIndex,
                    currentColumnName: columnLabels[columnIndex],
                    loading: false
                  });
                }
              }
            }
          }
        }
      }

      // Ctrl+Z for undo
      else if (event.ctrlKey && event.key === 'z' && !event.shiftKey && !disabled) {
        if (undoRedoState.canUndo) {
          event.preventDefault();
          handleUndo();
        }
      }

      // Ctrl+Y or Ctrl+Shift+Z for redo
      else if (((event.ctrlKey && event.key === 'y') || (event.ctrlKey && event.shiftKey && event.key === 'z')) && !disabled) {
        if (undoRedoState.canRedo) {
          event.preventDefault();
          handleRedo();
        }
      }

      // Ctrl+Shift+N for add column
      else if (event.ctrlKey && event.shiftKey && event.key === 'N' && !disabled) {
        const activeElement = document.activeElement;
        if (activeElement && containerRef.current?.contains(activeElement)) {
          // Try to determine which column is focused
          const cellElement = activeElement.closest('td, th');
          if (cellElement) {
            const headerRow = cellElement.closest('thead tr');
            let columnIndex = -1;

            if (headerRow) {
              // This is a header cell - get column index
              const headers = Array.from(headerRow.querySelectorAll('th'));
              columnIndex = headers.indexOf(cellElement as HTMLTableCellElement) - 1; // -1 for row header
            } else {
              // This is a data cell - get column index
              const row = cellElement.closest('tr');
              if (row) {
                const cells = Array.from(row.querySelectorAll('td'));
                columnIndex = cells.indexOf(cellElement as HTMLTableCellElement) - 1; // -1 for row header
              }
            }

            if (columnIndex >= 0 && columnIndex < columnLabels.length) {
              event.preventDefault();
              setAddColumnDialogState({
                isOpen: true,
                referenceColumnIndex: columnIndex,
                referenceColumnName: columnLabels[columnIndex],
                insertPosition: 'after', // Default to after
                loading: false
              });
            }
          }
        }
      }

      // Ctrl+Shift+R for add row
      else if (event.ctrlKey && event.shiftKey && event.key === 'R' && !disabled) {
        const activeElement = document.activeElement;
        if (activeElement && containerRef.current?.contains(activeElement)) {
          // Try to determine which row is focused
          const cellElement = activeElement.closest('td, th');
          if (cellElement) {
            const row = cellElement.closest('tr');
            if (row && !row.closest('thead')) {
              // This is a data row - get row index
              const tbody = row.closest('tbody');
              if (tbody) {
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const rowIndex = rows.indexOf(row as HTMLTableRowElement);

                if (rowIndex >= 0 && rowIndex < dataRows.length) {
                  event.preventDefault();
                  setAddRowDialogState({
                    isOpen: true,
                    referenceRowIndex: rowIndex,
                    insertPosition: 'below', // Default to below
                    loading: false
                  });
                }
              }
            }
          }
        }
      }

      // Shift+F10 or Menu key for context menu
      else if ((event.shiftKey && event.key === 'F10') || event.key === 'ContextMenu') {
        // For keyboard access, we'd need to determine the currently focused cell
        // This is a basic implementation - could be enhanced
        const activeElement = document.activeElement;
        if (activeElement && containerRef.current?.contains(activeElement)) {
          event.preventDefault();
          // Position menu near the active element
          const rect = activeElement.getBoundingClientRect();
          setContextMenuState({
            isOpen: true,
            anchorX: rect.left + rect.width / 2,
            anchorY: rect.bottom,
            menuType: 'column', // Default to column menu for keyboard access
            targetIndex: 0,
            targetColumnName: columnLabels[0]
          });
        }
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('contextmenu', handleContextMenu);
      container.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      if (container) {
        container.removeEventListener('contextmenu', handleContextMenu);
        container.removeEventListener('keydown', handleKeyDown);
      }
    };
  }, [columnLabels]);

  // Toolbar handlers
  const handleToolbarAddColumn = () => {
    // Add column at the end
    const lastColumnIndex = columnLabels.length - 1;
    setAddColumnDialogState({
      isOpen: true,
      referenceColumnIndex: lastColumnIndex,
      referenceColumnName: columnLabels[lastColumnIndex],
      insertPosition: 'after',
      loading: false
    });
  };

  const handleToolbarRemoveColumn = () => {
    console.log('🔧 Toolbar remove clicked. Selected columns:', selectedColumns);
    if (selectedColumns.length === 0) {
      console.log('🔧 Cannot remove: no columns selected');
      return;
    }

    // For single selection, show remove dialog
    if (selectedColumns.length === 1) {
      const columnIndex = selectedColumns[0];
      const columnData = dataRows.map(row => row[columnIndex] || '');
      console.log('🔧 Opening remove dialog for column:', columnIndex, columnLabels[columnIndex]);
      console.log('🔧 Column data analysis:', {
        columnIndex,
        totalDataRows: dataRows.length,
        columnData,
        nonEmptyValues: columnData.filter(val => val && val.trim() !== ''),
        emptyValues: columnData.filter(val => !val || val.trim() === '')
      });
      setRemoveColumnDialogState({
        isOpen: true,
        columnIndex,
        columnName: columnLabels[columnIndex],
        columnData,
        totalRows: dataRows.length,
        loading: false
      });
    } else {
      // For multiple selections, handle bulk removal
      console.log('🔧 Multiple columns selected, showing bulk message');
      showFeedback('Bulk column removal not yet implemented', 'info');
    }
  };

  const handleToolbarRenameColumn = () => {
    console.log('🔧 Toolbar rename clicked. Selected columns:', selectedColumns);
    if (selectedColumns.length !== 1) {
      console.log('🔧 Cannot rename: need exactly 1 column selected, got:', selectedColumns.length);
      return;
    }

    const columnIndex = selectedColumns[0];
    console.log('🔧 Opening rename dialog for column:', columnIndex, columnLabels[columnIndex]);
    setRenameDialogState({
      isOpen: true,
      columnIndex,
      currentColumnName: columnLabels[columnIndex],
      loading: false
    });
  };

  const handleToolbarAddRowAbove = () => {
    if (selectedRows.length === 0) {
      // Add at the beginning
      setAddRowDialogState({
        isOpen: true,
        referenceRowIndex: 0,
        insertPosition: 'above',
        loading: false
      });
    } else {
      const rowIndex = selectedRows[0];
      setAddRowDialogState({
        isOpen: true,
        referenceRowIndex: rowIndex,
        insertPosition: 'above',
        loading: false
      });
    }
  };

  const handleToolbarAddRowBelow = () => {
    if (selectedRows.length === 0) {
      // Add at the end
      const lastRowIndex = dataRows.length - 1;
      setAddRowDialogState({
        isOpen: true,
        referenceRowIndex: lastRowIndex,
        insertPosition: 'below',
        loading: false
      });
    } else {
      const rowIndex = selectedRows[0];
      setAddRowDialogState({
        isOpen: true,
        referenceRowIndex: rowIndex,
        insertPosition: 'below',
        loading: false
      });
    }
  };

  const handleToolbarRemoveRow = () => {
    if (selectedRows.length === 0) return;

    // For single selection, show remove dialog
    if (selectedRows.length === 1) {
      const rowIndex = selectedRows[0];
      const rowData = dataRows[rowIndex] || [];
      const affectedCells = rowData.filter(cell => cell && cell.trim() !== '').length;
      const affectedValidationErrors = getValidationErrorsForRow(rowIndex);

      setRemoveRowDialogState({
        isOpen: true,
        rowIndex,
        rowData,
        affectedCells,
        affectedValidationErrors,
        loading: false
      });
    } else {
      // For multiple selections, handle bulk removal
      showFeedback('Bulk row removal not yet implemented', 'info');
    }
  };

  const handleToolbarBulkOperations = (operation: string) => {
    showFeedback(`Bulk ${operation} not yet implemented`, 'info');
  };

  const handleToolbarToggleSelectionMode = () => {
    setIsSelectionMode(!isSelectionMode);
  };

  const handleToolbarToggleDragMode = () => {
    setIsDragMode(!isDragMode);
  };

  const handleToolbarImportExport = (operation: string) => {
    showFeedback(`${operation} not yet implemented`, 'info');
  };

  const handleToolbarSettings = (operation: string) => {
    showFeedback(`${operation} not yet implemented`, 'info');
  };

  // Handle context menu close
  const handleContextMenuClose = () => {
    setContextMenuState(prev => ({ ...prev, isOpen: false }));
  };

  // Handle column operations from context menu
  const handleColumnOperation = (operation: ColumnOperation) => {
    console.log('🔧 SpreadsheetEditor: Column operation requested:', operation);

    if (operation.action === 'rename') {
      // Handle rename operation directly
      setRenameDialogState({
        isOpen: true,
        columnIndex: operation.columnIndex,
        currentColumnName: operation.columnName,
        loading: false
      });
    } else if (operation.action === 'add_before' || operation.action === 'add_after') {
      // Handle add column operations directly
      setAddColumnDialogState({
        isOpen: true,
        referenceColumnIndex: operation.columnIndex,
        referenceColumnName: operation.columnName,
        insertPosition: operation.action === 'add_before' ? 'before' : 'after',
        loading: false
      });
    } else if (operation.action === 'remove') {
      // Handle remove column operation directly
      const columnData = dataRows.map(row => row[operation.columnIndex] || '');
      setRemoveColumnDialogState({
        isOpen: true,
        columnIndex: operation.columnIndex,
        columnName: operation.columnName,
        columnData: columnData,
        totalRows: dataRows.length,
        loading: false
      });
    } else {
      // Pass other operations to parent
      onColumnOperation?.(operation);
    }
  };

  // Handle row operations from context menu
  const handleRowOperation = (operation: RowOperation) => {
    console.log('🔧 SpreadsheetEditor: Row operation requested:', operation);

    if (operation.action === 'add_above' || operation.action === 'add_below') {
      // Handle add row operations directly
      setAddRowDialogState({
        isOpen: true,
        referenceRowIndex: operation.rowIndex,
        insertPosition: operation.action === 'add_above' ? 'above' : 'below',
        loading: false
      });
    } else if (operation.action === 'remove') {
      // Handle remove row operation directly
      const rowData = dataRows[operation.rowIndex] || [];
      const affectedCells = rowData.filter(cell => cell && cell.trim() !== '').length;
      const affectedValidationErrors = getValidationErrorsForRow(operation.rowIndex);

      setRemoveRowDialogState({
        isOpen: true,
        rowIndex: operation.rowIndex,
        rowData: rowData,
        affectedCells: affectedCells,
        affectedValidationErrors,
        loading: false
      });
    } else {
      // Pass other operations to parent
      onRowOperation?.(operation);
    }
  };

  const handleSpreadsheetChange = (newData: any) => {
    console.log('✏️ SpreadsheetEditor: Cell change detected:', {
      disabled,
      newDataLength: newData?.length || 0,
      newDataPreview: newData?.slice(0, 2) || []
    });

    if (disabled) {
      console.log('🚫 SpreadsheetEditor: Change ignored - component is disabled');
      return;
    }

    // Convert spreadsheet data back to string array (data rows only)
    const stringDataRows = newData.map((row: any) =>
      row.map((cell: any) => cell?.value?.toString() || '')
    );

    // Reconstruct full data array with header + data rows
    const fullStringData = [columnLabels, ...stringDataRows];

    console.log('🔄 SpreadsheetEditor: Processing change:', {
      stringDataRowsCount: stringDataRows.length,
      fullDataCount: fullStringData.length,
      fullDataPreview: fullStringData.slice(0, 3)
    });

    // Find what changed by comparing with current data rows
    for (let rowIndex = 0; rowIndex < stringDataRows.length; rowIndex++) {
      for (let colIndex = 0; colIndex < stringDataRows[rowIndex].length; colIndex++) {
        const oldValue = dataRows[rowIndex]?.[colIndex] || '';
        const newValue = stringDataRows[rowIndex][colIndex];

        if (oldValue !== newValue) {
          const change: Change = {
            row: rowIndex + 1, // +1 because we're skipping header row
            column: colIndex,
            oldValue,
            newValue,
            timestamp: new Date()
          };

          console.log('📝 SpreadsheetEditor: Change detected and calling onChange:', {
            change,
            fullDataLength: fullStringData.length
          });

          onChange?.(fullStringData, change);
          return; // Only handle one change at a time
        }
      }
    }

    console.log('ℹ️ SpreadsheetEditor: No actual changes detected in data comparison');
  };

  return (
    <Box sx={{ height: '100%', width: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Data Structure Toolbar - Fixed at top */}
      <DataStructureToolbar
        onAddColumn={handleToolbarAddColumn}
        onRemoveColumn={handleToolbarRemoveColumn}
        onRenameColumn={handleToolbarRenameColumn}
        onAddRowAbove={handleToolbarAddRowAbove}
        onAddRowBelow={handleToolbarAddRowBelow}
        onRemoveRow={handleToolbarRemoveRow}
        onBulkAddColumns={() => handleToolbarBulkOperations('add columns')}
        onBulkRemoveColumns={() => handleToolbarBulkOperations('remove columns')}
        onBulkRenameColumns={() => handleToolbarBulkOperations('rename columns')}
        onBulkAddRows={() => handleToolbarBulkOperations('add rows')}
        onBulkRemoveRows={() => handleToolbarBulkOperations('remove rows')}
        onUndo={handleUndo}
        onRedo={handleRedo}
        canUndo={undoRedoState.canUndo}
        canRedo={undoRedoState.canRedo}
        onToggleSelectionMode={handleToolbarToggleSelectionMode}
        onToggleDragMode={handleToolbarToggleDragMode}
        isSelectionMode={isSelectionMode}
        isDragMode={isDragMode}
        onImportStructure={() => handleToolbarImportExport('Import structure')}
        onExportStructure={() => handleToolbarImportExport('Export structure')}
        onOpenTemplates={() => handleToolbarSettings('Templates')}
        onOpenSettings={() => handleToolbarSettings('Settings')}
        onOpenStatistics={() => handleToolbarSettings('Statistics')}
        selectedColumns={selectedColumns}
        selectedRows={selectedRows}
        totalColumns={columnLabels.length}
        totalRows={dataRows.length}
        modifiedColumns={modifiedColumns}
        modifiedRows={modifiedRows}
      />

      {/* Scrollable Spreadsheet Container */}
      <Box
        ref={containerRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          overflowX: 'auto', // Enable horizontal scrolling
          overflowY: 'auto', // Enable vertical scrolling
          p: 2,
          '& .error-cell': {
            backgroundColor: '#ffebee !important',
            border: '2px solid #f44336 !important',
            '&:focus': {
              backgroundColor: '#ffcdd2 !important',
            }
          },
          '& .spreadsheet-disabled': {
            pointerEvents: 'none',
            opacity: 0.6,
          },
          '& .Spreadsheet': {
            width: 'max-content', // Allow table to expand beyond container width
            minWidth: '100%', // Ensure minimum width fills container
            minHeight: '400px',
          },
          '& .Spreadsheet__table': {
            width: 'max-content', // Allow table to expand for many columns
            minWidth: '100%',
            borderCollapse: 'collapse',
            tableLayout: 'auto', // Allow columns to size based on content
          },
          '& .Spreadsheet__header': {
            backgroundColor: '#f5f5f5',
            fontWeight: 'bold',
            position: 'sticky',
            top: 0,
            zIndex: 10, // Higher z-index to stay above content during scroll
          },
          '& .Spreadsheet__header th': {
            position: 'sticky',
            top: 0,
            backgroundColor: '#f5f5f5',
            zIndex: 10,
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: '#e0e0e0',
            },
            '&.selected-column': {
              backgroundColor: '#1976d2 !important',
              color: 'white',
            },
          },
          '& .Spreadsheet__cell': {
            border: '1px solid #ddd',
            padding: '8px',
            minWidth: '120px', // Slightly wider minimum for better readability
            maxWidth: '300px', // Prevent extremely wide columns
            whiteSpace: 'nowrap', // Prevent text wrapping in cells
            overflow: 'hidden',
            textOverflow: 'ellipsis', // Show ellipsis for long content
            '&:focus': {
              outline: '2px solid #1976d2',
              outlineOffset: '-2px',
            },
            '&.selected-column': {
              backgroundColor: '#e3f2fd !important',
            },
            '&.selected-row': {
              backgroundColor: '#fff3e0 !important',
            },
          },
          '& .Spreadsheet__row-header': {
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: '#e0e0e0',
            },
            '&.selected-row': {
              backgroundColor: '#ff9800 !important',
              color: 'white',
            },
          },
          // Styles for data attributes used by filtered props
          '& [data-active="true"]': {
            backgroundColor: '#e3f2fd',
          },
          '& [data-copied="true"]': {
            backgroundColor: '#f3e5f5',
          },
          '& [data-dragging="true"]': {
            opacity: 0.7,
          },
          '& [data-selected="true"]': {
            outline: '2px solid #1976d2',
          },
          // Hide any debug elements from react-spreadsheet
          '& .Spreadsheet__debug': {
            display: 'none !important',
          },
          '& [class*="debug"]': {
            display: 'none !important',
          },
          '& [class*="Debug"]': {
            display: 'none !important',
          },
          // Hide debug table that shows "Debug: Raw Data Table" and row/column counts
          '& table[class*="debug"]': {
            display: 'none !important',
          },
          '& div[class*="debug"]': {
            display: 'none !important',
          },
          // Improve scrollbar styling for better visibility
          '&::-webkit-scrollbar': {
            width: '12px',
            height: '12px',
          },
          '&::-webkit-scrollbar-track': {
            backgroundColor: '#f1f1f1',
            borderRadius: '6px',
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: '#c1c1c1',
            borderRadius: '6px',
            '&:hover': {
              backgroundColor: '#a8a8a8',
            }
          },
          // Ensure proper scrolling behavior
          scrollBehavior: 'smooth',
        }}
      >
        {/* Spreadsheet with horizontal scrolling support for wide tables */}
        <Spreadsheet
          data={spreadsheetData}
          onChange={handleSpreadsheetChange}
          columnLabels={columnLabels}
          rowLabels={rowLabels}
          className={disabled ? 'spreadsheet-disabled' : ''}
        />

        {/* Context Menu */}
        <ContextMenuComponent
          contextMenuState={contextMenuState}
          onClose={handleContextMenuClose}
          onColumnOperation={handleColumnOperation}
          onRowOperation={handleRowOperation}
        />

        {/* Column Rename Dialog */}
        <ColumnRenameDialog
          open={renameDialogState.isOpen}
          currentColumnName={renameDialogState.currentColumnName}
          columnIndex={renameDialogState.columnIndex}
          existingColumnNames={columnLabels}
          loading={renameDialogState.loading}
          onConfirm={handleColumnRenameConfirm}
          onCancel={handleColumnRenameCancel}
        />

        {/* Add Column Dialog */}
        <AddColumnDialog
          open={addColumnDialogState.isOpen}
          referenceColumnIndex={addColumnDialogState.referenceColumnIndex}
          referenceColumnName={addColumnDialogState.referenceColumnName}
          insertPosition={addColumnDialogState.insertPosition}
          existingColumnNames={columnLabels}
          loading={addColumnDialogState.loading}
          onConfirm={handleAddColumnConfirm}
          onCancel={handleAddColumnCancel}
        />

        {/* Remove Column Dialog */}
        <RemoveColumnDialog
          open={removeColumnDialogState.isOpen}
          columnIndex={removeColumnDialogState.columnIndex}
          columnName={removeColumnDialogState.columnName}
          columnData={removeColumnDialogState.columnData}
          totalRows={removeColumnDialogState.totalRows}
          loading={removeColumnDialogState.loading}
          onConfirm={handleRemoveColumnConfirm}
          onCancel={handleRemoveColumnCancel}
        />

        {/* Add Row Dialog */}
        <AddRowDialog
          open={addRowDialogState.isOpen}
          referenceRowIndex={addRowDialogState.referenceRowIndex}
          insertPosition={addRowDialogState.insertPosition}
          loading={addRowDialogState.loading}
          onConfirm={handleAddRowConfirm}
          onCancel={handleAddRowCancel}
        />

        {/* Remove Row Dialog */}
        <RemoveRowDialog
          open={removeRowDialogState.isOpen}
          rowIndex={removeRowDialogState.rowIndex}
          rowData={removeRowDialogState.rowData}
          affectedCells={removeRowDialogState.affectedCells}
          affectedValidationErrors={removeRowDialogState.affectedValidationErrors}
          loading={removeRowDialogState.loading}
          onConfirm={handleRemoveRowConfirm}
          onCancel={handleRemoveRowCancel}
        />

        {/* Feedback Snackbar */}
        <Snackbar
          open={feedbackState.isOpen}
          autoHideDuration={4000}
          onClose={() => setFeedbackState(prev => ({ ...prev, isOpen: false }))}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            onClose={() => setFeedbackState(prev => ({ ...prev, isOpen: false }))}
            severity={feedbackState.severity}
            variant="filled"
            sx={{ width: '100%' }}
          >
            {feedbackState.message}
          </Alert>
        </Snackbar>
      </Box>
    </Box>
  );
};
