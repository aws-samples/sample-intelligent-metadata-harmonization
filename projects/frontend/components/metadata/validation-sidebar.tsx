/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Button,
  Typography,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
  Paper,
  LinearProgress,
  Alert,
  Snackbar,
  Tabs,
  Tab,
  Badge,
  Collapse,
  IconButton
} from '@mui/material';
import { Send, Refresh, Error, Transform, ExpandMore } from '@mui/icons-material';
import { useAuth } from 'react-oidc-context';
import {
  updateValidationJob,
  pollValidationStatus,
  submitMetadataValidation
} from '../../lib/api';
import {
  ValidationJobStatus,
  ValidationStatusResponse,
  ValidationError,
  Change,
  SchemaAlignmentChangeDetail,
  SchemaAlignmentResults,
  ChangeTrackingResults
} from '../../lib/types';
import { ValidationErrorsPanel } from './validation-errors-panel';
import { SchemaChangesPanel } from './schema-changes-panel';

interface ValidationSidebarProps {
  data: string[][];
  changes: Change[];
  validationErrors?: ValidationError[] | null;
  schemaAlignmentResults?: SchemaAlignmentResults | null;
  // currentView removed - no longer using toggle functionality
  isSubmitting?: boolean;
  jobId?: string;
  coreSchemaId?: string;
  programSchemaId?: string;
  onValidationComplete: (jobId?: string, changeTracking?: ChangeTrackingResults) => void;
  onValidationErrors: (errors: ValidationError[], jobId?: string, schemaAlignmentResults?: SchemaAlignmentResults) => void;
  onApplyChange?: (change: ValidationError) => void;
  onApplyAllChanges?: (columnChanges: ValidationError[]) => void;
  onDisableSpreadsheet?: (disabled: boolean) => void;
  onAcceptSchemaChange?: (changeId: string) => void;
  onRevertSchemaChange?: (changeId: string) => void;
  // Manual schema transformation callbacks
  onApplyColumnRename?: (originalColumn: string, newColumn: string) => void;
  onApplyColumnAddition?: (newColumn: string) => void;
  onApplyColumnRemoval?: (columnName: string) => void;
  // Applied schema changes state
  appliedSchemaChangeIds?: Set<string>;
  getSchemaChangeId?: (change: SchemaAlignmentChangeDetail, index: number) => string;
  // Final data update callback for bulk operations
  onFinalDataUpdate?: (finalData: string[][]) => void;
  // Applied changes update callback for tracking state changes
  onAppliedChangesUpdate?: (changeId: string, isApplied: boolean) => void;
  // Bulk schema changes applied callback for UI change tracking
  onBulkSchemaChangesApplied?: (appliedChanges: Array<{ change: SchemaAlignmentChangeDetail; index: number; columnIndex?: number }>) => void;
  children?: React.ReactNode;
}

