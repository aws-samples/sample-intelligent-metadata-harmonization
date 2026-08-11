/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress
} from '@mui/material';
import { Warning, Delete } from '@mui/icons-material';

export interface RemoveColumnDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Column index to remove */
  columnIndex: number;
  /** Current column name */
  columnName: string;
  /** Sample data from the column (first few values) */
  columnData?: string[];
  /** Total number of rows that will be affected */
  totalRows?: number;
  /** Whether the operation is currently processing */
  loading?: boolean;
  /** Callback when user confirms removal */
  onConfirm: () => void;
  /** Callback when user cancels removal */
  onCancel: () => void;
}

/**
 * Dialog component for confirming column removal
 * Shows warning about data loss and preview of affected data
 */
export const RemoveColumnDialog: React.FC<RemoveColumnDialogProps> = ({
  open,
  columnIndex,
  columnName,
  columnData = [],
  totalRows = 0,
  loading = false,
  onConfirm,
  onCancel
}) => {
  const [confirmationText, setConfirmationText] = useState('');

  // Calculate statistics about the column data
  const nonEmptyValues = columnData.filter(value => value && value.trim() !== '');
  const emptyRows = (totalRows || columnData.length) - nonEmptyValues.length;

  // Show preview of first few data values (excluding empty ones)
  const previewData = nonEmptyValues.slice(0, 5);
  const hasData = previewData.length > 0;

  const handleConfirm = () => {
    onConfirm();
  };

  const handleCancel = () => {
    setConfirmationText('');
    onCancel();
  };

  return (
    <Dialog
      open={open}
      onClose={handleCancel}
      maxWidth="md"
      fullWidth
      aria-labelledby="remove-column-dialog-title"
      aria-describedby="remove-column-dialog-description"
    >
      <DialogTitle
        id="remove-column-dialog-title"
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          color: 'error.main'
        }}
      >
        <Warning color="error" />
        Remove Column: "{columnName}"
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mb: 3 }}>
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
              Warning: This action cannot be undone!
            </Typography>
            <Typography variant="body2">
              Removing this column will permanently delete all data in column "{columnName}"
              across {totalRows} rows. This action cannot be reversed.
            </Typography>
          </Alert>

          <Box sx={{ mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              Column Information
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
              <Chip
                label={`Column: ${columnName}`}
                color="primary"
                variant="outlined"
              />
              <Chip
                label={`Position: ${columnIndex + 1}`}
                color="secondary"
                variant="outlined"
              />
              <Chip
                label={`Total Rows: ${totalRows}`}
                color="info"
                variant="outlined"
              />
              {hasData && (
                <Chip
                  label={`Rows with Data: ${previewData.length}`}
                  color="warning"
                  variant="outlined"
                />
              )}
              {emptyRows > 0 && (
                <Chip
                  label={`Empty Rows: ${emptyRows}`}
                  color="default"
                  variant="outlined"
                />
              )}
            </Box>
          </Box>

          {hasData && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Data Preview (First {previewData.length} non-empty values)
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold' }}>Row</TableCell>
                      <TableCell sx={{ fontWeight: 'bold' }}>Value</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {previewData.map((value, index) => (
                      <TableRow key={index}>
                        <TableCell>{index + 1}</TableCell>
                        <TableCell>
                          <Typography
                            variant="body2"
                            sx={{
                              maxWidth: 300,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {value}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              {columnData.length > 5 && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  ... and {columnData.length - 5} more values
                </Typography>
              )}
            </Box>
          )}

          {!hasData && (
            <Box sx={{ mb: 2 }}>
              <Alert severity="info">
                This column appears to be empty or contains only blank values.
              </Alert>
            </Box>
          )}

          <Box sx={{ mt: 3, p: 2, bgcolor: 'error.light', borderRadius: 1 }}>
            <Typography variant="body2" color="error.contrastText" sx={{ fontWeight: 'bold' }}>
              Impact of Removal:
            </Typography>
            <Typography variant="body2" color="error.contrastText" component="ul" sx={{ mt: 1, pl: 2 }}>
              <li>Column "{columnName}" will be permanently deleted</li>
              <li>All data in this column will be lost</li>
              <li>Column positions will shift left to fill the gap</li>
              <li>Any validation errors for this column will be cleared</li>
              <li>This action cannot be undone</li>
            </Typography>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={handleCancel}
          disabled={loading}
          variant="outlined"
          size="large"
        >
          Cancel
        </Button>
        <Button
          onClick={handleConfirm}
          disabled={loading}
          variant="contained"
          color="error"
          size="large"
          startIcon={loading ? <CircularProgress size={20} /> : <Delete />}
          sx={{ minWidth: 140 }}
        >
          {loading ? 'Removing...' : 'Remove Column'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
