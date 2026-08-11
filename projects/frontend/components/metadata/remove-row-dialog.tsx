/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper
} from '@mui/material';
import { Delete, Warning } from '@mui/icons-material';

interface RemoveRowDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Index of the row to remove (0-based, excluding header) */
  rowIndex: number;
  /** Data in the row to be removed */
  rowData: string[];
  /** Number of cells with data that will be affected */
  affectedCells: number;
  /** Whether the operation is in progress */
  loading?: boolean;
  /** Validation errors that will be affected by removing this row */
  affectedValidationErrors?: Array<{
    column: string;
    errorType: string;
    currentValue: string;
  }>;
  /** Callback when user confirms the removal */
  onConfirm: () => void;
  /** Callback when user cancels the removal */
  onCancel: () => void;
}

/**
 * Dialog for removing rows from the spreadsheet
 * Shows data preview and warns about permanent data loss
 */
export const RemoveRowDialog: React.FC<RemoveRowDialogProps> = ({
  open,
  rowIndex,
  rowData,
  affectedCells,
  loading = false,
  affectedValidationErrors = [],
  onConfirm,
  onCancel
}) => {
  const handleConfirm = () => {
    onConfirm();
  };

  const handleCancel = () => {
    onCancel();
  };

  // Convert 0-based row index to 1-based for display
  const displayRowNumber = rowIndex + 1;

  // Get non-empty cells for preview
  const nonEmptyCells = rowData
    .map((cell, index) => ({ value: cell, columnIndex: index }))
    .filter(({ value }) => value && value.trim() !== '');

  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : handleCancel}
      maxWidth="md"
      fullWidth
      aria-labelledby="remove-row-dialog-title"
      aria-describedby="remove-row-dialog-description"
    >
      <DialogTitle
        id="remove-row-dialog-title"
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          pb: 1
        }}
      >
        <Delete color="error" />
        Remove Row {displayRowNumber}
      </DialogTitle>

      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <Alert
            severity="warning"
            icon={<Warning />}
            sx={{ mb: 3 }}
          >
            <Typography variant="body2" fontWeight="medium">
              This action cannot be undone!
            </Typography>
            <Typography variant="body2">
              Row {displayRowNumber} and all its data will be permanently deleted.
              All subsequent rows will be renumbered.
            </Typography>
          </Alert>

          <Typography
            id="remove-row-dialog-description"
            variant="body1"
            sx={{ mb: 2 }}
          >
            You are about to remove row {displayRowNumber} which contains:
          </Typography>

          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
              <Chip
                label={`${affectedCells} cells with data`}
                color={affectedCells > 0 ? 'warning' : 'default'}
                size="small"
              />
              <Chip
                label={`${rowData.length - affectedCells} empty cells`}
                color="default"
                size="small"
              />
            </Box>

            {nonEmptyCells.length > 0 ? (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Data Preview:
                </Typography>
                <TableContainer
                  component={Paper}
                  variant="outlined"
                  sx={{ maxHeight: 200, mb: 2 }}
                >
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Column</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Value</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {nonEmptyCells.slice(0, 10).map(({ value, columnIndex }) => (
                        <TableRow key={columnIndex}>
                          <TableCell>
                            <Chip
                              label={`Column ${columnIndex + 1}`}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            <Typography
                              variant="body2"
                              sx={{
                                maxWidth: 200,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                              }}
                              title={value}
                            >
                              {value}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                      {nonEmptyCells.length > 10 && (
                        <TableRow>
                          <TableCell colSpan={2} align="center">
                            <Typography variant="caption" color="text.secondary">
                              ... and {nonEmptyCells.length - 10} more cells
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            ) : (
              <Box
                sx={{
                  p: 3,
                  textAlign: 'center',
                  backgroundColor: 'grey.50',
                  borderRadius: 1,
                  border: '1px dashed',
                  borderColor: 'grey.300'
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  This row is empty (no data will be lost)
                </Typography>
              </Box>
            )}
          </Box>

          {affectedValidationErrors.length > 0 && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2" fontWeight="medium">
                Validation Errors Impact:
              </Typography>
              <Typography variant="body2">
                {affectedValidationErrors.length} validation error{affectedValidationErrors.length > 1 ? 's' : ''} on this row will be resolved by removing it.
                All subsequent row numbers in remaining validation errors will be updated.
              </Typography>
              <Box sx={{ mt: 1 }}>
                {affectedValidationErrors.slice(0, 3).map((error, index) => (
                  <Chip
                    key={index}
                    label={`${error.column}: ${error.errorType}`}
                    size="small"
                    color="info"
                    variant="outlined"
                    sx={{ mr: 0.5, mb: 0.5 }}
                  />
                ))}
                {affectedValidationErrors.length > 3 && (
                  <Chip
                    label={`+${affectedValidationErrors.length - 3} more`}
                    size="small"
                    color="info"
                    variant="outlined"
                    sx={{ mr: 0.5, mb: 0.5 }}
                  />
                )}
              </Box>
            </Alert>
          )}

          {affectedCells > 0 && (
            <Alert severity="error" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Data Loss Warning:</strong> {affectedCells} cells containing data will be permanently deleted.
                Consider exporting your data before proceeding if you might need this information later.
              </Typography>
            </Alert>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={handleCancel}
          disabled={loading}
          color="inherit"
        >
          Cancel
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          color="error"
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} /> : <Delete />}
          sx={{ minWidth: 140 }}
        >
          {loading ? 'Removing...' : 'Remove Row'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