export const ValidationSidebarComponent: React.FC<ValidationSidebarProps> = ({
  data,
  changes,
  validationErrors = null,
  schemaAlignmentResults = null,
  // currentView removed - no longer using toggle functionality
  isSubmitting = false,
  jobId,
  coreSchemaId,
  programSchemaId,
  onValidationComplete,
  onValidationErrors,
  onApplyChange,
  onApplyAllChanges,
  onDisableSpreadsheet,
  onAcceptSchemaChange,
  onRevertSchemaChange,
  onApplyColumnRename,
  onApplyColumnAddition,
  onApplyColumnRemoval,
  appliedSchemaChangeIds,
  getSchemaChangeId,
  onFinalDataUpdate,
  onAppliedChangesUpdate,
  onBulkSchemaChangesApplied,
  children
}) => {
  const auth = useAuth();

  // State management for submission and polling
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<ValidationJobStatus | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | undefined>(jobId);
  const [error, setError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [pollingProgress, setPollingProgress] = useState(0);

  // Tab state management - Schema Changes tab first, then Validation Errors tab
  const [activeTab, setActiveTab] = useState<'schema' | 'validation'>('schema');

  // Recent Changes collapsible state - default to collapsed
  const [recentChangesExpanded, setRecentChangesExpanded] = useState(false);

  // Update jobId when prop changes
  useEffect(() => {
    setCurrentJobId(jobId);
  }, [jobId]);

  // Disable spreadsheet during processing or polling
  useEffect(() => {
    const shouldDisable = isProcessing || isPolling;
    if (onDisableSpreadsheet) {
      onDisableSpreadsheet(shouldDisable);
    }
  }, [isProcessing, isPolling, onDisableSpreadsheet]);

  const convertDataToCSV = useCallback((data: string[][]): string => {
    return data.map(row =>
      row.map(cell => {
        // Escape cells that contain commas, quotes, or newlines
        if (cell.includes(',') || cell.includes('"') || cell.includes('\n')) {
          return `"${cell.replace(/"/g, '""')}"`;
        }
        return cell;
      }).join(',')
    ).join('\n');
  }, []);

  const handleStatusUpdate = useCallback((status: ValidationJobStatus, response: ValidationStatusResponse) => {
    console.log('Status update received:', status, response);
    setCurrentStatus(status);

    // Update progress based on status
    switch (status) {
      case ValidationJobStatus.PENDING:
        setPollingProgress(25);
        break;
      case ValidationJobStatus.PROCESSING:
        setPollingProgress(50);
        break;
      case ValidationJobStatus.COMPLETED:
      case ValidationJobStatus.COMPLETED_WITH_ERRORS:
      case ValidationJobStatus.FAILED:
        setPollingProgress(100);
        break;
    }
  }, []);

  const handleSubmit = async () => {
    if (isProcessing || isPolling) return;

    // Validate required data
    if (!data || data.length === 0) {
      setError('No data to validate');
      setSnackbarOpen(true);
      return;
    }

    // For initial submission, require schema IDs
    if (!currentJobId && (!coreSchemaId || !programSchemaId)) {
      setError('Core and Program schema IDs are required for validation');
      setSnackbarOpen(true);
      return;
    }

    setIsProcessing(true);
    setError(null);
    setCurrentStatus(null);
    setPollingProgress(0);

    try {
      console.log('Starting validation submission...');

      let response;

      if (currentJobId) {
        // Resubmission - update existing job
        console.log('Resubmitting validation job:', currentJobId);

        // Convert data to CSV and create file
        const csvContent = convertDataToCSV(data);
        const csvFile = new File([csvContent], 'metadata.csv', { type: 'text/csv' });

        response = await updateValidationJob(
          currentJobId,
          csvFile,
          auth.user?.id_token
        );
      } else {
        // Initial submission - create new job
        console.log('Creating new validation job with schemas:', { coreSchemaId, programSchemaId });

        response = await submitMetadataValidation(
          data,
          coreSchemaId!,
          programSchemaId!,
          auth.user?.id_token
        );
      }

      if (!response.success) {
        const errorMessage = response.error || 'Failed to submit validation job';
        throw { message: errorMessage };
      }

      if (!response.jobId) {
        const errorMessage = 'No job ID returned from validation service';
        throw { message: errorMessage };
      }

      console.log('Validation job created/updated successfully:', response.jobId);
      setCurrentJobId(response.jobId);
      setIsProcessing(false);

      // Start polling for results
      console.log('Starting polling for job:', response.jobId);
      setIsPolling(true);
      setCurrentStatus(ValidationJobStatus.PENDING);
      setPollingProgress(10);

      const pollResult = await pollValidationStatus(
        response.jobId,
        handleStatusUpdate,
        auth.user?.id_token,
        {
          pollInterval: 2000, // 2 seconds
          maxAttempts: 150,   // 5 minutes max
          timeoutMs: 300000   // 5 minutes timeout
        }
      );

      console.log('Polling completed with result:', pollResult);

      if (!pollResult.success) {
        const errorMessage = pollResult.error || 'Validation polling failed';
        throw { message: errorMessage };
      }

      // Process final results
      const finalStatus = pollResult.status;
      if (finalStatus === ValidationJobStatus.COMPLETED) {
        // Validation completed successfully - check if there are any validation errors
        if (pollResult.latestResults && pollResult.latestResults.validationResults && pollResult.latestResults.validationResults.validationResults.length > 0) {
          // Has validation errors - stay on edit page
          console.log('Validation completed with errors:', pollResult.latestResults.validationResults.validationResults.length);
          onValidationErrors(
            pollResult.latestResults.validationResults.validationResults,
            response.jobId,
            pollResult.latestResults.schemaAlignmentResults || undefined
          );
        } else {
          // No errors - navigate to complete page
          console.log('Validation completed successfully with no errors');
          const changeTracking = pollResult.latestResults?.changeTracking || undefined;
          console.log('Change tracking data:', changeTracking);
          onValidationComplete(response.jobId, changeTracking);
        }
      } else if (finalStatus === ValidationJobStatus.COMPLETED_WITH_ERRORS) {
        // Validation completed but with errors - always stay on edit page to show errors
        console.log('Validation completed with errors (COMPLETED_WITH_ERRORS status)');
        if (pollResult.latestResults && pollResult.latestResults.validationResults) {
          onValidationErrors(
            pollResult.latestResults.validationResults.validationResults,
            response.jobId,
            pollResult.latestResults.schemaAlignmentResults || undefined
          );
        } else {
          // This shouldn't happen - COMPLETED_WITH_ERRORS should always have validation results
          console.warn('COMPLETED_WITH_ERRORS status but no validation results found');
          onValidationErrors([], response.jobId);
        }
      } else if (finalStatus === ValidationJobStatus.FAILED) {
        // Job failed on the server - stay on validation page and show error
        console.error('Validation job failed on server:', pollResult);
        throw { message: 'Validation job failed on the server. Please check your data and try again.' };
      } else {
        throw { message: `Unexpected final status: ${pollResult.status}` };
      }

    } catch (error) {
      console.error('Validation submission/polling failed:', error);
      const errorMessage = (error as any)?.message || 'Validation failed. Please try again.';
      setError(errorMessage);
      setSnackbarOpen(true);
    } finally {
      setIsProcessing(false);
      setIsPolling(false);
      setCurrentStatus(null);
      setPollingProgress(0);
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: 'schema' | 'validation') => {
    setActiveTab(newValue);

    // Scroll to top when switching tabs for better user experience
    const tabContentElement = document.querySelector('[data-tab-content="true"]');
    if (tabContentElement && typeof tabContentElement.scrollTo === 'function') {
      tabContentElement.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleRecentChangesToggle = () => {
    setRecentChangesExpanded(!recentChangesExpanded);
  };

  const handleRecentChangesKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleRecentChangesToggle();
    }
  };

  const formatChangeText = (change: Change): string => {
    const columnName = data[0]?.[change.column] || `Col ${change.column}`;
    return `Row ${change.row + 1}, ${columnName}: "${change.oldValue}" → "${change.newValue}"`;
  };

  const getRecentChanges = () => {
    return changes.slice(-5).reverse(); // Show last 5 changes, most recent first
  };

  const getSubmitButtonText = () => {
    if (isProcessing) return 'Submitting...';
    if (isPolling) {
      switch (currentStatus) {
        case ValidationJobStatus.PENDING:
          return 'Queued for Processing...';
        case ValidationJobStatus.PROCESSING:
          return 'Processing...';
        default:
          return 'Validating...';
      }
    }
    return currentJobId ? 'Resubmit for Validation' : 'Submit for Validation';
  };

  const getSubmitButtonIcon = () => {
    if (isProcessing || isPolling) {
      return <CircularProgress size={20} color="inherit" />;
    }
    return currentJobId ? <Refresh /> : <Send />;
  };

  const isSubmitDisabled = isProcessing || isPolling || isSubmitting;

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderLeft: 1,
        borderColor: 'divider',
        backgroundColor: 'background.paper',
        overflow: 'hidden' // Prevent main container from scrolling
      }}
    >
      {/* Submit Button Section */}
      <Box sx={{ p: 2 }}>
        <Button
          variant="contained"
          fullWidth
          size="large"
          startIcon={getSubmitButtonIcon()}
          onClick={handleSubmit}
          disabled={isSubmitDisabled}
          sx={{
            minHeight: 48,
            fontWeight: 'bold'
          }}
        >
          {getSubmitButtonText()}
        </Button>

        {/* Polling Progress */}
        {isPolling && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress
              variant="determinate"
              value={pollingProgress}
              sx={{ mb: 1 }}
            />
            <Typography variant="caption" color="text.secondary" align="center" display="block">
              {currentStatus === ValidationJobStatus.PENDING && 'Waiting in queue...'}
              {currentStatus === ValidationJobStatus.PROCESSING && 'Processing your data...'}
              {!currentStatus && 'Initializing validation...'}
            </Typography>
          </Box>
        )}

        {/* Status Display */}
        {currentStatus && !isPolling && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary" align="center" display="block">
              Last status: {currentStatus}
            </Typography>
          </Box>
        )}
      </Box>

      <Divider />

      {/* Recent Changes Section - Collapsible */}
      <Box sx={{ p: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: 'action.hover',
              borderRadius: 1
            },
            p: 0.5,
            mx: -0.5
          }}
          onClick={handleRecentChangesToggle}
          onKeyDown={handleRecentChangesKeyDown}
          tabIndex={0}
          role="button"
          aria-expanded={recentChangesExpanded}
          aria-label={`${recentChangesExpanded ? 'Collapse' : 'Expand'} Recent Changes section`}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
            Recent Changes ({changes.length})
          </Typography>
          <IconButton
            size="small"
            sx={{
              transition: 'transform 0.2s ease-in-out',
              transform: recentChangesExpanded ? 'rotate(0deg)' : 'rotate(-90deg)'
            }}
            aria-label={recentChangesExpanded ? 'Collapse' : 'Expand'}
          >
            <ExpandMore />
          </IconButton>
        </Box>

        <Collapse in={recentChangesExpanded} timeout="auto" unmountOnExit>
          <Box sx={{ mt: 1 }}>
            {changes.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                No changes made yet
              </Typography>
            ) : (
              <Paper variant="outlined" sx={{ maxHeight: 150, overflow: 'auto', p: 1 }}>
                <List dense>
                  {getRecentChanges().map((change) => (
                    <ListItem key={`${change.row}-${change.column}-${change.timestamp.getTime()}`} sx={{ px: 1 }}>
                      <ListItemText
                        primary={formatChangeText(change)}
                        primaryTypographyProps={{
                          variant: 'body2',
                          sx: { fontSize: '0.875rem' }
                        }}
                        secondary={change.timestamp.toLocaleTimeString()}
                        secondaryTypographyProps={{
                          variant: 'caption',
                          color: 'text.secondary'
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            )}
          </Box>
        </Collapse>
      </Box>

      <Divider />

      {/* Tabbed Interface */}
      <Box sx={{ flexGrow: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* Tab Navigation - Schema Changes first, then Validation Errors - Fixed Header */}
        <Box sx={{
          borderBottom: 1,
          borderColor: 'divider',
          flexShrink: 0,
          backgroundColor: 'background.paper',
          zIndex: 1
        }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="fullWidth"
            sx={{ minHeight: 48 }}
          >
            <Tab
              label={
                (() => {
                  // Calculate pending (unapplied) schema changes count
                  const totalChanges = schemaAlignmentResults?.schemaAlignmentResults || [];
                  const pendingCount = totalChanges.filter((change, index) => {
                    if (!getSchemaChangeId) {
                      // Fallback: if no getSchemaChangeId function, assume all are pending
                      return true;
                    }
                    const changeId = getSchemaChangeId(change, index);
                    return !appliedSchemaChangeIds?.has(changeId);
                  }).length;

                  return (
                    <Badge badgeContent={pendingCount > 0 ? pendingCount : undefined} color="error" max={99}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Transform fontSize="small" />
                        <Typography variant="body2" sx={{ fontWeight: 'inherit' }}>
                          Schema Changes
                        </Typography>
                      </Box>
                    </Badge>
                  );
                })()
              }
              value="schema"
              sx={{
                minHeight: 48,
                textTransform: 'none',
                fontSize: '0.875rem'
              }}
            />
            <Tab
              label={
                <Badge badgeContent={validationErrors?.length && validationErrors.length > 0 ? validationErrors.length : undefined} color="warning" max={99}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Error fontSize="small" />
                    <Typography variant="body2" sx={{ fontWeight: 'inherit' }}>
                      Validation Errors
                    </Typography>
                  </Box>
                </Badge>
              }
              value="validation"
              sx={{
                minHeight: 48,
                textTransform: 'none',
                fontSize: '0.875rem'
              }}
            />
          </Tabs>
        </Box>

        {/* Tab Content - Let individual panels handle scrolling */}
        <Box
          sx={{
            flexGrow: 1,
            overflow: 'hidden', // Don't scroll at this level
            p: 2,
            minHeight: 0, // Allow flex child to shrink below content size
            maxHeight: 'calc(100vh - 325px)', // Constrain to available space minus other elements
            display: 'flex',
            flexDirection: 'column'
          }}
          data-tab-content="true"
        >
          {activeTab === 'schema' && (
            <Box sx={{ flexGrow: 1, minHeight: 0, overflow: 'hidden' }}>
              <SchemaChangesPanel
                changes={schemaAlignmentResults?.schemaAlignmentResults || []}
                currentColumns={data[0] || []}
                currentData={data}
                onFinalDataUpdate={onFinalDataUpdate}
                onAppliedChangesUpdate={onAppliedChangesUpdate}
                onBulkSchemaChangesApplied={onBulkSchemaChangesApplied}
                onAcceptChange={onAcceptSchemaChange || (() => { })}
                onRevertChange={onRevertSchemaChange || (() => { })}
                onApplyColumnRename={onApplyColumnRename}
                onApplyColumnAddition={onApplyColumnAddition}
                onApplyColumnRemoval={onApplyColumnRemoval}
                appliedChangeIds={appliedSchemaChangeIds}
                getChangeId={getSchemaChangeId}
              />
            </Box>
          )}

          {activeTab === 'validation' && (
            <Box sx={{ flexGrow: 1, minHeight: 0, overflow: 'hidden' }}>
              <ValidationErrorsPanel
                errors={validationErrors || []}
                // currentView removed - no longer using toggle functionality
                isLoading={isPolling}
                onAcceptError={onApplyChange}
                onAcceptAllErrors={onApplyAllChanges}
              >
                {children}
              </ValidationErrorsPanel>
            </Box>
          )}
        </Box>
      </Box>

      {/* Job ID Footer */}
      {currentJobId && (
        <Box sx={{
          p: 2,
          pt: 1,
          borderTop: 1,
          borderColor: 'divider',
          backgroundColor: 'grey.50'
        }}>
          <Typography
            variant="body2"
            sx={{
              fontSize: '0.75rem',
              color: 'text.secondary',
              lineHeight: 1.2,
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}
          >
            <span style={{ fontWeight: 'bold' }}>Job ID</span>
            <span style={{
              fontFamily: 'monospace',
              fontSize: '0.7rem',
              wordBreak: 'break-all',
              flex: 1,
              minWidth: 0
            }}>
              {currentJobId}
            </span>
          </Typography>
        </Box>
      )}

      {/* Error Snackbar */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};
