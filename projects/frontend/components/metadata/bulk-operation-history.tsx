/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  Stack,
  Divider
} from '@mui/material';
import {
  ExpandMore,
  History,
  CheckCircle,
  Error,
  Warning,
  Undo,
  Refresh,
  Delete,
  Info
} from '@mui/icons-material';
import { SchemaAlignmentChangeDetail } from '../../lib/types';
import {
  BulkOperationResult,
  ConfidenceDistribution,
  calculateConfidenceDistribution,
  getConfidenceColor
} from '../../lib/transformation-operations';

/**
 * Bulk operation history entry with confidence information
 */
export interface BulkOperationHistoryEntry {
  id: string;
  timestamp: Date;
  operationType: 'apply' | 'revert';
  selectedChanges: SchemaAlignmentChangeDetail[];
  result: BulkOperationResult;
  canRollback: boolean;
}

interface BulkOperationHistoryProps {
  /** Whether dialog is open */
  open: boolean;
  /** Callback to close dialog */
  onClose: () => void;
  /** Operation history entries */
  history: BulkOperationHistoryEntry[];
  /** Callback to rollback an operation */
  onRollback?: (entryId: string) => Promise<void>;
  /** Callback to clear history */
  onClearHistory?: () => void;
  /** Callback to retry failed operations */
  onRetryOperation?: (entryId: string) => Promise<void>;
}

/**
 * Compact confidence distribution display for history entries
 */
