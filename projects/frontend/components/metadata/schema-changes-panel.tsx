/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Chip,
  Stack,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Divider
} from '@mui/material';
import {
  Transform,
  PlaylistAddCheck,
  Settings,
  History,
  Undo,
  DriveFileRenameOutline,
  Add,
  Remove
} from '@mui/icons-material';
import { SchemaAlignmentChangeDetail } from '../../lib/types';
import {
  generateChangeId,
  generateTransformationPreview,
  TransformationCallbacks,
  TransformationState
} from '../../lib/schema-transformation-utils';
import {
  generateConfirmationContent,
  generateDestructiveWarning,
  resetConfirmationConfig,
  ConfirmationDialogConfig
} from '../../lib/confirmation-dialog-utils';
import {
  createTransformationManager,
  createUndoRedoManager,
  createSequencingManager,
  TransformationManager,
  UndoRedoManager,
  SequencingManager,
  BulkOperationResult,
  SelectiveBulkConfig,
  BulkOperationConfig
} from '../../lib/transformation-operations';
import { BulkOperationsDialog } from './bulk-operations-dialog';
import { BulkOperationHistory, BulkOperationHistoryEntry } from './bulk-operation-history';
import { SchemaChangeCard } from './schema-change-card';

interface SchemaChangesPanelProps {
  /** Array of schema alignment changes to display */
  changes: SchemaAlignmentChangeDetail[];
  /** Current column names from live data state */
  currentColumns?: string[];
  /** Current data array for bulk operations */
  currentData?: string[][];
  /** Callback when bulk operations complete with final data */
  onFinalDataUpdate?: (finalData: string[][]) => void;
  /** Callback when changes are applied or reverted to update parent state */
  onAppliedChangesUpdate?: (changeId: string, isApplied: boolean) => void;
  /** Callback when bulk schema changes are applied for UI change tracking */
  onBulkSchemaChangesApplied?: (appliedChanges: Array<{ change: SchemaAlignmentChangeDetail; index: number; columnIndex?: number }>) => void;
  // currentView removed - no longer using toggle functionality
  /** Callback when user applies a column rename */
  onApplyColumnRename?: (originalColumn: string, newColumn: string) => void;
  /** Callback when user applies a column addition */
  onApplyColumnAddition?: (newColumn: string) => void;
  /** Callback when user applies a column removal */
  onApplyColumnRemoval?: (columnName: string) => void;
  /** Callback when user accepts a change (legacy support) */
  onAcceptChange: (changeId: string) => void;
  /** Callback when user reverts a change (legacy support) */
  onRevertChange: (changeId: string) => void;
  /** Set of applied change IDs from parent component */
  appliedChangeIds?: Set<string>;
  /** Callback to get change ID for a specific change */
  getChangeId?: (change: SchemaAlignmentChangeDetail, index: number) => string;
}

/**
 * SchemaChangesPanel component displays schema alignment changes with options
 * for accepting or reverting individual changes.
 *
 * This component shows the transformations that were automatically applied
 * during schema alignment processing and allows users to manage them.
 */
