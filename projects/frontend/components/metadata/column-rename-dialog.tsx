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
  IconButton
} from '@mui/material';
import { Close } from '@mui/icons-material';

export interface ColumnRenameDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Current column name */
  currentColumnName: string;
  /** Index of the column being renamed */
  columnIndex: number;
  /** List of all existing column names for validation */
  existingColumnNames: string[];
  /** Whether the rename operation is in progress */
  loading?: boolean;
  /** Callback when rename is confirmed */
  onConfirm: (newColumnName: string) => void;
  /** Callback when dialog is cancelled */
  onCancel: () => void;
}

/**
 * Dialog component for renaming columns with validation and user feedback
 * Features:
 * - Input validation (empty names, duplicates)
 * - Real-time validation feedback
 * - Loading state during rename operation
 * - Keyboard shortcuts (Enter to confirm, Escape to cancel)
 * - Auto-focus on text field when opened
 */
export const ColumnRenameDialog: React.FC<ColumnRenameDialogProps> = ({
  open,
  currentColumnName,
  columnIndex,
  existingColumnNames,
  loading = false,
  onConfirm,
  onCancel
}) => {
  const [newColumnName, setNewColumnName] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const textFieldRef = useRef<HTMLInputElement>(null);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setNewColumnName(currentColumnName);
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
  }, [open, currentColumnName]);

  // Validate the new column name
  const validateColumnName = (name: string): string | null => {
    // Check for empty name
    if (!name.trim()) {
      return 'Column name cannot be empty';
    }

    // Check for duplicate names (excluding current column)
    const otherColumnNames = existingColumnNames.filter((_, index) => index !== columnIndex);
    if (otherColumnNames.includes(name.trim())) {
      return 'A column with this name already exists';
    }

    // Check for invalid characters (optional - can be customized)
    if (name.includes(',') || name.includes('\n') || name.includes('\r')) {
      return 'Column name cannot contain commas or line breaks';
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

  // Handle confirm action
  const handleConfirm = () => {
    const trimmedName = newColumnName.trim();
    const error = validateColumnName(trimmedName);

    if (error) {
      setValidationError(error);
      return;
    }

    // Only proceed if the name actually changed
    if (trimmedName !== currentColumnName) {
      onConfirm(trimmedName);
    } else {
      // If name didn't change, just close the dialog
      onCancel();
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !loading && !validationError) {
      event.preventDefault();
      handleConfirm();
    } else if (event.key === 'Escape' && !loading) {
      event.preventDefault();
      onCancel();
    }
  };

  const isConfirmDisabled = loading || !!validationError || newColumnName.trim() === currentColumnName;

  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : onCancel}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown={loading}
      aria-labelledby="column-rename-dialog-title"
    >
      <DialogTitle id="column-rename-dialog-title">
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Rename Column
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
            Renaming column "{currentColumnName}" (Column {columnIndex + 1})
          </Typography>

          <TextField
            ref={textFieldRef}
            fullWidth
            label="New Column Name"
            value={newColumnName}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            error={!!validationError}
            helperText={validationError || 'Enter a unique name for this column'}
            disabled={loading}
            variant="outlined"
            autoComplete="off"
            inputProps={{
              'aria-describedby': 'column-rename-help-text'
            }}
          />

          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              <Typography variant="body2" color="text.secondary">
                Renaming column...
              </Typography>
            </Box>
          )}

          {!loading && newColumnName.trim() && newColumnName.trim() !== currentColumnName && !validationError && (
            <Alert severity="info" sx={{ mt: 2 }}>
              This will rename the column and update all data references.
              Validation errors will be re-evaluated after the rename.
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
          {loading ? 'Renaming...' : 'Rename Column'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