const CompactConfidenceDisplay: React.FC<{
  distribution: ConfidenceDistribution;
}> = ({ distribution }) => {
  const total = distribution.high + distribution.medium + distribution.low;

  if (total === 0) {
    return (
      <Typography variant="caption" color="text.secondary">
        No confidence data
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Typography variant="caption" color="text.secondary">
        Confidence:
      </Typography>
      <Box sx={{ display: 'flex', gap: 0.5 }}>
        {distribution.high > 0 && (
          <Chip
            label={distribution.high}
            size="small"
            sx={{
              backgroundColor: getConfidenceColor('High'),
              color: 'white',
              fontSize: '0.7rem',
              height: 18,
              minWidth: 24
            }}
          />
        )}
        {distribution.medium > 0 && (
          <Chip
            label={distribution.medium}
            size="small"
            sx={{
              backgroundColor: getConfidenceColor('Medium'),
              color: 'white',
              fontSize: '0.7rem',
              height: 18,
              minWidth: 24
            }}
          />
        )}
        {distribution.low > 0 && (
          <Chip
            label={distribution.low}
            size="small"
            sx={{
              backgroundColor: getConfidenceColor('Low'),
              color: 'white',
              fontSize: '0.7rem',
              height: 18,
              minWidth: 24
            }}
          />
        )}
      </Box>
      <Typography variant="caption" color="text.secondary">
        (Avg: {(distribution.averageScore * 100).toFixed(0)}%)
      </Typography>
    </Box>
  );
};

/**
 * Bulk operation history dialog with rollback capabilities
 */
export const BulkOperationHistory: React.FC<BulkOperationHistoryProps> = ({
  open,
  onClose,
  history,
  onRollback,
  onClearHistory,
  onRetryOperation
}) => {
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);
  const [isRollingBack, setIsRollingBack] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState<string | null>(null);

  // Format timestamp
  const formatTimestamp = (date: Date): string => {
    return date.toLocaleString();
  };

  // Format duration
  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  // Handle rollback
  const handleRollback = async (entryId: string) => {
    if (!onRollback) return;

    setIsRollingBack(entryId);
    try {
      await onRollback(entryId);
    } catch (error) {
      console.error('Rollback failed:', error);
    } finally {
      setIsRollingBack(null);
    }
  };

  // Handle retry
  const handleRetry = async (entryId: string) => {
    if (!onRetryOperation) return;

    setIsRetrying(entryId);
    try {
      await onRetryOperation(entryId);
    } catch (error) {
      console.error('Retry failed:', error);
    } finally {
      setIsRetrying(null);
    }
  };

  // Handle clear history
  const handleClearHistory = () => {
    if (onClearHistory) {
      onClearHistory();
    }
  };

  // Get operation status color
  const getStatusColor = (result: BulkOperationResult): 'success' | 'warning' | 'error' => {
    if (result.success) return 'success';
    if (result.summary.successfulOperations > 0) return 'warning';
    return 'error';
  };

  // Get operation status text
  const getStatusText = (result: BulkOperationResult): string => {
    if (result.success) return 'Success';
    if (result.summary.successfulOperations > 0) return 'Partial Success';
    return 'Failed';
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <History />
            <Typography variant="h6">
              Bulk Operation History
            </Typography>
          </Box>
          {history.length > 0 && onClearHistory && (
            <Tooltip title="Clear all history">
              <IconButton onClick={handleClearHistory} size="small">
                <Delete />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        {history.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <History sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="body1" color="text.secondary" gutterBottom>
              No Operation History
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Bulk operations you perform will appear here with rollback options.
            </Typography>
          </Box>
        ) : (
          <Stack spacing={2}>
            {history.map((entry) => (
              <Card key={entry.id} variant="outlined">
                <Accordion
                  expanded={expandedEntry === entry.id}
                  onChange={() => setExpandedEntry(expandedEntry === entry.id ? null : entry.id)}
                >
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', pr: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Chip
                          icon={
                            entry.result.success ? <CheckCircle /> :
                            entry.result.summary.successfulOperations > 0 ? <Warning /> :
                            <Error />
                          }
                          label={getStatusText(entry.result)}
                          color={getStatusColor(entry.result)}
                          size="small"
                        />
                        <Typography variant="subtitle2">
                          {entry.operationType === 'apply' ? 'Applied' : 'Reverted'} {entry.selectedChanges.length} changes
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Typography variant="caption" color="text.secondary">
                          {formatTimestamp(entry.timestamp)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatDuration(entry.result.summary.totalDuration)}
                        </Typography>
                        {/* Compact confidence display */}
                        <CompactConfidenceDisplay
                          distribution={entry.result.confidenceDistribution}
                        />
                      </Box>
                    </Box>
                  </AccordionSummary>

                  <AccordionDetails>
                    <Stack spacing={3}>
                      {/* Operation Summary */}
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Operation Summary
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          <Chip
                            label={`${entry.result.summary.totalOperations} total`}
                            size="small"
                          />
                          <Chip
                            label={`${entry.result.summary.successfulOperations} successful`}
                            color="success"
                            size="small"
                          />
                          {entry.result.summary.failedOperations > 0 && (
                            <Chip
                              label={`${entry.result.summary.failedOperations} failed`}
                              color="error"
                              size="small"
                            />
                          )}
                          {entry.result.summary.cancelledOperations > 0 && (
                            <Chip
                              label={`${entry.result.summary.cancelledOperations} cancelled`}
                              color="warning"
                              size="small"
                            />
                          )}
                          <Chip
                            label={`${formatDuration(entry.result.summary.averageOperationTime)} avg`}
                            size="small"
                          />
                        </Box>
                      </Box>

                      {/* Affected Changes */}
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Affected Changes ({entry.selectedChanges.length})
                        </Typography>
                        <List dense sx={{ maxHeight: 200, overflow: 'auto' }}>
                          {entry.selectedChanges.map((change, index) => (
                            <ListItem key={index} dense>
                              <ListItemIcon>
                                <Chip
                                  label={change.changeType}
                                  size="small"
                                  color={
                                    change.changeType.toLowerCase() === 'remove' ? 'warning' :
                                    change.changeType.toLowerCase() === 'add' ? 'success' : 'info'
                                  }
                                />
                              </ListItemIcon>
                              <ListItemText
                                primary={
                                  change.changeType.toLowerCase() === 'rename'
                                    ? `${change.originalColumn} → ${change.newColumn}`
                                    : change.originalColumn || change.newColumn
                                }
                                secondary={change.reason}
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Box>

                      {/* Error Details */}
                      {entry.result.errorReport && entry.result.errorReport.errors.length > 0 && (
                        <Box>
                          <Typography variant="subtitle2" gutterBottom>
                            Error Details ({entry.result.errorReport.errors.length} errors)
                          </Typography>
                          <Alert severity="error">
                            <List dense>
                              {entry.result.errorReport.errors.slice(0, 3).map((error, index) => (
                                <ListItem key={index} dense>
                                  <ListItemText
                                    primary={`${error.change.changeType}: ${error.change.originalColumn || error.change.newColumn}`}
                                    secondary={error.error.message}
                                  />
                                </ListItem>
                              ))}
                            </List>
                            {entry.result.errorReport.errors.length > 3 && (
                              <Typography variant="caption">
                                ... and {entry.result.errorReport.errors.length - 3} more errors
                              </Typography>
                            )}
                          </Alert>
                        </Box>
                      )}

                      {/* Recovery Options */}
                      {entry.result.errorReport && entry.result.errorReport.recoveryOptions.length > 0 && (
                        <Box>
                          <Typography variant="subtitle2" gutterBottom>
                            Recovery Options
                          </Typography>
                          <Alert severity="info">
                            <ul style={{ margin: 0, paddingLeft: 20 }}>
                              {entry.result.errorReport.recoveryOptions.map((option, index) => (
                                <li key={index}>{option}</li>
                              ))}
                            </ul>
                          </Alert>
                        </Box>
                      )}

                      {/* Actions */}
                      <Divider />
                      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                        {entry.canRollback && onRollback && (
                          <Button
                            startIcon={<Undo />}
                            onClick={() => handleRollback(entry.id)}
                            disabled={isRollingBack === entry.id}
                            color="warning"
                            size="small"
                          >
                            {isRollingBack === entry.id ? 'Rolling back...' : 'Rollback'}
                          </Button>
                        )}
                        {entry.result.errorReport && entry.result.errorReport.errors.length > 0 && onRetryOperation && (
                          <Button
                            startIcon={<Refresh />}
                            onClick={() => handleRetry(entry.id)}
                            disabled={isRetrying === entry.id}
                            color="primary"
                            size="small"
                          >
                            {isRetrying === entry.id ? 'Retrying...' : 'Retry Failed'}
                          </Button>
                        )}
                      </Box>
                    </Stack>
                  </AccordionDetails>
                </Accordion>
              </Card>
            ))}
          </Stack>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};