export const SchemaChangesPanel: React.FC<SchemaChangesPanelProps> = ({
  changes,
  currentColumns: propCurrentColumns,
  currentData: propCurrentData,
  onFinalDataUpdate,
  onAppliedChangesUpdate,
  onBulkSchemaChangesApplied,
  onApplyColumnRename,
  onApplyColumnAddition,
  onApplyColumnRemoval,
  onAcceptChange,
  onRevertChange,
  appliedChangeIds,
  getChangeId
}) => {
  // State for confirmation dialogs using shared type
  const [confirmationDialog, setConfirmationDialog] = useState<ConfirmationDialogConfig>(
    resetConfirmationConfig()
  );

  // State for enhanced bulk operations
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [bulkOperationType, setBulkOperationType] = useState<'apply' | 'revert'>('apply');
  const [showHistory, setShowHistory] = useState(false);
  const [operationHistory, setOperationHistory] = useState<BulkOperationHistoryEntry[]>([]);

  // Use applied changes from parent if provided, otherwise maintain local state for backward compatibility
  const [localAppliedChanges, setLocalAppliedChanges] = useState<Set<string>>(new Set());

  // Create shared transformation state
  const transformationState: TransformationState = {
    appliedChangeIds: appliedChangeIds || localAppliedChanges,
    markAsApplied: (changeId: string) => {
      console.log('🔧 SchemaChangesPanel: markAsApplied called for:', changeId);

      if (!appliedChangeIds) {
        // Update local state if no parent state provided
        setLocalAppliedChanges(prev => new Set([...prev, changeId]));
      }

      // Always notify parent when changes are applied (for both local and parent-managed state)
      if (onAppliedChangesUpdate) {
        console.log('🔧 SchemaChangesPanel: Notifying parent of applied change:', changeId);
        onAppliedChangesUpdate(changeId, true);
      }
    },
    markAsReverted: (changeId: string) => {
      console.log('🔄 SchemaChangesPanel: markAsReverted called for:', changeId);

      if (!appliedChangeIds) {
        // Update local state if no parent state provided
        setLocalAppliedChanges(prev => {
          const newSet = new Set(prev);
          newSet.delete(changeId);
          return newSet;
        });
      }

      // Always notify parent when changes are reverted (for both local and parent-managed state)
      if (onAppliedChangesUpdate) {
        console.log('🔄 SchemaChangesPanel: Notifying parent of reverted change:', changeId);
        onAppliedChangesUpdate(changeId, false);
      }
    },
    isApplied: (changeId: string) => {
      return (appliedChangeIds || localAppliedChanges).has(changeId);
    }
  };

  // Create shared transformation callbacks
  const transformationCallbacks: TransformationCallbacks = {
    onApplyColumnRename,
    onApplyColumnAddition,
    onApplyColumnRemoval,
    onRevertChange
  };

  // Use live current columns from props if available, otherwise derive from changes for backward compatibility
  const currentColumns = React.useMemo(() => {
    if (propCurrentColumns && propCurrentColumns.length > 0) {
      // Use live columns from parent component (preferred for accurate validation)
      return propCurrentColumns;
    }

    // Fallback: Extract unique column names from changes for validation (backward compatibility)
    const columns = new Set<string>();
    changes.forEach(change => {
      if (change.originalColumn) columns.add(change.originalColumn);
      if (change.newColumn && change.changeType.toLowerCase() !== 'rename') {
        columns.add(change.newColumn);
      }
    });
    return Array.from(columns);
  }, [propCurrentColumns, changes]);

  // Create current data array for bulk operations
  const currentData = React.useMemo(() => {
    if (propCurrentData && propCurrentData.length > 0) {
      // Use live data from parent component (preferred for bulk operations)
      return propCurrentData;
    }

    // Fallback: Create minimal data structure with just headers for backward compatibility
    if (currentColumns.length > 0) {
      return [currentColumns];
    }

    return [[]];
  }, [propCurrentData, currentColumns]);

  // Create shared managers
  const transformationManager: TransformationManager = React.useMemo(() =>
    createTransformationManager(
      currentData,
      transformationCallbacks,
      transformationState,
      undefined, // onProgress - not used in SchemaChangesPanel
      onFinalDataUpdate,
      onBulkSchemaChangesApplied
    ), [currentData, transformationCallbacks, transformationState, onFinalDataUpdate, onBulkSchemaChangesApplied]
  );

  const undoRedoManager: UndoRedoManager = React.useMemo(() =>
    createUndoRedoManager(transformationManager), [transformationManager]
  );

  const sequencingManager: SequencingManager = React.useMemo(() =>
    createSequencingManager(), []
  );

  // Helper to get change ID for a specific change
  const getChangeIdForChange = (change: SchemaAlignmentChangeDetail, index: number): string => {
    if (getChangeId) {
      return getChangeId(change, index);
    }
    // Use shared utility for consistent ID generation
    return generateChangeId(change, index);
  };

  // Helper to check if a change is applied
  const isChangeApplied = (change: SchemaAlignmentChangeDetail, index: number): boolean => {
    const changeId = getChangeIdForChange(change, index);
    if (appliedChangeIds) {
      return appliedChangeIds.has(changeId);
    }
    return localAppliedChanges.has(changeId);
  };


  /**
   * Get the appropriate icon for a change type
   */
  const getChangeIcon = (changeType: string) => {
    switch (changeType.toLowerCase()) {
      case 'rename':
        return <DriveFileRenameOutline color="info" />;
      case 'add':
        return <Add color="success" />;
      case 'remove':
        return <Remove color="warning" />;
      default:
        return <Transform color="action" />;
    }
  };

  /**
   * Get the appropriate color for a change type
   */
  const getChangeColor = (changeType: string): 'info' | 'success' | 'warning' | 'default' => {
    switch (changeType.toLowerCase()) {
      case 'rename':
        return 'info';
      case 'add':
        return 'success';
      case 'remove':
        return 'warning';
      default:
        return 'default';
    }
  };

  /**
   * Get a human-readable label for the change type
   */
  const getChangeTypeLabel = (changeType: string): string => {
    switch (changeType.toLowerCase()) {
      case 'rename':
        return 'Rename';
      case 'add':
        return 'Add';
      case 'remove':
        return 'Remove';
      default:
        return changeType;
    }
  };

  /**
   * Get confidence color consistent with error cards
   */
  const getConfidenceColor = (level: string): string => {
    switch (level) {
      case 'High': return '#4caf50';  // Green
      case 'Medium': return '#ff9800'; // Orange
      case 'Low': return '#f44336';   // Red
      default: return '#757575';      // Gray
    }
  };

  /**
   * Get confidence level display text
   */
  const getConfidenceLevel = (change: SchemaAlignmentChangeDetail): string => {
    // First check if confidenceLevel is directly set
    const level = change.confidenceLevel;
    if (level && ['High', 'Medium', 'Low'].includes(level)) {
      return level;
    }

    // Try to extract confidence from structured reason string
    const parsedReason = parseEnhancedReason(change.reason);
    if (parsedReason?.confidence && ['High', 'Medium', 'Low'].includes(parsedReason.confidence)) {
      return parsedReason.confidence;
    }

    // Map confidence score to level if confidenceLevel is not set
    const score = change.confidenceScore || 0;
    if (score >= 0.8) return 'High';
    if (score >= 0.5) return 'Medium';
    if (score > 0) return 'Low';
    return 'Unknown';
  };

  /**
   * Get confidence tooltip text with reasoning
   */
  const getConfidenceTooltip = (change: SchemaAlignmentChangeDetail): string => {
    const level = getConfidenceLevel(change);

    // Extract only the reasoning part from structured reason string
    const parsedReason = parseEnhancedReason(change.reason);
    const reasoning = parsedReason?.reasoning || change.reason || 'No reasoning provided';

    // Show percentage only if we have a meaningful confidence score
    const score = change.confidenceScore;
    if (score !== undefined && score !== null && score > 0) {
      const percentage = (score * 100).toFixed(2);
      return `Reasoning: ${reasoning}`;
    } else {
      // If no numeric score, just show the confidence level
      return `Reasoning: ${reasoning}`;
    }
  };

  /**
   * Parse enhanced reasoning to extract structured information
   */
  const parseEnhancedReason = (reason: string | undefined) => {
    if (!reason) return null;

    // Try to parse Target/Match/Confidence/Reasoning format
    const targetMatch = reason.match(/Target:\s*([^|]+)/);
    const matchMatch = reason.match(/Match:\s*([^|]+)/);
    const confidenceMatch = reason.match(/Confidence:\s*([^|]+)/);
    const reasoningMatch = reason.match(/Reasoning:\s*(.+)$/);

    if (targetMatch || matchMatch || confidenceMatch || reasoningMatch) {
      return {
        target: targetMatch?.[1]?.trim(),
        match: matchMatch?.[1]?.trim(),
        confidence: confidenceMatch?.[1]?.trim(),
        reasoning: reasoningMatch?.[1]?.trim()
      };
    }

    return null;
  };

  // Legacy support for accept/revert operations
  const revertableChanges = changes;
  const acceptableChanges = changes;

  /**
   * Handle manual application of individual schema changes using shared utilities
   */
  const handleApplyChange = async (change: SchemaAlignmentChangeDetail, index: number) => {
    console.log('🔧 SchemaChangesPanel: Applying individual change:', { change, index });

    // Check if confirmation is needed using shared utility
    const confirmationConfig = transformationManager.checkConfirmationNeeded('remove', [change]);

    if (confirmationConfig && change.changeType.toLowerCase() === 'remove') {
      // Show confirmation dialog for potentially destructive changes
      setConfirmationDialog({ ...confirmationConfig, change, changeIndex: index });
    } else {
      // Apply change directly using shared transformation manager
      await applyChangeDirectly(change, index);
    }
  };

  /**
   * Apply change directly using shared transformation manager
   */
  const applyChangeDirectly = async (change: SchemaAlignmentChangeDetail, index: number) => {
    console.log('🔧 SchemaChangesPanel: Applying change directly using shared utilities:', {
      change: {
        type: change.changeType,
        originalColumn: change.originalColumn,
        newColumn: change.newColumn,
        reason: change.reason
      },
      index,
      availableCallbacks: {
        onApplyColumnRename: !!onApplyColumnRename,
        onApplyColumnAddition: !!onApplyColumnAddition,
        onApplyColumnRemoval: !!onApplyColumnRemoval
      }
    });

    try {
      // Validate that we have the necessary callbacks
      const changeType = change.changeType.toLowerCase();
      if (changeType === 'rename' && !onApplyColumnRename) {
        throw new Error('onApplyColumnRename callback is required for rename operations');
      }
      if (changeType === 'add' && !onApplyColumnAddition) {
        throw new Error('onApplyColumnAddition callback is required for add operations');
      }
      if (changeType === 'remove' && !onApplyColumnRemoval) {
        throw new Error('onApplyColumnRemoval callback is required for remove operations');
      }

      const result = await transformationManager.applyChange(change, index);

      if (result.success) {
        console.log('✅ SchemaChangesPanel: Change applied successfully using shared utilities');

        // Record operation for undo/redo
        (undoRedoManager as any).recordOperation?.('apply', generateChangeId(change, index), change, index);
      } else {
        console.error('❌ SchemaChangesPanel: Failed to apply change:', result.error);
        throw result.error || new Error('Unknown error applying change');
      }
    } catch (error) {
      console.error('❌ SchemaChangesPanel: Error applying change:', error, {
        changeType: change.changeType,
        originalColumn: change.originalColumn,
        newColumn: change.newColumn
      });
      throw error;
    }
  };

  /**
   * Handle reverting applied changes using shared utilities
   */
  const handleRevertChange = (change: SchemaAlignmentChangeDetail, index: number) => {
    const changeId = getChangeIdForChange(change, index);
    console.log('🔄 SchemaChangesPanel: Reverting change using shared utilities:', {
      change: {
        type: change.changeType,
        originalColumn: change.originalColumn,
        newColumn: change.newColumn
      },
      index,
      changeId,
      availableCallbacks: {
        onRevertChange: !!onRevertChange
      }
    });

    try {
      // Validate that we have the necessary callback
      if (!onRevertChange) {
        throw new Error('onRevertChange callback is required for revert operations');
      }

      const result = transformationManager.revertChange(changeId);

      if (result.success) {
        console.log('✅ SchemaChangesPanel: Change reverted successfully using shared utilities');

        // Record operation for undo/redo
        (undoRedoManager as any).recordOperation?.('revert', changeId, change, index);
      } else {
        console.error('❌ SchemaChangesPanel: Failed to revert change:', result.error);
        throw result.error || new Error('Unknown error reverting change');
      }
    } catch (error) {
      console.error('❌ SchemaChangesPanel: Error reverting change:', error, {
        changeId,
        changeType: change.changeType,
        originalColumn: change.originalColumn,
        newColumn: change.newColumn
      });
      throw error;
    }
  };

  const handleConfirmBulkAction = async () => {
    console.log('🔧 SchemaChangesPanel: Confirming bulk action using shared utilities:', confirmationDialog.type);

    try {
      if (confirmationDialog.type === 'accept') {
        // Legacy support for accept operation
        acceptableChanges.forEach((change, index) => onAcceptChange(getChangeIdForChange(change, index)));
      } else if (confirmationDialog.type === 'revert') {
        revertAllAppliedChanges();
      } else if (confirmationDialog.type === 'apply') {
        await applyAllPendingChanges();
      }
    } catch (error) {
      console.error('❌ SchemaChangesPanel: Bulk action failed:', error);
    } finally {
      setConfirmationDialog(resetConfirmationConfig());
    }
  };

  const handleConfirmSingleAction = async () => {
    console.log('🔧 SchemaChangesPanel: Confirming single action using shared utilities:', confirmationDialog.type);

    try {
      if (confirmationDialog.change && confirmationDialog.changeIndex !== undefined) {
        if (confirmationDialog.type === 'remove') {
          await applyChangeDirectly(confirmationDialog.change, confirmationDialog.changeIndex);
        }
      }
    } catch (error) {
      console.error('❌ SchemaChangesPanel: Single action failed:', error);
    } finally {
      setConfirmationDialog(resetConfirmationConfig());
    }
  };

  /**
   * Handle applying all pending schema transformations using enhanced bulk operations
   */
  const handleApplyAllChanges = async () => {
    console.log('🔧 SchemaChangesPanel: Starting enhanced bulk apply operation');

    // Check if we have pending changes
    const pendingChanges = changes
      .map((change, index) => ({ change, index }))
      .filter(({ change, index }) => !isChangeApplied(change, index));

    if (pendingChanges.length === 0) {
      console.log('🔧 SchemaChangesPanel: No pending changes to apply');
      return;
    }

    // Check if individual transformation callbacks are available
    if (!onApplyColumnRename || !onApplyColumnAddition || !onApplyColumnRemoval) {
      console.log('❌ SchemaChangesPanel: Missing required individual transformation callbacks');
      return;
    }

    // Check if confirmation is needed for destructive changes
    const hasDestructiveChanges = pendingChanges.some(({ change }) =>
      change.changeType.toLowerCase() === 'remove'
    );

    if (hasDestructiveChanges) {
      // Show confirmation dialog for destructive changes
      const confirmationConfig: ConfirmationDialogConfig = {
        open: true,
        type: 'apply',
        count: pendingChanges.length,
        change: pendingChanges[0].change,
        changeIndex: 0
      };

      setConfirmationDialog(confirmationConfig);
    } else {
      // Apply directly if no destructive changes
      await applyAllPendingChanges();
    }
  };

  /**
   * Apply all pending changes using shared transformation manager
   */
  const applyAllPendingChanges = async () => {
    console.log('🔧 SchemaChangesPanel: Executing bulk apply operation using shared utilities');

    const pendingChanges = changes
      .map((change, index) => ({ change, index }))
      .filter(({ change, index }) => !isChangeApplied(change, index));

    if (pendingChanges.length === 0) {
      console.log('🔧 SchemaChangesPanel: No pending changes to apply');
      return;
    }

    console.log('🔧 SchemaChangesPanel: Found pending changes:', {
      totalChanges: changes.length,
      pendingCount: pendingChanges.length,
      pendingChanges: pendingChanges.map(({ change, index }) => ({
        index,
        type: change.changeType,
        originalColumn: change.originalColumn,
        newColumn: change.newColumn
      }))
    });

    try {
      // Use shared transformation manager for bulk operations
      console.log('🔧 SchemaChangesPanel: Calling transformationManager.applyAllChanges');

      const progressResult = await transformationManager.applyAllChanges(pendingChanges);

      console.log('🏁 SchemaChangesPanel: Bulk apply operation completed:', {
        total: progressResult.total,
        completed: progressResult.completed,
        failed: progressResult.failed,
        errors: progressResult.errors.slice(0, 3).map(e => e.message) // Log first 3 error messages
      });

      // Show user feedback based on results
      if (progressResult.completed > 0 && progressResult.failed === 0) {
        console.log(`✅ SchemaChangesPanel: Successfully applied all ${progressResult.completed} changes`);
      } else if (progressResult.completed > 0 && progressResult.failed > 0) {
        console.warn(`⚠️ SchemaChangesPanel: Applied ${progressResult.completed} changes, but ${progressResult.failed} failed`);
      } else if (progressResult.failed > 0) {
        console.error(`❌ SchemaChangesPanel: Failed to apply ${progressResult.failed} changes`);
      }

      // Record bulk operation for undo/redo
      if (progressResult.completed > 0) {
        undoRedoManager.clearHistory(); // Clear history after bulk operation for simplicity
      }



    } catch (error) {
      console.error('❌ SchemaChangesPanel: Bulk apply operation failed:', error);
      throw error;
    }
  };

  /**
   * Handle reverting all applied transformations using enhanced bulk operations
   */
  const handleRevertAllChanges = () => {
    console.log('🔄 SchemaChangesPanel: Starting enhanced bulk revert operation');

    // Check if we have applied changes
    const appliedChanges = changes
      .map((change, index) => ({ change, index }))
      .filter(({ change, index }) => isChangeApplied(change, index));

    if (appliedChanges.length === 0) {
      console.log('🔄 SchemaChangesPanel: No applied changes to revert');
      return;
    }

    // Check if individual revert callback is available
    if (!onRevertChange) {
      console.log('❌ SchemaChangesPanel: Missing required individual revert callback');
      return;
    }

    // Show confirmation dialog for bulk revert
    const confirmationConfig: ConfirmationDialogConfig = {
      open: true,
      type: 'revert',
      count: appliedChanges.length,
      change: appliedChanges[0].change,
      changeIndex: 0
    };

    setConfirmationDialog(confirmationConfig);
  };

  /**
   * Revert all applied changes using shared transformation manager
   */
  const revertAllAppliedChanges = () => {
    console.log('🔄 SchemaChangesPanel: Executing bulk revert operation using shared utilities');

    const appliedChanges = changes
      .map((change, index) => ({ change, index }))
      .filter(({ change, index }) => isChangeApplied(change, index));

    if (appliedChanges.length === 0) {
      console.log('🔄 SchemaChangesPanel: No applied changes to revert');
      return;
    }

    console.log('🔄 SchemaChangesPanel: Found applied changes:', {
      totalChanges: changes.length,
      appliedCount: appliedChanges.length,
      appliedChanges: appliedChanges.map(({ change, index }) => ({
        index,
        type: change.changeType,
        originalColumn: change.originalColumn,
        newColumn: change.newColumn
      }))
    });

    try {
      // Use shared transformation manager for bulk revert operations
      console.log('🔄 SchemaChangesPanel: Calling transformationManager.revertAllChanges');

      const progressResult = transformationManager.revertAllChanges(appliedChanges);

      console.log('🏁 SchemaChangesPanel: Bulk revert operation completed:', {
        total: progressResult.total,
        completed: progressResult.completed,
        failed: progressResult.failed,
        errors: progressResult.errors.slice(0, 3).map(e => e.message) // Log first 3 error messages
      });

      // Show user feedback based on results
      if (progressResult.completed > 0 && progressResult.failed === 0) {
        console.log(`✅ SchemaChangesPanel: Successfully reverted all ${progressResult.completed} changes`);
      } else if (progressResult.completed > 0 && progressResult.failed > 0) {
        console.warn(`⚠️ SchemaChangesPanel: Reverted ${progressResult.completed} changes, but ${progressResult.failed} failed`);
      } else if (progressResult.failed > 0) {
        console.error(`❌ SchemaChangesPanel: Failed to revert ${progressResult.failed} changes`);
      }

      // Record bulk revert for undo/redo
      if (progressResult.completed > 0) {
        undoRedoManager.clearHistory(); // Clear history after bulk operation for simplicity
      }


    } catch (error) {
      console.error('❌ SchemaChangesPanel: Bulk revert operation failed:', error);
      throw error;
    }
  };

  /**
   * Get count of applied changes
   */
  const getAppliedChangesCount = (): number => {
    if (appliedChangeIds) {
      return changes.filter((change, index) => isChangeApplied(change, index)).length;
    }
    return localAppliedChanges.size;
  };

  /**
   * Handle preview of what data will look like after all transformations
   */
  const handlePreviewChanges = () => {
    console.log('👁️ SchemaChangesPanel: Generating preview of pending changes');

    // In a real implementation, this would show a preview dialog
    // For now, we'll just show an alert with the transformation summary
    const pendingChanges = changes.filter((change, index) => !isChangeApplied(change, index));
    const renameCount = pendingChanges.filter(c => c.changeType.toLowerCase() === 'rename').length;
    const addCount = pendingChanges.filter(c => c.changeType.toLowerCase() === 'add').length;
    const removeCount = pendingChanges.filter(c => c.changeType.toLowerCase() === 'remove').length;

    const totalRowsAffected = pendingChanges.reduce((sum, change) =>
      sum + (change.rowCountAffected || 0), 0
    );

    console.log('👁️ SchemaChangesPanel: Preview summary:', {
      pendingCount: pendingChanges.length,
      renameCount,
      addCount,
      removeCount,
      totalRowsAffected
    });

    alert(`Preview: This will rename ${renameCount} columns, add ${addCount} columns, and remove ${removeCount} columns affecting ${totalRowsAffected} total rows.`);
  };

  const handleCancelBulkAction = () => {
    setConfirmationDialog(resetConfirmationConfig());
  };

  /**
   * Handle enhanced bulk operation execution
   */
  const handleExecuteBulkOperation = async (config: SelectiveBulkConfig): Promise<BulkOperationResult> => {
    console.log('🔧 SchemaChangesPanel: Executing enhanced bulk operation:', config);

    const changesWithIndex = changes.map((change, index) => ({ change, index }));
    const result = await transformationManager.executeSelectiveBulkOperation(config, changesWithIndex);

    // Add to history
    const historyEntry: BulkOperationHistoryEntry = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      operationType: config.operationType,
      selectedChanges: changesWithIndex
        .filter(({ change, index }) => config.selectedChangeIds.has(generateChangeId(change, index)))
        .map(({ change }) => change),
      result,
      canRollback: result.success || result.summary.successfulOperations > 0
    };

    setOperationHistory(prev => [historyEntry, ...prev.slice(0, 9)]); // Keep last 10 entries

    return result;
  };

  /**
   * Handle bulk operation preview
   */
  const handlePreviewBulkOperation = (config: SelectiveBulkConfig) => {
    const changesWithIndex = changes.map((change, index) => ({ change, index }));
    return transformationManager.previewBulkOperation(config, changesWithIndex);
  };

  /**
   * Handle operation rollback
   */
  const handleRollbackOperation = async (entryId: string): Promise<void> => {
    console.log('🔄 SchemaChangesPanel: Rolling back operation:', entryId);

    const entry = operationHistory.find(e => e.id === entryId);
    if (!entry) {
      throw new Error('Operation not found in history');
    }

    // Create opposite operation config
    const rollbackConfig: SelectiveBulkConfig = {
      selectedChangeIds: new Set(entry.selectedChanges.map((change, index) => generateChangeId(change, index))),
      operationType: entry.operationType === 'apply' ? 'revert' : 'apply',
      config: {
        continueOnError: true,
        showProgress: true,
        allowCancellation: false,
        maxRetries: 1
      }
    };

    const changesWithIndex = changes.map((change, index) => ({ change, index }));
    const rollbackResult = await transformationManager.executeSelectiveBulkOperation(rollbackConfig, changesWithIndex);

    // Add rollback to history
    const rollbackEntry: BulkOperationHistoryEntry = {
      id: `rollback-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      operationType: rollbackConfig.operationType,
      selectedChanges: entry.selectedChanges,
      result: rollbackResult,
      canRollback: false // Prevent rollback of rollbacks
    };

    setOperationHistory(prev => [rollbackEntry, ...prev]);

    // Mark original entry as rolled back
    setOperationHistory(prev => prev.map(e =>
      e.id === entryId ? { ...e, canRollback: false } : e
    ));
  };

  /**
   * Handle retry failed operations
   */
  const handleRetryOperation = async (entryId: string): Promise<void> => {
    console.log('🔄 SchemaChangesPanel: Retrying failed operations:', entryId);

    const entry = operationHistory.find(e => e.id === entryId);
    if (!entry || !entry.result.errorReport) {
      throw new Error('No failed operations to retry');
    }

    // Create retry config with only failed changes
    const failedChangeIds = new Set(
      entry.result.errorReport.errors.map(error => generateChangeId(error.change, 0))
    );

    const retryConfig: SelectiveBulkConfig = {
      selectedChangeIds: failedChangeIds,
      operationType: entry.operationType,
      config: {
        continueOnError: true,
        showProgress: true,
        allowCancellation: true,
        maxRetries: 3 // More retries for retry operation
      }
    };

    const changesWithIndex = changes.map((change, index) => ({ change, index }));
    const retryResult = await transformationManager.executeSelectiveBulkOperation(retryConfig, changesWithIndex);

    // Add retry to history
    const retryEntry: BulkOperationHistoryEntry = {
      id: `retry-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      operationType: entry.operationType,
      selectedChanges: entry.result.errorReport.errors.map(error => error.change),
      result: retryResult,
      canRollback: retryResult.success || retryResult.summary.successfulOperations > 0
    };

    setOperationHistory(prev => [retryEntry, ...prev]);
  };

  /**
   * Handle clear operation history
   */
  const handleClearHistory = () => {
    setOperationHistory([]);
  };

  // Empty state when no changes exist
  if (changes.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Transform sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography variant="body1" color="text.secondary" gutterBottom>
          No Schema Changes
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Your data structure matches the target schema perfectly.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header section */}
      <Box sx={{ mb: 2, flexShrink: 0 }}>
        {/* Header content removed - tab badges already show counts */}
      </Box>

      {/* Changes List - Scrollable within parent container */}
      <Box sx={{
        flexGrow: 1,
        mb: 2,
        overflow: 'auto',
        minHeight: 0,
        '&::-webkit-scrollbar': {
          width: '8px',
        },
        '&::-webkit-scrollbar-track': {
          backgroundColor: 'grey.100',
          borderRadius: '4px',
        },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: 'grey.400',
          borderRadius: '4px',
          '&:hover': {
            backgroundColor: 'grey.600',
          },
        },
      }}>
        <Stack spacing={2}>
          {changes.map((change, index) => {
            const isApplied = isChangeApplied(change, index);

            return (
              <SchemaChangeCard
                key={index}
                change={change}
                index={index}
                isApplied={isApplied}
                onApplyChange={handleApplyChange}
                onRevertChange={handleRevertChange}
                getChangeId={getChangeIdForChange}
              />
            );
          })}
        </Stack>
      </Box>

      {/* Bulk Actions Footer - Compact Layout */}
      {
        changes.length > 0 && (
          <Box sx={{ flexShrink: 0, pt: 1.5, borderTop: 1, borderColor: 'divider' }}>
            {/* Header with inline stats */}
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'primary.dark', fontSize: '0.875rem' }}>
                Bulk Actions
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {getAppliedChangesCount()}/{changes.length} applied • {' '}
                {changes.filter(c => c.changeType.toLowerCase() === 'rename').length}R {' '}
                {changes.filter(c => c.changeType.toLowerCase() === 'add').length}A {' '}
                {changes.filter(c => c.changeType.toLowerCase() === 'remove').length}D
              </Typography>
            </Box>

            {/* Actions Row - Centered layout with left and right sections */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              {/* Left section - Main action buttons */}
              <Stack direction="row" spacing={1} alignItems="center">
                <Button
                  variant="contained"
                  color="primary"
                  size="small"
                  startIcon={<PlaylistAddCheck />}
                  onClick={handleApplyAllChanges}
                  disabled={getAppliedChangesCount() === changes.length}
                  sx={{
                    textTransform: 'none',
                    fontWeight: 'bold',
                    fontSize: '0.75rem',
                    minWidth: 120,
                    py: 0.5
                  }}
                >
                  Apply All
                </Button>

                {getAppliedChangesCount() > 0 && (
                  <Button
                    variant="outlined"
                    color="secondary"
                    size="small"
                    startIcon={<Undo />}
                    onClick={handleRevertAllChanges}
                    sx={{
                      textTransform: 'none',
                      fontWeight: 'bold',
                      fontSize: '0.75rem',
                      minWidth: 120,
                      py: 0.5
                    }}
                  >
                    Revert All
                  </Button>
                )}

                <Button
                  variant="outlined"
                  color="info"
                  size="small"
                  startIcon={<Settings />}
                  onClick={() => {
                    setBulkOperationType('apply');
                    setShowBulkDialog(true);
                  }}
                  disabled={changes.length === 0}
                  sx={{
                    textTransform: 'none',
                    fontSize: '0.75rem',
                    minWidth: 100,
                    py: 0.5
                  }}
                >
                  Advanced
                </Button>
              </Stack>

              {/* Center divider */}
              <Box sx={{ flexGrow: 1, display: 'flex', justifyContent: 'center' }}>
                <Divider orientation="vertical" flexItem sx={{ height: 20 }} />
              </Box>

              {/* Right section - Undo/Redo buttons */}
              <Stack direction="row" spacing={1} alignItems="center">
                <Button
                  size="small"
                  variant="text"
                  onClick={() => undoRedoManager.undo()}
                  disabled={!undoRedoManager.canUndo()}
                  sx={{
                    textTransform: 'none',
                    minWidth: 60,
                    fontSize: '0.75rem',
                    py: 0.25
                  }}
                >
                  Undo
                </Button>

                <Button
                  size="small"
                  variant="text"
                  onClick={() => undoRedoManager.redo()}
                  disabled={!undoRedoManager.canRedo()}
                  sx={{
                    textTransform: 'none',
                    minWidth: 60,
                    fontSize: '0.75rem',
                    py: 0.25
                  }}
                >
                  Redo
                </Button>

                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {(() => {
                    const history = undoRedoManager.getHistorySize();
                    return `${history.undoCount}↶ ${history.redoCount}↷`;
                  })()}
                </Typography>

                {operationHistory.length > 0 && (
                  <Button
                    variant="text"
                    color="info"
                    size="small"
                    startIcon={<History />}
                    onClick={() => setShowHistory(true)}
                    sx={{
                      textTransform: 'none',
                      fontSize: '0.75rem',
                      minWidth: 80,
                      py: 0.5
                    }}
                  >
                    History
                  </Button>
                )}
              </Stack>
            </Box>

            {/* Status message row */}
            <Stack direction="row" alignItems="center">
              {getAppliedChangesCount() > 0 && (
                <Typography variant="caption" color="success.main" sx={{ fontSize: '0.7rem', fontStyle: 'italic' }}>
                  Changes applied immediately
                </Typography>
              )}
            </Stack>
          </Box>
        )
      }

      {/* Confirmation Dialog for Bulk Actions and Destructive Changes */}
      <Dialog
        open={confirmationDialog.open}
        onClose={handleCancelBulkAction}
        aria-labelledby="action-dialog-title"
        aria-describedby="action-dialog-description"
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle id="action-dialog-title" sx={{ pb: 1 }}>
          {confirmationDialog.type === 'remove' ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'warning.main' }}>
              <Remove />
              Confirm Column Removal
            </Box>
          ) : confirmationDialog.type === 'apply' ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'primary.main' }}>
              <PlaylistAddCheck />
              Apply All Schema Changes
            </Box>
          ) : confirmationDialog.type === 'revert' ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'secondary.main' }}>
              <Undo />
              Revert All Schema Changes
            </Box>
          ) : (
            `Confirm Bulk ${confirmationDialog.type === 'accept' ? 'Accept' : 'Action'}`
          )}
        </DialogTitle>
        <DialogContent>
          {confirmationDialog.type === 'remove' && confirmationDialog.change ? (
            <>
              <DialogContentText id="action-dialog-description">
                Are you sure you want to remove the column "{confirmationDialog.change.originalColumn}"?
                This action will permanently delete the column and all its data from your dataset.
              </DialogContentText>
              <Box sx={{ mt: 2, p: 2, backgroundColor: 'warning.50', borderRadius: 1, border: 1, borderColor: 'warning.200' }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'warning.dark', mb: 1 }}>
                  ⚠️ Warning: This action cannot be undone
                </Typography>
                <Typography variant="body2" color="warning.dark">
                  • Column: {confirmationDialog.change.originalColumn}
                </Typography>
                <Typography variant="body2" color="warning.dark">
                  • Affected rows: {confirmationDialog.change.rowCountAffected || 'Unknown'}
                </Typography>
                <Typography variant="body2" color="warning.dark">
                  • Reason: {confirmationDialog.change.reason || 'Column not required in target schema'}
                </Typography>
              </Box>
            </>
          ) : (
            <DialogContentText id="action-dialog-description">
              {confirmationDialog.type === 'apply' ? (
                <>
                  This will apply {confirmationDialog.count} changes to your data structure.
                  {(() => {
                    const pendingChanges = changes.filter((change, index) => !isChangeApplied(change, index));
                    const removeCount = pendingChanges.filter(c => c.changeType.toLowerCase() === 'remove').length;
                    const renameCount = pendingChanges.filter(c => c.changeType.toLowerCase() === 'rename').length;
                    const addCount = pendingChanges.filter(c => c.changeType.toLowerCase() === 'add').length;

                    const parts = [];
                    if (renameCount > 0) parts.push(`${renameCount} column rename${renameCount > 1 ? 's' : ''}`);
                    if (addCount > 0) parts.push(`${addCount} column addition${addCount > 1 ? 's' : ''}`);
                    if (removeCount > 0) parts.push(`${removeCount} column removal${removeCount > 1 ? 's' : ''}`);

                    return parts.length > 0 ? ` This includes ${parts.join(', ')}.` : '';
                  })()}
                  {' '}All changes will be executed in the correct sequence to avoid conflicts.
                </>
              ) : confirmationDialog.type === 'revert' ? (
                <>
                  This will revert {confirmationDialog.count} applied changes and restore your data to its original state before any transformations were applied.
                </>
              ) : confirmationDialog.type === 'accept' ? (
                `Are you sure you want to accept all ${confirmationDialog.count} schema changes? This will mark them as accepted and they will be applied to your data.`
              ) : (
                `Are you sure you want to proceed with this bulk action on ${confirmationDialog.count} schema changes?`
              )}
            </DialogContentText>
          )}

          {confirmationDialog.type !== 'remove' && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                This action affects the following changes:
              </Typography>
              <Box sx={{ mt: 1, maxHeight: 200, overflow: 'auto' }}>
                {confirmationDialog.type === 'apply' ? (
                  changes.filter((change, index) => !isChangeApplied(change, index)).map((change, index) => (
                    <Typography key={index} variant="body2" sx={{ ml: 2, mb: 0.5 }}>
                      • {change.reason || `${getChangeTypeLabel(change.changeType)} column transformation`}
                    </Typography>
                  ))
                ) : confirmationDialog.type === 'revert' ? (
                  changes.filter((change, index) => isChangeApplied(change, index)).map((change, index) => (
                    <Typography key={index} variant="body2" sx={{ ml: 2, mb: 0.5 }}>
                      • {change.reason || `${getChangeTypeLabel(change.changeType)} column transformation`}
                    </Typography>
                  ))
                ) : (
                  (confirmationDialog.type === 'accept' ? acceptableChanges : revertableChanges).map((change, index) => (
                    <Typography key={index} variant="body2" sx={{ ml: 2, mb: 0.5 }}>
                      • {change.reason || `${getChangeTypeLabel(change.changeType)} column transformation`}
                    </Typography>
                  ))
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleCancelBulkAction} color="inherit" sx={{ textTransform: 'none' }}>
            Cancel
          </Button>
          <Button
            onClick={confirmationDialog.type === 'remove' ? handleConfirmSingleAction : handleConfirmBulkAction}
            color={
              confirmationDialog.type === 'remove' ? 'warning' :
                confirmationDialog.type === 'apply' ? 'primary' :
                  confirmationDialog.type === 'revert' ? 'secondary' :
                    confirmationDialog.type === 'accept' ? 'primary' : 'secondary'
            }
            variant="contained"
            autoFocus
            sx={{ textTransform: 'none', fontWeight: 'bold' }}
          >
            {confirmationDialog.type === 'remove' ? 'Remove Column' :
              confirmationDialog.type === 'apply' ? 'Apply All Changes' :
                confirmationDialog.type === 'revert' ? 'Revert All Changes' :
                  confirmationDialog.type === 'accept' ? 'Accept All' : 'Confirm'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Enhanced Bulk Operations Dialog */}
      <BulkOperationsDialog
        open={showBulkDialog}
        onClose={() => setShowBulkDialog(false)}
        changes={changes.map((change, index) => ({ change, index }))}
        appliedChangeIds={appliedChangeIds || localAppliedChanges}
        operationType={bulkOperationType}
        onExecuteBulkOperation={handleExecuteBulkOperation}
        onPreviewBulkOperation={handlePreviewBulkOperation}
        onViewHistory={() => {
          setShowBulkDialog(false);
          setShowHistory(true);
        }}
      />

      {/* Bulk Operation History Dialog */}
      <BulkOperationHistory
        open={showHistory}
        onClose={() => setShowHistory(false)}
        history={operationHistory}
        onRollback={handleRollbackOperation}
        onClearHistory={handleClearHistory}
        onRetryOperation={handleRetryOperation}
      />
    </Box >
  );
};
