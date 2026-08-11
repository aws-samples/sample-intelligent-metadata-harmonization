/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  Alert,
  CircularProgress,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText
} from '@mui/material';
import { Close } from '@mui/icons-material';

export interface AddColumnDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Index of the column where the new column will be inserted relative to */
  referenceColumnIndex: number;
  /** Name of the reference column for user context */
  referenceColumnName: string;
  /** Position where the new column will be inserted */
  insertPosition: 'before' | 'after';
  /** List of all existing column names for validation */
  existingColumnNames: string[];
  /** Whether the add operation is in progress */
  loading?: boolean;
  /** Callback when add is confirmed */
  onConfirm: (newColumnName: string, insertPosition: 'before' | 'after') => void;
  /** Callback when dialog is cancelled */
  onCancel: () => void;
}

/**
 * Dialog component for adding new columns with validation and positioning options
 * Features:
 * - Input validation (empty names, duplicates)
 * - Position selection (before/after reference column)
 * - Real-time validation feedback
 * - Loading state during add operation
 * - Keyboard shortcuts (Enter to confirm, Escape to cancel)
 * - Auto-focus on text field when opened
 * - Default column naming with auto-increment
 */
export const AddColumnDialog: React.FC<AddColumnDialogProps> = ({
  open,
  referenceColumnIndex,
  referenceColumnName,
  insertPosition: initialInsertPosition,
  existingColumnNames,
  loading = false,
  onConfirm,
  onCancel
}) => {
  const [newColumnName, setNewColumnName] = useState('');
  const [insertPosition, setInsertPosition] = useState<'before' | 'after'>(initialInsertPosition);
  const [validationError, setValidationError] = useState<string | null>(null);
  const textFieldRef = useRef<HTMLInputElement>(null);

  // Generate default column name
  const generateDefaultColumnName = (): string => {
    let counter = 1;
    let defaultName = `New Column ${counter}`;

    while (existingColumnNames.includes(defaultName)) {
      counter++;
      defaultName = `New Column ${counter}`;
    }

    return defaultName;
  };

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      const defaultName = generateDefaultColumnName();
      setNewColumnName(defaultName);
      setInsertPosition(initialInsertPosition);
      setValidationError(null);

      // Auto-focus the text field after a short delay to ensure dialog is rendered
      setTimeout(() => {
        if (textFieldRef.current) {
          textFieldRef.current.focus();
          // Select all text for easy replacement (with fallback for test environments)
          try {
            textFieldRef.current.select();
          } catch (error) {
            // Fallback for test environments where select() may not be available
            textFieldRef.current.setSelectionRange?.(0, textFieldRef.current.value.length);
          }
        }
      }, 100);
    }
  }, [open, initialInsertPosition, existingColumnNames]);

  // Validate the new column name
  const validateColumnName = (name: string): string | null => {
    // Check for empty name
    if (!name.trim()) {
      return 'Column name cannot be empty';
    }

    // Check for duplicate names
    if (existingColumnNames.includes(name.trim())) {
      return 'A column with this name already exists';
    }

    // Check for invalid characters (optional - can be customized)
    if (name.includes(',') || name.includes('\n') || name.includes('\r')) {
      return 'Column name cannot contain commas or line breaks';
    }

    // Check for reasonable length
    if (name.trim().length > 100) {
      return 'Column name is too long (maximum 100 characters)';
    }

    return null;
  };

  // Handle input change with real-time validation
  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setNewColumnName(value);

    // Validate in real-time
    const error = validateColumnName(value);
    setValidationError(error);
  };

  // Handle position change
  const handlePositionChange = (event: any) => {
    setInsertPosition(event.target.value as 'before' | 'after');
  };

  // Handle confirm action
  const handleConfirm = () => {
    const trimmedName = newColumnName.trim();
    const error = validateColumnName(trimmedName);

    if (error) {
      setValidationError(error);
      return;
    }

    onConfirm(trimmedName, insertPosition);
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !loading && !validationError && newColumnName.trim()) {
      event.preventDefault();
      handleConfirm();
    } else if (event.key === 'Escape' && !loading) {
      event.preventDefault();
      onCancel();
    }
  };

  const isConfirmDisabled = loading || !!validationError || !newColumnName.trim();

  // Calculate the final column position for user feedback
  const getFinalColumnPosition = (): number => {
    if (insertPosition === 'before') {
      return referenceColumnIndex + 1; // +1 for 1-based display
    } else {
      return referenceColumnIndex + 2; // +1 for after, +1 for 1-based display
    }
  };

  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : onCancel}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown={loading}
      aria-labelledby="add-column-dialog-title"
    >
      <DialogTitle id="add-column-dialog-title">
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Add New Column
          </Typography>
          {!loading && (
            <IconButton
              aria-label="close"
              onClick={onCancel}
              size="small"
              sx={{ color: 'grey.500' }}
            >
              <Close />
            </IconButton>
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Adding new column relative to "{referenceColumnName}" (Column {referenceColumnIndex + 1})
          </Typography>

          <TextField
            ref={textFieldRef}
            fullWidth
            label="New Column Name"
            value={newColumnName}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            error={!!validationError}
            helperText={validationError || 'Enter a unique name for the new column'}
            disabled={loading}
            variant="outlined"
            autoComplete="off"
            sx={{ mb: 3 }}
            inputProps={{
              'aria-describedby': 'add-column-help-text'
            }}
          />

          <FormControl fullWidth variant="outlined" disabled={loading} sx={{ mb: 2 }}>
            <InputLabel id="insert-position-label">Insert Position</InputLabel>
            <Select
              labelId="insert-position-label"
              value={insertPosition}
              onChange={handlePositionChange}
              label="Insert Position"
              aria-describedby="insert-position-help-text"
            >
              <MenuItem value="before">
                Before "{referenceColumnName}" (Column {referenceColumnIndex + 1})
              </MenuItem>
              <MenuItem value="after">
                After "{referenceColumnName}" (Column {referenceColumnIndex + 2})
              </MenuItem>
            </Select>
            <FormHelperText id="insert-position-help-text">
              Choose where to insert the new column
            </FormHelperText>
          </FormControl>

          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              <Typography variant="body2" color="text.secondary">
                Adding column...
              </Typography>
            </Box>
          )}

          {!loading && newColumnName.trim() && !validationError && (
            <Alert severity="info" sx={{ mt: 2 }}>
              The new column "{newColumnName}" will be inserted at position {getFinalColumnPosition()}
              with empty values for all data rows. You can immediately start editing the new column cells.
            </Alert>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={onCancel}
          disabled={loading}
          color="inherit"
        >
          Cancel
        </Button>
        <Button
          onClick={handleConfirm}
          disabled={isConfirmDisabled}
          variant="contained"
          color="primary"
          startIcon={loading ? <CircularProgress size={16} /> : undefined}
        >
          {loading ? 'Adding...' : 'Add Column'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
