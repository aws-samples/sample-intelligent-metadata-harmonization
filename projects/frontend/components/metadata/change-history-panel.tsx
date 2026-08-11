/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState } from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Collapse,
  Divider,
  Tooltip
} from '@mui/material';
import {
  Undo,
  Warning,
  Person,
  SmartToy,
  ExpandMore,
  ExpandLess,
  History,
  Error as ErrorIcon
} from '@mui/icons-material';
import { ChangeHistoryEntry, ManualDataChange } from '../../lib/types';
import { ValidationErrorUtils } from '../../lib/validation-error-manager';

interface ChangeHistoryPanelProps {
  changeHistory: ChangeHistoryEntry[];
  onRollbackChange: (changeId: string) => void;
  disabled?: boolean;
}

export const ChangeHistoryPanel: React.FC<ChangeHistoryPanelProps> = ({
  changeHistory,
  onRollbackChange,
  disabled = false
}) => {
  const [expanded, setExpanded] = useState(false);
  const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false);
  const [selectedChange, setSelectedChange] = useState<ChangeHistoryEntry | null>(null);

  const handleToggleExpanded = () => {
    setExpanded(!expanded);
  };

  const handleRollbackClick = (change: ChangeHistoryEntry) => {
    setSelectedChange(change);
    setRollbackDialogOpen(true);
  };

  const handleRollbackConfirm = () => {
    if (selectedChange) {
      onRollbackChange(selectedChange.id);
    }
    setRollbackDialogOpen(false);
    setSelectedChange(null);
  };

  const handleRollbackCancel = () => {
    setRollbackDialogOpen(false);
    setSelectedChange(null);
  };

  const getChangeIcon = (change: ManualDataChange) => {
    const indicator = ValidationErrorUtils.createChangeIndicator(change, false);

    if (change.isManualChange) {
      return <Person fontSize="small" sx={{ color: indicator.color }} />;
    } else {
      return <SmartToy fontSize="small" sx={{ color: indicator.color }} />;
    }
  };

  const getChangeStatusChip = (change: ManualDataChange) => {
    if (change.hasSchemaConflict) {
      return (
        <Chip
          size="small"
          icon={<Warning fontSize="small" />}
          label="Conflict"
          color="warning"
          variant="outlined"
        />
      );
    }

    return (
      <Chip
        size="small"
        label={change.isManualChange ? "Manual" : "Auto"}
        color={change.isManualChange ? "primary" : "secondary"}
        variant="outlined"
      />
    );
  };

  const formatTimestamp = (timestamp: Date): string => {
    return timestamp.toLocaleString();
  };

  const rollbackMessage = selectedChange ?
    ValidationErrorUtils.generateRollbackMessage(
      selectedChange.change,
      selectedChange.change.affectedValidationErrors?.length || 0
    ) : null;

  if (changeHistory.length === 0) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <History sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
        <Typography variant="body2" color="text.secondary">
          No changes made yet
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 2,
          cursor: 'pointer',
          '&:hover': {
            backgroundColor: 'action.hover'
          }
        }}
        onClick={handleToggleExpanded}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <History fontSize="small" />
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
            Change History ({changeHistory.length})
          </Typography>
        </Box>
        <IconButton size="small">
          {expanded ? <ExpandLess /> : <ExpandMore />}
        </IconButton>
      </Box>

      {/* Content */}
      <Collapse in={expanded}>
        <Divider />
        <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
          <List dense>
            {changeHistory.slice().reverse().map((entry, index) => (
              <ListItem key={entry.id} divider={index < changeHistory.length - 1}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 1 }}>
                  {getChangeIcon(entry.change)}
                </Box>
                <ListItemText
                  primary={
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                        {entry.change.description}
                      </Typography>
                      {getChangeStatusChip(entry.change)}
                    </span>
                  }
                  secondary={
                    <>
                      <Typography variant="caption" color="text.secondary">
                        {formatTimestamp(entry.change.timestamp)}
                      </Typography>
                      {entry.change.affectedValidationErrors && entry.change.affectedValidationErrors.length > 0 && (
                        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                          • {entry.change.affectedValidationErrors.length} validation error(s) affected
                        </Typography>
                      )}
                      {entry.change.hasSchemaConflict && entry.change.schemaConflictWarning && (
                        <span style={{ display: 'block', marginTop: '4px' }}>
                          <Alert severity="warning" sx={{ py: 0, fontSize: '0.75rem' }}>
                            {entry.change.schemaConflictWarning}
                          </Alert>
                        </span>
                      )}
                    </>
                  }
                />
                <ListItemSecondaryAction>
                  {entry.canRollback && (
                    <Tooltip title="Rollback this change">
                      <IconButton
                        size="small"
                        onClick={() => handleRollbackClick(entry)}
                        disabled={disabled}
                        color="primary"
                      >
                        <Undo fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Box>
      </Collapse>

      {/* Rollback Confirmation Dialog */}
      <Dialog
        open={rollbackDialogOpen}
        onClose={handleRollbackCancel}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Undo />
          {rollbackMessage?.title || 'Confirm Rollback'}
        </DialogTitle>
        <DialogContent>
          {rollbackMessage && (
            <Box>
              <Typography variant="body1" gutterBottom>
                {rollbackMessage.message}
              </Typography>

              {rollbackMessage.warnings.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                      Please note:
                    </Typography>
                    <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                      {rollbackMessage.warnings.map((warning, index) => (
                        <li key={index}>
                          <Typography variant="body2">{warning}</Typography>
                        </li>
                      ))}
                    </ul>
                  </Alert>
                </Box>
              )}

              {selectedChange?.change.hasSchemaConflict && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    This change had schema conflicts. Rolling back will restore the previous state
                    but may reintroduce validation issues.
                  </Typography>
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleRollbackCancel}>
            Cancel
          </Button>
          <Button
            onClick={handleRollbackConfirm}
            variant="contained"
            color="primary"
            startIcon={<Undo />}
          >
            Rollback Change
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
