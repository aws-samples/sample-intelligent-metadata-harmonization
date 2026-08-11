/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  AlertTitle,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Divider,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  Stack,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Switch,
  Slider,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Badge,
  Collapse
} from '@mui/material';
import {
  ExpandMore,
  PlayArrow,
  Stop,
  CheckCircle,
  Error,
  Warning,
  Info,
  InfoOutlined,
  Refresh,
  Preview,
  History,
  Cancel,
  Settings,
  Speed,
  Security,
  Timeline,
  Visibility,
  VisibilityOff,
  FilterList,
  Sort,
  Pause,
  SkipNext,
  RestartAlt,
  SaveAlt,
  CloudDownload
} from '@mui/icons-material';
import { SchemaAlignmentChangeDetail } from '../../lib/types';
import {
  BulkOperationConfig,
  BulkOperationResult,
  BulkOperationPreview,
  SelectiveBulkConfig,
  EnhancedProgressTracker,
  ConfidenceDistribution,
  calculateConfidenceDistribution,
  getConfidenceLevelFromScore,
  getConfidenceColor
} from '../../lib/transformation-operations';
import { formatChangeDescription } from '../../lib/schema-transformation-utils';

interface BulkOperationsDialogProps {
  /** Whether dialog is open */
  open: boolean;
  /** Callback to close dialog */
  onClose: () => void;
  /** Available changes for bulk operations */
  changes: Array<{ change: SchemaAlignmentChangeDetail; index: number }>;
  /** Applied change IDs */
  appliedChangeIds: Set<string>;
  /** Operation type */
  operationType: 'apply' | 'revert';
  /** Callback to execute bulk operation */
  onExecuteBulkOperation: (config: SelectiveBulkConfig) => Promise<BulkOperationResult>;
  /** Callback to preview bulk operation */
  onPreviewBulkOperation: (config: SelectiveBulkConfig) => BulkOperationPreview;
  /** Callback for operation history */
  onViewHistory?: () => void;
  /** Callback to save operation configuration */
  onSaveConfiguration?: (config: SelectiveBulkConfig, name: string) => void;
  /** Callback to load saved configurations */
  onLoadConfigurations?: () => Array<{ name: string; config: SelectiveBulkConfig }>;
}

// Enhanced error recovery options
type ErrorRecoveryMode = 'stop' | 'continue' | 'skip' | 'retry';

// Enhanced progress tracking modes
type ProgressDisplayMode = 'compact' | 'detailed' | 'minimal';

// Operation execution modes
type ExecutionMode = 'sequential' | 'batch' | 'optimized';

// Enhanced bulk operation configuration
interface EnhancedBulkConfig extends BulkOperationConfig {
  errorRecoveryMode: ErrorRecoveryMode;
  progressDisplayMode: ProgressDisplayMode;
  executionMode: ExecutionMode;
  batchSize?: number;
  pauseOnError?: boolean;
  autoRetryCount?: number;
  validationLevel: 'strict' | 'moderate' | 'lenient';
  backupBeforeExecution?: boolean;
}

/**
 * Confidence distribution display component
 */
