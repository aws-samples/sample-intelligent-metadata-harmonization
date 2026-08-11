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
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio
} from '@mui/material';
import { AddCircleOutline } from '@mui/icons-material';

interface AddRowDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Index of the reference row (0-based, excluding header) */
  referenceRowIndex: number;
  /** Initial insert position */
  insertPosition: 'above' | 'below';
  /** Whether the operation is in progress */
  loading?: boolean;
  /** Callback when user confirms the addition */
  onConfirm: (insertPosition: 'above' | 'below') => void;
  /** Callback when user cancels the addition */
  onCancel: () => void;
}

/**
 * Dialog for adding new rows to the spreadsheet
 * Allows users to specify position (above or below reference row)
 */
export const AddRowDialog: React.FC<AddRowDialogProps> = ({
  open,
  referenceRowIndex,
  insertPosition: initialInsertPosition,
  loading = false,
  onConfirm,
  onCancel
}) => {
  const [insertPosition, setInsertPosition] = React.useState<'above' | 'below'>(initialInsertPosition);

  // Reset position when dialog opens
  React.useEffect(() => {
    if (open) {
      setInsertPosition(initialInsertPosition);
    }
  }, [open, initialInsertPosition]);

  const handleConfirm = () => {
    onConfirm(insertPosition);
  };

  const handleCancel = () => {
    onCancel();
  };

  const handlePositionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setInsertPosition(event.target.value as 'above' | 'below');
  };

  // Convert 0-based row index to 1-based for display
  const displayRowNumber = referenceRowIndex + 1;

  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : handleCancel}
      maxWidth="sm"
      fullWidth
      aria-labelledby="add-row-dialog-title"
      aria-describedby="add-row-dialog-description"
    >
      <DialogTitle
        id="add-row-dialog-title"
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          pb: 1
        }}
      >
        <AddCircleOutline color="primary" />
        Add New Row
      </DialogTitle>

      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <Typography
            id="add-row-dialog-description"
            variant="body1"
            sx={{ mb: 3 }}
          >
            Add a new empty row to your data. Choose where to insert the new row relative to row {displayRowNumber}.
          </Typography>

          <FormControl component="fieldset" fullWidth>
            <FormLabel component="legend" sx={{ mb: 2, fontWeight: 'medium' }}>
              Insert Position
            </FormLabel>
            <RadioGroup
              value={insertPosition}
              onChange={handlePositionChange}
              aria-label="insert position"
            >
              <FormControlLabel
                value="above"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="medium">
                      Above row {displayRowNumber}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Insert the new row before the current row
                    </Typography>
                  </Box>
                }
                disabled={loading}
              />
              <FormControlLabel
                value="below"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="medium">
                      Below row {displayRowNumber}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Insert the new row after the current row
                    </Typography>
                  </Box>
                }
                disabled={loading}
              />
            </RadioGroup>
          </FormControl>

          <Box
            sx={{
              mt: 3,
              p: 2,
              backgroundColor: 'info.light',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'info.main'
            }}
          >
            <Typography variant="body2" color="info.contrastText">
              <strong>Note:</strong> The new row will be empty initially. You can add data to it immediately after creation.
              All subsequent row numbers will be updated automatically.
            </Typography>
          </Box>
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
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} /> : <AddCircleOutline />}
          sx={{ minWidth: 120 }}
        >
          {loading ? 'Adding...' : 'Add Row'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