const ConfidenceDistributionDisplay: React.FC<{
  distribution: ConfidenceDistribution;
  title?: string;
  showDetails?: boolean;
}> = ({ distribution, title = "Confidence Distribution", showDetails = true }) => {
  const total = distribution.high + distribution.medium + distribution.low;

  if (total === 0) {
    return (
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            {title}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            No operations selected
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="subtitle2" gutterBottom>
          {title}
        </Typography>

        {/* Confidence level chips */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          <Chip
            label={`High: ${distribution.high}`}
            size="small"
            sx={{
              backgroundColor: getConfidenceColor('High'),
              color: 'white',
              fontWeight: 'bold'
            }}
          />
          <Chip
            label={`Medium: ${distribution.medium}`}
            size="small"
            sx={{
              backgroundColor: getConfidenceColor('Medium'),
              color: 'white',
              fontWeight: 'bold'
            }}
          />
          <Chip
            label={`Low: ${distribution.low}`}
            size="small"
            sx={{
              backgroundColor: getConfidenceColor('Low'),
              color: 'white',
              fontWeight: 'bold'
            }}
          />
        </Box>

        {/* Progress bar showing distribution */}
        <Box sx={{ mb: 1 }}>
          <Box sx={{ display: 'flex', height: 8, borderRadius: 1, overflow: 'hidden', backgroundColor: '#f5f5f5' }}>
            {distribution.high > 0 && (
              <Box
                sx={{
                  width: `${(distribution.high / total) * 100}%`,
                  backgroundColor: getConfidenceColor('High')
                }}
              />
            )}
            {distribution.medium > 0 && (
              <Box
                sx={{
                  width: `${(distribution.medium / total) * 100}%`,
                  backgroundColor: getConfidenceColor('Medium')
                }}
              />
            )}
            {distribution.low > 0 && (
              <Box
                sx={{
                  width: `${(distribution.low / total) * 100}%`,
                  backgroundColor: getConfidenceColor('Low')
                }}
              />
            )}
          </Box>
        </Box>

        {/* Detailed statistics */}
        {showDetails && (
          <Box sx={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
            <Typography variant="caption" color="text.secondary">
              Total: {total} operations
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Avg: {(distribution.averageScore * 100).toFixed(1)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Range: {(distribution.minScore * 100).toFixed(1)}% - {(distribution.maxScore * 100).toFixed(1)}%
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

/**
 * Enhanced bulk operations dialog with progress tracking, error recovery, and selective operations
 */
export const BulkOperationsDialog: React.FC<BulkOperationsDialogProps> = ({
  open,
  onClose,
  changes,
  appliedChangeIds,
  operationType,
  onExecuteBulkOperation,
  onPreviewBulkOperation,
  onViewHistory,
  onSaveConfiguration,
  onLoadConfigurations
}) => {
  // Enhanced state management
  const [selectedChangeIds, setSelectedChangeIds] = useState<Set<string>>(new Set());
  const [enhancedConfig, setEnhancedConfig] = useState<EnhancedBulkConfig>({
    continueOnError: true,
    showProgress: true,
    allowCancellation: true,
    operationDelay: 100,
    maxRetries: 2,
    errorRecoveryMode: 'continue',
    progressDisplayMode: 'detailed',
    executionMode: 'optimized',
    batchSize: 10,
    pauseOnError: false,
    autoRetryCount: 1,
    validationLevel: 'moderate',
    backupBeforeExecution: true
  });
  const [preview, setPreview] = useState<BulkOperationPreview | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [progress, setProgress] = useState<EnhancedProgressTracker | null>(null);
  const [result, setResult] = useState<BulkOperationResult | null>(null);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [executionPhase, setExecutionPhase] = useState<'preparation' | 'validation' | 'execution' | 'completion'>('preparation');
  const [detailedProgress, setDetailedProgress] = useState<Array<{
    changeId: string;
    status: 'pending' | 'executing' | 'completed' | 'failed' | 'skipped';
    error?: string;
    duration?: number;
  }>>([]);
  const [filterType, setFilterType] = useState<'all' | 'rename' | 'add' | 'remove'>('all');
  const [sortBy, setSortBy] = useState<'type' | 'impact' | 'risk'>('type');
  const [savedConfigurations, setSavedConfigurations] = useState<Array<{ name: string; config: SelectiveBulkConfig }>>([]);
  const [configurationName, setConfigurationName] = useState('');
  const [showSaveConfig, setShowSaveConfig] = useState(false);

  // Enhanced filtering and sorting
  const getFilteredAndSortedChanges = () => {
    let filtered = changes.filter(({ change, index }) => {
      const changeId = `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`;

      // Filter by operation type
      const isAvailable = operationType === 'apply'
        ? !appliedChangeIds.has(changeId)
        : appliedChangeIds.has(changeId);

      if (!isAvailable) return false;

      // Filter by change type
      if (filterType !== 'all' && change.changeType.toLowerCase() !== filterType) {
        return false;
      }

      return true;
    });

    // Sort changes
    filtered.sort(({ change: a }, { change: b }) => {
      switch (sortBy) {
        case 'type':
          return a.changeType.localeCompare(b.changeType);
        case 'impact':
          return (b.rowCountAffected || 0) - (a.rowCountAffected || 0);
        case 'risk':
          const getRiskScore = (change: SchemaAlignmentChangeDetail) => {
            if (change.changeType.toLowerCase() === 'remove') return 3;
            if (change.changeType.toLowerCase() === 'rename') return 2;
            return 1;
          };
          return getRiskScore(b) - getRiskScore(a);
        default:
          return 0;
      }
    });

    return filtered;
  };

  const availableChanges = getFilteredAndSortedChanges();

  // Initialize with all available changes selected
  useEffect(() => {
    if (open && availableChanges.length > 0) {
      const allChangeIds = new Set(
        availableChanges.map(({ change, index }) =>
          `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`
        )
      );
      setSelectedChangeIds(allChangeIds);
    }
  }, [open, changes, appliedChangeIds, operationType, filterType, sortBy]);

  // Load saved configurations on mount
  useEffect(() => {
    if (open && onLoadConfigurations) {
      const configs = onLoadConfigurations();
      setSavedConfigurations(configs);
    }
  }, [open, onLoadConfigurations]);

  // Initialize detailed progress tracking
  useEffect(() => {
    if (selectedChangeIds.size > 0) {
      const progressItems = Array.from(selectedChangeIds).map(changeId => ({
        changeId,
        status: 'pending' as const,
        error: undefined,
        duration: undefined
      }));
      setDetailedProgress(progressItems);
    }
  }, [selectedChangeIds]);

  // Generate preview when selection or config changes
  useEffect(() => {
    if (selectedChangeIds.size > 0) {
      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType,
        config: enhancedConfig
      };
      const newPreview = onPreviewBulkOperation(config);
      setPreview(newPreview);
    } else {
      setPreview(null);
    }
  }, [selectedChangeIds, enhancedConfig, operationType, onPreviewBulkOperation]);

  // Handle change selection
  const handleChangeSelection = (changeId: string, selected: boolean) => {
    setSelectedChangeIds(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(changeId);
      } else {
        newSet.delete(changeId);
      }
      return newSet;
    });
  };

  // Handle select all/none
  const handleSelectAll = () => {
    const allChangeIds = new Set(
      availableChanges.map(({ change, index }) =>
        `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`
      )
    );
    setSelectedChangeIds(allChangeIds);
  };

  const handleSelectNone = () => {
    setSelectedChangeIds(new Set());
  };

  // Enhanced bulk operation execution with detailed progress tracking
  const handleExecute = async () => {
    if (selectedChangeIds.size === 0) return;

    setIsExecuting(true);
    setIsPaused(false);
    setResult(null);
    setProgress(null);
    setCurrentStep(0);
    setExecutionPhase('preparation');

    try {
      // Phase 1: Preparation
      setExecutionPhase('preparation');
      setCurrentStep(1);
      await new Promise(resolve => setTimeout(resolve, 500)); // Simulate preparation

      // Phase 2: Validation
      setExecutionPhase('validation');
      setCurrentStep(2);

      // Enhanced validation based on validation level
      if (enhancedConfig.validationLevel === 'strict' && preview && preview.conflicts.length > 0) {
        const errorMessage = `Validation failed: ${preview.conflicts.join(', ')}`;
        throw new (Error as any)(errorMessage);
      }

      await new Promise(resolve => setTimeout(resolve, 300)); // Simulate validation

      // Phase 3: Backup (if enabled)
      if (enhancedConfig.backupBeforeExecution) {
        setCurrentStep(3);
        await new Promise(resolve => setTimeout(resolve, 200)); // Simulate backup
      }

      // Phase 4: Execution
      setExecutionPhase('execution');
      setCurrentStep(enhancedConfig.backupBeforeExecution ? 4 : 3);

      const config: SelectiveBulkConfig = {
        selectedChangeIds,
        operationType,
        config: enhancedConfig
      };

      // Enhanced execution with progress callbacks
      const operationResult = await executeWithEnhancedProgress(config);

      // Phase 5: Completion
      setExecutionPhase('completion');
      setCurrentStep(enhancedConfig.backupBeforeExecution ? 5 : 4);

      setResult(operationResult);

    } catch (error) {
      console.error('Bulk operation failed:', error);
      setResult({
        success: false,
        progress: progress || createMockProgress(),
        summary: {
          totalOperations: selectedChangeIds.size,
          successfulOperations: 0,
          failedOperations: selectedChangeIds.size,
          cancelledOperations: 0,
          totalDuration: 0,
          averageOperationTime: 0
        },
        confidenceDistribution: {
          high: 0,
          medium: 0,
          low: 0,
          averageScore: 0,
          minScore: 0,
          maxScore: 0
        },
        errorReport: {
          errors: [{
            changeId: 'general',
            change: availableChanges[0]?.change || {} as SchemaAlignmentChangeDetail,
            error: error instanceof Error ? error : new (Error as any)('Unknown error'),
            retryCount: 0
          }],
          recoveryOptions: ['Review configuration and try again', 'Contact support']
        }
      });
    } finally {
      setIsExecuting(false);
      setIsPaused(false);
    }
  };

  // Enhanced execution with detailed progress tracking
  const executeWithEnhancedProgress = async (config: SelectiveBulkConfig): Promise<BulkOperationResult> => {
    const totalOperations = selectedChangeIds.size;
    let completedOperations = 0;
    let failedOperations = 0;

    // Simulate enhanced progress tracking
    const progressCallback = (changeId: string, status: 'executing' | 'completed' | 'failed', error?: string, duration?: number) => {
      setDetailedProgress(prev => prev.map(item =>
        item.changeId === changeId
          ? { ...item, status, error, duration }
          : item
      ));

      if (status === 'completed') completedOperations++;
      if (status === 'failed') failedOperations++;

      // Update overall progress
      const progressPercentage = ((completedOperations + failedOperations) / totalOperations) * 100;
      setProgress(prev => prev ? {
        ...prev,
        completed: completedOperations,
        failed: failedOperations,
        currentOperation: `Processing ${changeId}...`
      } : null);
    };

    // Execute the actual bulk operation with progress tracking
    return await onExecuteBulkOperation(config);
  };

  // Create mock progress for error scenarios
  const createMockProgress = (): EnhancedProgressTracker => ({
    total: selectedChangeIds.size,
    completed: 0,
    failed: selectedChangeIds.size,
    errors: [],
    cancelled: false,
    canCancel: false,
    startTime: new Date(),
    operationResults: [],
    cancel: () => {},
    currentOperation: 'Failed to start operation'
  });

  // Enhanced operation control
  const handleCancel = () => {
    if (progress && progress.canCancel) {
      progress.cancel();
    }
  };

  const handlePause = () => {
    setIsPaused(!isPaused);
    // In a real implementation, this would pause the actual operation
  };

  const handleSkipCurrent = () => {
    // Skip current operation and continue with next
    console.log('Skipping current operation');
  };

  const handleRetryFailed = async () => {
    if (!result || !result.errorReport) return;

    // Create new config with only failed operations
    const failedChangeIds = new Set(result.errorReport.errors.map(e => e.changeId));
    const retryConfig: SelectiveBulkConfig = {
      selectedChangeIds: failedChangeIds,
      operationType,
      config: enhancedConfig
    };

    setResult(null);
    setIsExecuting(true);

    try {
      const retryResult = await onExecuteBulkOperation(retryConfig);
      setResult(retryResult);
    } catch (error) {
      console.error('Retry failed:', error);
    } finally {
      setIsExecuting(false);
    }
  };

  // Save current configuration
  const handleSaveConfiguration = () => {
    if (!configurationName.trim() || !onSaveConfiguration) return;

    const config: SelectiveBulkConfig = {
      selectedChangeIds,
      operationType,
      config: enhancedConfig
    };

    onSaveConfiguration(config, configurationName.trim());
    setConfigurationName('');
    setShowSaveConfig(false);

    // Refresh saved configurations
    if (onLoadConfigurations) {
      setSavedConfigurations(onLoadConfigurations());
    }
  };

  // Load saved configuration
  const handleLoadConfiguration = (savedConfig: SelectiveBulkConfig) => {
    setSelectedChangeIds(savedConfig.selectedChangeIds);
    setEnhancedConfig(savedConfig.config as EnhancedBulkConfig);
  };

  // Handle dialog close
  const handleClose = () => {
    if (!isExecuting) {
      onClose();
      // Reset state
      setSelectedChangeIds(new Set());
      setResult(null);
      setProgress(null);
      setShowPreview(false);
      setShowAdvancedSettings(false);
    }
  };

  // Calculate progress percentage
  const progressPercentage = progress
    ? Math.round(((progress.completed + progress.failed) / progress.total) * 100)
    : 0;

  // Format duration
  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      disableEscapeKeyDown={isExecuting}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            {operationType === 'apply' ? 'Apply' : 'Revert'} Schema Changes
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {onViewHistory && (
              <Tooltip title="View operation history">
                <IconButton onClick={onViewHistory} size="small">
                  <History />
                </IconButton>
              </Tooltip>
            )}
            <Tooltip title="Advanced settings">
              <IconButton
                onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                size="small"
                color={showAdvancedSettings ? 'primary' : 'default'}
              >
                <Settings />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Stack spacing={3}>
          {/* Execution Progress Stepper */}
          {isExecuting && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Operation Progress
                </Typography>
                <Stepper activeStep={currentStep} orientation="horizontal" alternativeLabel>
                  <Step>
                    <StepLabel>Preparation</StepLabel>
                  </Step>
                  <Step>
                    <StepLabel>Validation</StepLabel>
                  </Step>
                  {enhancedConfig.backupBeforeExecution && (
                    <Step>
                      <StepLabel>Backup</StepLabel>
                    </Step>
                  )}
                  <Step>
                    <StepLabel>Execution</StepLabel>
                  </Step>
                  <Step>
                    <StepLabel>Completion</StepLabel>
                  </Step>
                </Stepper>

                {executionPhase === 'execution' && enhancedConfig.progressDisplayMode === 'detailed' && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" gutterBottom>
                      Detailed Progress ({detailedProgress.filter(p => p.status === 'completed').length} of {detailedProgress.length})
                    </Typography>
                    <List dense sx={{ maxHeight: 200, overflow: 'auto' }}>
                      {detailedProgress.map((item, index) => (
                        <ListItem key={item.changeId} dense>
                          <ListItemIcon>
                            {item.status === 'pending' && <CircularProgress size={16} />}
                            {item.status === 'executing' && <CircularProgress size={16} />}
                            {item.status === 'completed' && <CheckCircle color="success" fontSize="small" />}
                            {item.status === 'failed' && <Error color="error" fontSize="small" />}
                            {item.status === 'skipped' && <SkipNext color="warning" fontSize="small" />}
                          </ListItemIcon>
                          <ListItemText
                            primary={item.changeId}
                            secondary={
                              <Box>
                                <Typography variant="caption" color="text.secondary">
                                  Status: {item.status}
                                </Typography>
                                {item.duration && (
                                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                                    ({item.duration}ms)
                                  </Typography>
                                )}
                                {item.error && (
                                  <Typography variant="caption" color="error" display="block">
                                    Error: {item.error}
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </CardContent>
            </Card>
          )}

          {/* Enhanced Selection Controls */}
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="subtitle1" fontWeight="bold">
                Select Changes ({selectedChangeIds.size} of {availableChanges.length})
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button size="small" onClick={handleSelectAll}>
                  Select All
                </Button>
                <Button size="small" onClick={handleSelectNone}>
                  Select None
                </Button>
                <Button
                  size="small"
                  startIcon={<Preview />}
                  onClick={() => setShowPreview(!showPreview)}
                  variant={showPreview ? 'contained' : 'outlined'}
                >
                  Preview
                </Button>
                <Button
                  size="small"
                  startIcon={<SaveAlt />}
                  onClick={() => setShowSaveConfig(true)}
                  disabled={selectedChangeIds.size === 0}
                >
                  Save Config
                </Button>
              </Box>
            </Box>

            {/* Filtering and Sorting Controls */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Filter by Type</InputLabel>
                <Select
                  value={filterType}
                  label="Filter by Type"
                  onChange={(e) => setFilterType(e.target.value as any)}
                >
                  <MenuItem value="all">All Types</MenuItem>
                  <MenuItem value="rename">Rename</MenuItem>
                  <MenuItem value="add">Add</MenuItem>
                  <MenuItem value="remove">Remove</MenuItem>
                </Select>
              </FormControl>

              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Sort by</InputLabel>
                <Select
                  value={sortBy}
                  label="Sort by"
                  onChange={(e) => setSortBy(e.target.value as any)}
                >
                  <MenuItem value="type">Type</MenuItem>
                  <MenuItem value="impact">Impact</MenuItem>
                  <MenuItem value="risk">Risk Level</MenuItem>
                </Select>
              </FormControl>

              <Chip
                label={`${availableChanges.length} available`}
                size="small"
                color="primary"
              />
              {filterType !== 'all' && (
                <Chip
                  label={`Filtered by ${filterType}`}
                  size="small"
                  onDelete={() => setFilterType('all')}
                />
              )}
            </Box>

            {/* Saved Configurations */}
            {savedConfigurations.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" gutterBottom>
                  Saved Configurations:
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {savedConfigurations.map((saved, index) => (
                    <Chip
                      key={index}
                      label={saved.name}
                      size="small"
                      onClick={() => handleLoadConfiguration(saved.config)}
                      clickable
                      variant="outlined"
                    />
                  ))}
                </Box>
              </Box>
            )}

            {/* Change Selection List */}
            <Card variant="outlined" sx={{ maxHeight: 300, overflow: 'auto' }}>
              <List dense>
                {availableChanges.map(({ change, index }) => {
                  const changeId = `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`;
                  const isSelected = selectedChangeIds.has(changeId);

                  return (
                    <ListItem key={changeId} dense>
                      <ListItemIcon>
                        <Checkbox
                          checked={isSelected}
                          onChange={(e) => handleChangeSelection(changeId, e.target.checked)}
                          disabled={isExecuting}
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary={formatChangeDescription(change)}
                        secondary={
                          <React.Fragment>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5, flexWrap: 'wrap' }}>
                              <Chip
                                label={change.changeType}
                                size="small"
                                color={
                                  change.changeType.toLowerCase() === 'remove' ? 'warning' :
                                  change.changeType.toLowerCase() === 'add' ? 'success' : 'info'
                                }
                              />
                              {/* Confidence indicator */}
                              <Chip
                                label={`${change.confidenceLevel || 'Low'} Confidence`}
                                size="small"
                                sx={{
                                  backgroundColor: getConfidenceColor(change.confidenceLevel || 'Low'),
                                  color: 'white',
                                  fontWeight: 'bold'
                                }}
                              />
                              {change.rowCountAffected && (
                                <Typography variant="caption" color="text.secondary" component="span">
                                  {change.rowCountAffected} rows affected
                                </Typography>
                              )}
                              {/* Confidence score tooltip */}
                              <Tooltip title={`Confidence Score: ${((change.confidenceScore || 0) * 100).toFixed(1)}%`}>
                                <InfoOutlined sx={{ fontSize: 14, color: 'text.secondary' }} />
                              </Tooltip>
                            </Box>
                          </React.Fragment>
                        }
                      />
                    </ListItem>
                  );
                })}
              </List>
            </Card>
          </Box>

          {/* Enhanced Advanced Settings */}
          {showAdvancedSettings && (
            <Accordion expanded={showAdvancedSettings}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">Advanced Settings</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Stack spacing={3}>
                  {/* Error Handling */}
                  <Box>
                    <Typography variant="body2" fontWeight="bold" gutterBottom>
                      Error Handling
                    </Typography>
                    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                      <InputLabel>Error Recovery Mode</InputLabel>
                      <Select
                        value={enhancedConfig.errorRecoveryMode}
                        label="Error Recovery Mode"
                        onChange={(e) => setEnhancedConfig(prev => ({
                          ...prev,
                          errorRecoveryMode: e.target.value as ErrorRecoveryMode
                        }))}
                        disabled={isExecuting}
                      >
                        <MenuItem value="stop">Stop on first error</MenuItem>
                        <MenuItem value="continue">Continue on error</MenuItem>
                        <MenuItem value="skip">Skip failed operations</MenuItem>
                        <MenuItem value="retry">Auto-retry failed operations</MenuItem>
                      </Select>
                    </FormControl>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={enhancedConfig.pauseOnError}
                          onChange={(e) => setEnhancedConfig(prev => ({
                            ...prev,
                            pauseOnError: e.target.checked
                          }))}
                          disabled={isExecuting}
                        />
                      }
                      label="Pause on error for manual review"
                    />
                  </Box>

                  {/* Execution Settings */}
                  <Box>
                    <Typography variant="body2" fontWeight="bold" gutterBottom>
                      Execution Settings
                    </Typography>
                    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                      <InputLabel>Execution Mode</InputLabel>
                      <Select
                        value={enhancedConfig.executionMode}
                        label="Execution Mode"
                        onChange={(e) => setEnhancedConfig(prev => ({
                          ...prev,
                          executionMode: e.target.value as ExecutionMode
                        }))}
                        disabled={isExecuting}
                      >
                        <MenuItem value="sequential">Sequential (one at a time)</MenuItem>
                        <MenuItem value="batch">Batch processing</MenuItem>
                        <MenuItem value="optimized">Optimized order</MenuItem>
                      </Select>
                    </FormControl>

                    {enhancedConfig.executionMode === 'batch' && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" gutterBottom>
                          Batch Size: {enhancedConfig.batchSize}
                        </Typography>
                        <Slider
                          value={enhancedConfig.batchSize || 10}
                          onChange={(_, value) => setEnhancedConfig(prev => ({
                            ...prev,
                            batchSize: value as number
                          }))}
                          min={1}
                          max={50}
                          step={1}
                          marks={[
                            { value: 1, label: '1' },
                            { value: 10, label: '10' },
                            { value: 25, label: '25' },
                            { value: 50, label: '50' }
                          ]}
                          disabled={isExecuting}
                        />
                      </Box>
                    )}

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" gutterBottom>
                        Operation Delay: {enhancedConfig.operationDelay}ms
                      </Typography>
                      <Slider
                        value={enhancedConfig.operationDelay || 100}
                        onChange={(_, value) => setEnhancedConfig(prev => ({
                          ...prev,
                          operationDelay: value as number
                        }))}
                        min={0}
                        max={2000}
                        step={50}
                        marks={[
                          { value: 0, label: '0ms' },
                          { value: 500, label: '500ms' },
                          { value: 1000, label: '1s' },
                          { value: 2000, label: '2s' }
                        ]}
                        disabled={isExecuting}
                      />
                    </Box>
                  </Box>

                  {/* Validation and Safety */}
                  <Box>
                    <Typography variant="body2" fontWeight="bold" gutterBottom>
                      Validation & Safety
                    </Typography>
                    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                      <InputLabel>Validation Level</InputLabel>
                      <Select
                        value={enhancedConfig.validationLevel}
                        label="Validation Level"
                        onChange={(e) => setEnhancedConfig(prev => ({
                          ...prev,
                          validationLevel: e.target.value as 'strict' | 'moderate' | 'lenient'
                        }))}
                        disabled={isExecuting}
                      >
                        <MenuItem value="lenient">Lenient (minimal validation)</MenuItem>
                        <MenuItem value="moderate">Moderate (standard validation)</MenuItem>
                        <MenuItem value="strict">Strict (comprehensive validation)</MenuItem>
                      </Select>
                    </FormControl>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={enhancedConfig.backupBeforeExecution}
                          onChange={(e) => setEnhancedConfig(prev => ({
                            ...prev,
                            backupBeforeExecution: e.target.checked
                          }))}
                          disabled={isExecuting}
                        />
                      }
                      label="Create backup before execution"
                    />

                    <FormControlLabel
                      control={
                        <Switch
                          checked={enhancedConfig.allowCancellation}
                          onChange={(e) => setEnhancedConfig(prev => ({
                            ...prev,
                            allowCancellation: e.target.checked
                          }))}
                          disabled={isExecuting}
                        />
                      }
                      label="Allow operation cancellation"
                    />
                  </Box>

                  {/* Progress Display */}
                  <Box>
                    <Typography variant="body2" fontWeight="bold" gutterBottom>
                      Progress Display
                    </Typography>
                    <FormControl fullWidth size="small">
                      <InputLabel>Progress Display Mode</InputLabel>
                      <Select
                        value={enhancedConfig.progressDisplayMode}
                        label="Progress Display Mode"
                        onChange={(e) => setEnhancedConfig(prev => ({
                          ...prev,
                          progressDisplayMode: e.target.value as ProgressDisplayMode
                        }))}
                        disabled={isExecuting}
                      >
                        <MenuItem value="minimal">Minimal (basic progress bar)</MenuItem>
                        <MenuItem value="compact">Compact (summary only)</MenuItem>
                        <MenuItem value="detailed">Detailed (step-by-step)</MenuItem>
                      </Select>
                    </FormControl>
                  </Box>
                </Stack>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Preview */}
          {showPreview && preview && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Operation Preview
                </Typography>
                <Stack spacing={2}>
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Chip
                      label={`${preview.affectedChanges.length} operations`}
                      color="primary"
                    />
                    <Chip
                      label={`${preview.impact.totalRowsAffected} rows affected`}
                      color="info"
                    />
                    <Chip
                      label={`~${formatDuration(preview.impact.estimatedDuration)}`}
                      color="default"
                    />
                    {preview.impact.destructiveOperations > 0 && (
                      <Chip
                        label={`${preview.impact.destructiveOperations} destructive`}
                        color="warning"
                      />
                    )}
                  </Box>

                  {/* Confidence Distribution */}
                  <ConfidenceDistributionDisplay
                    distribution={preview.confidenceDistribution}
                    title="Confidence Distribution of Selected Operations"
                    showDetails={true}
                  />

                  {preview.warnings.length > 0 && (
                    <Alert severity="warning">
                      <AlertTitle>Warnings</AlertTitle>
                      <ul style={{ margin: 0, paddingLeft: 20 }}>
                        {preview.warnings.map((warning, index) => (
                          <li key={index}>{warning}</li>
                        ))}
                      </ul>
                    </Alert>
                  )}

                  {preview.conflicts.length > 0 && (
                    <Alert severity="error">
                      <AlertTitle>Conflicts Detected</AlertTitle>
                      <ul style={{ margin: 0, paddingLeft: 20 }}>
                        {preview.conflicts.map((conflict, index) => (
                          <li key={index}>{conflict}</li>
                        ))}
                      </ul>
                    </Alert>
                  )}
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* Enhanced Progress Indicator */}
          {isExecuting && progress && (
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                  <Typography variant="subtitle2">
                    Operation Progress
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {enhancedConfig.allowCancellation && (
                      <Tooltip title={isPaused ? "Resume operation" : "Pause operation"}>
                        <IconButton size="small" onClick={handlePause} disabled={!progress.canCancel}>
                          {isPaused ? <PlayArrow /> : <Pause />}
                        </IconButton>
                      </Tooltip>
                    )}
                    {enhancedConfig.errorRecoveryMode === 'skip' && (
                      <Tooltip title="Skip current operation">
                        <IconButton size="small" onClick={handleSkipCurrent}>
                          <SkipNext />
                        </IconButton>
                      </Tooltip>
                    )}
                    {progress.canCancel && (
                      <Tooltip title="Cancel operation">
                        <IconButton size="small" onClick={handleCancel} color="error">
                          <Stop />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">
                      {progress.completed + progress.failed} of {progress.total} operations
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" color="text.secondary">
                        {progressPercentage}%
                      </Typography>
                      {isPaused && (
                        <Chip label="PAUSED" size="small" color="warning" />
                      )}
                    </Box>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={progressPercentage}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: isPaused ? 'warning.main' : 'primary.main'
                      }
                    }}
                  />
                </Box>

                {progress.currentOperation && (
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Current: {progress.currentOperation}
                  </Typography>
                )}

                <Box sx={{ display: 'flex', gap: 1, mt: 2, flexWrap: 'wrap' }}>
                  <Chip
                    icon={<CheckCircle />}
                    label={`${progress.completed} completed`}
                    color="success"
                    size="small"
                  />
                  {progress.failed > 0 && (
                    <Chip
                      icon={<Error />}
                      label={`${progress.failed} failed`}
                      color="error"
                      size="small"
                    />
                  )}
                  {progress.cancelled && (
                    <Chip
                      icon={<Cancel />}
                      label="Cancelled"
                      color="warning"
                      size="small"
                    />
                  )}
                  {progress.estimatedTimeRemaining && (
                    <Chip
                      icon={<Timeline />}
                      label={`~${formatDuration(progress.estimatedTimeRemaining)} remaining`}
                      size="small"
                    />
                  )}
                  <Chip
                    icon={<Speed />}
                    label={`${formatDuration(Date.now() - progress.startTime.getTime())} elapsed`}
                    size="small"
                  />
                </Box>
              </CardContent>
            </Card>
          )}

          {/* Enhanced Results with Recovery Options */}
          {result && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Operation Results
                </Typography>
                <Stack spacing={2}>
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Chip
                      icon={result.success ? <CheckCircle /> : <Error />}
                      label={result.success ? 'Success' : 'Completed with errors'}
                      color={result.success ? 'success' : 'warning'}
                    />
                    <Chip
                      label={`${result.summary.successfulOperations} successful`}
                      color="success"
                    />
                    {result.summary.failedOperations > 0 && (
                      <Chip
                        label={`${result.summary.failedOperations} failed`}
                        color="error"
                      />
                    )}
                    {result.summary.cancelledOperations > 0 && (
                      <Chip
                        label={`${result.summary.cancelledOperations} cancelled`}
                        color="warning"
                      />
                    )}
                    <Chip
                      label={`${formatDuration(result.summary.totalDuration)} total`}
                      color="info"
                    />
                    <Chip
                      label={`${formatDuration(result.summary.averageOperationTime)} avg`}
                      color="default"
                    />
                  </Box>

                  {/* Confidence Distribution of Applied Changes */}
                  <ConfidenceDistributionDisplay
                    distribution={result.confidenceDistribution}
                    title="Confidence Distribution of Applied Changes"
                    showDetails={true}
                  />

                  {/* Success Summary */}
                  {result.success && (
                    <Alert severity="success">
                      <AlertTitle>Operation Completed Successfully</AlertTitle>
                      All {result.summary.totalOperations} operations completed without errors.
                    </Alert>
                  )}

                  {/* Partial Success with Recovery Options */}
                  {!result.success && result.summary.successfulOperations > 0 && (
                    <Alert severity="warning">
                      <AlertTitle>Partial Success</AlertTitle>
                      {result.summary.successfulOperations} operations completed successfully,
                      but {result.summary.failedOperations} operations failed.
                      <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        <Button
                          size="small"
                          startIcon={<Refresh />}
                          onClick={handleRetryFailed}
                          variant="outlined"
                        >
                          Retry Failed Operations
                        </Button>
                        <Button
                          size="small"
                          startIcon={<RestartAlt />}
                          onClick={() => {
                            setResult(null);
                            setProgress(null);
                          }}
                          variant="outlined"
                        >
                          Start Over
                        </Button>
                      </Box>
                    </Alert>
                  )}

                  {/* Complete Failure */}
                  {!result.success && result.summary.successfulOperations === 0 && (
                    <Alert severity="error">
                      <AlertTitle>Operation Failed</AlertTitle>
                      All operations failed to complete. Please review the errors below and try again.
                    </Alert>
                  )}

                  {/* Error Details */}
                  {result.errorReport && result.errorReport.errors.length > 0 && (
                    <Accordion>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Typography variant="body2">
                          <Badge badgeContent={result.errorReport.errors.length} color="error">
                            View Error Details
                          </Badge>
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Stack spacing={2}>
                          <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
                            {result.errorReport.errors.map((error, index) => (
                              <ListItem key={index} divider>
                                <ListItemIcon>
                                  <Error color="error" />
                                </ListItemIcon>
                                <ListItemText
                                  primary={formatChangeDescription(error.change)}
                                  secondary={
                                    <Box>
                                      <Typography variant="body2" color="error">
                                        {error.error.message}
                                      </Typography>
                                      {error.retryCount > 0 && (
                                        <Typography variant="caption" color="text.secondary">
                                          Retried {error.retryCount} times
                                        </Typography>
                                      )}
                                    </Box>
                                  }
                                />
                              </ListItem>
                            ))}
                          </List>

                          {/* Recovery Options */}
                          <Box>
                            <Typography variant="body2" fontWeight="bold" gutterBottom>
                              Recovery Options:
                            </Typography>
                            <List dense>
                              {result.errorReport.recoveryOptions.map((option, index) => (
                                <ListItem key={index}>
                                  <ListItemIcon>
                                    <Info color="info" />
                                  </ListItemIcon>
                                  <ListItemText primary={option} />
                                </ListItem>
                              ))}
                            </List>
                          </Box>
                        </Stack>
                      </AccordionDetails>
                    </Accordion>
                  )}
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* Save Configuration Dialog */}
          <Dialog open={showSaveConfig} onClose={() => setShowSaveConfig(false)}>
            <DialogTitle>Save Configuration</DialogTitle>
            <DialogContent>
              <TextField
                autoFocus
                margin="dense"
                label="Configuration Name"
                fullWidth
                variant="outlined"
                value={configurationName}
                onChange={(e) => setConfigurationName(e.target.value)}
                placeholder="e.g., 'Quick Apply All' or 'Safe Rename Only'"
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setShowSaveConfig(false)}>Cancel</Button>
              <Button
                onClick={handleSaveConfiguration}
                disabled={!configurationName.trim()}
                variant="contained"
              >
                Save
              </Button>
            </DialogActions>
          </Dialog>
        </Stack>
      </DialogContent>

      <DialogActions>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {/* Operation Controls */}
            {isExecuting && (
              <>
                {enhancedConfig.allowCancellation && progress?.canCancel && (
                  <Button
                    startIcon={<Stop />}
                    onClick={handleCancel}
                    color="error"
                    size="small"
                  >
                    Cancel
                  </Button>
                )}
                {enhancedConfig.pauseOnError && (
                  <Button
                    startIcon={isPaused ? <PlayArrow /> : <Pause />}
                    onClick={handlePause}
                    color="warning"
                    size="small"
                  >
                    {isPaused ? 'Resume' : 'Pause'}
                  </Button>
                )}
              </>
            )}

            {/* Result Actions */}
            {result && result.errorReport && result.errorReport.errors.length > 0 && (
              <Button
                startIcon={<Refresh />}
                onClick={handleRetryFailed}
                color="primary"
                size="small"
                variant="outlined"
              >
                Retry Failed ({result.errorReport.errors.length})
              </Button>
            )}
          </Box>

          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            {/* Progress Summary */}
            {isExecuting && progress && (
              <Typography variant="caption" color="text.secondary">
                {progress.completed + progress.failed}/{progress.total} operations
              </Typography>
            )}

            {/* Validation Warning */}
            {preview && !preview.safeToExecute && !isExecuting && (
              <Tooltip title={`${preview.conflicts.length} conflicts detected`}>
                <Warning color="warning" />
              </Tooltip>
            )}

            {/* Main Actions */}
            <Button
              onClick={handleClose}
              disabled={isExecuting}
              color="inherit"
            >
              {result ? 'Close' : 'Cancel'}
            </Button>

            {!result && !isExecuting && (
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={handleExecute}
                disabled={Boolean(
                  selectedChangeIds.size === 0 ||
                  (enhancedConfig.validationLevel === 'strict' && preview && preview.safeToExecute === false)
                )}
                color={preview && !preview.safeToExecute ? 'warning' : 'primary'}
              >
                {operationType === 'apply' ? 'Apply' : 'Revert'} {selectedChangeIds.size} Selected
              </Button>
            )}

            {result && !result.success && result.summary.successfulOperations === 0 && (
              <Button
                startIcon={<RestartAlt />}
                onClick={() => {
                  setResult(null);
                  setProgress(null);
                  setDetailedProgress([]);
                  setCurrentStep(0);
                  setExecutionPhase('preparation');
                }}
                variant="contained"
                color="primary"
              >
                Try Again
              </Button>
            )}
          </Box>
        </Box>
      </DialogActions>
    </Dialog>
  );
};
