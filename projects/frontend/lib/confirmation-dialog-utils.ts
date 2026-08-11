/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import { SchemaAlignmentChangeDetail } from './types';
import { generateTransformationPreview } from './schema-transformation-utils';

/**
 * Shared utilities for confirmation dialogs in schema transformation operations
 */

export interface ConfirmationDialogConfig {
  open: boolean;
  type: 'accept' | 'revert' | 'apply' | 'remove';
  count: number;
  changeIndex?: number;
  change?: SchemaAlignmentChangeDetail;
}

export interface ConfirmationContent {
  title: string;
  message: string;
  confirmButtonText: string;
  confirmButtonColor: 'primary' | 'secondary' | 'warning' | 'error';
  isDestructive: boolean;
}

/**
 * Generates confirmation dialog content based on the operation type
 */
export const generateConfirmationContent = (
  config: ConfirmationDialogConfig,
  changes: SchemaAlignmentChangeDetail[],
  appliedChangeIds: Set<string>
): ConfirmationContent => {
  switch (config.type) {
    case 'apply':
      const preview = generateTransformationPreview(changes, appliedChangeIds);
      const parts = [];
      if (preview.renameCount > 0) parts.push(`${preview.renameCount} column rename${preview.renameCount > 1 ? 's' : ''}`);
      if (preview.addCount > 0) parts.push(`${preview.addCount} column addition${preview.addCount > 1 ? 's' : ''}`);
      if (preview.removeCount > 0) parts.push(`${preview.removeCount} column removal${preview.removeCount > 1 ? 's' : ''}`);

      const includesPart = parts.length > 0 ? ` This includes ${parts.join(', ')}.` : '';
      return {
        title: 'Apply All Changes',
        message: `This will apply ${config.count} changes to your data structure.${includesPart} All changes will be executed in the correct sequence to avoid conflicts.`,
        confirmButtonText: 'Apply All Changes',
        confirmButtonColor: 'primary',
        isDestructive: preview.hasDestructive
      };

    case 'revert':
      return {
        title: 'Revert All Changes',
        message: `This will revert ${config.count} applied changes and restore your data to its original state before any transformations were applied.`,
        confirmButtonText: 'Revert All Changes',
        confirmButtonColor: 'secondary',
        isDestructive: true
      };

    case 'remove':
      const columnName = config.change?.originalColumn || 'unknown';
      return {
        title: 'Remove Column',
        message: `Are you sure you want to remove the column "${columnName}"? This action will permanently delete the column and all its data from your dataset.`,
        confirmButtonText: 'Remove Column',
        confirmButtonColor: 'warning',
        isDestructive: true
      };

    case 'accept':
      return {
        title: 'Accept All Changes',
        message: `Are you sure you want to accept all ${config.count} schema changes? This will mark them as accepted and they will be applied to your data.`,
        confirmButtonText: 'Accept All',
        confirmButtonColor: 'primary',
        isDestructive: false
      };

    default:
      return {
        title: 'Confirm Action',
        message: `Are you sure you want to proceed with this bulk action on ${config.count} schema changes?`,
        confirmButtonText: 'Confirm',
        confirmButtonColor: 'primary',
        isDestructive: false
      };
  }
};

/**
 * Generates warning information for destructive operations
 */
export const generateDestructiveWarning = (
  config: ConfirmationDialogConfig,
  changes: SchemaAlignmentChangeDetail[]
): {
  hasWarning: boolean;
  warningTitle?: string;
  warningMessage?: string;
  affectedItems?: string[];
} => {
  if (config.type === 'remove' && config.change) {
    return {
      hasWarning: true,
      warningTitle: 'Data Loss Warning',
      warningMessage: 'This action cannot be undone. All data in this column will be permanently lost.',
      affectedItems: [`Column: ${config.change.originalColumn}`]
    };
  }

  if (config.type === 'apply') {
    const destructiveChanges = changes.filter(change => change.changeType.toLowerCase() === 'remove');
    if (destructiveChanges.length > 0) {
      return {
        hasWarning: true,
        warningTitle: 'Destructive Changes Warning',
        warningMessage: `${destructiveChanges.length} column${destructiveChanges.length > 1 ? 's' : ''} will be permanently removed.`,
        affectedItems: destructiveChanges.map(change => `Remove: ${change.originalColumn}`)
      };
    }
  }

  if (config.type === 'revert') {
    return {
      hasWarning: true,
      warningTitle: 'Revert Warning',
      warningMessage: 'This will undo all applied transformations and return to the original data structure.',
      affectedItems: [`${config.count} applied changes will be reverted`]
    };
  }

  return { hasWarning: false };
};

/**
 * Validates if a confirmation dialog should be shown
 */
export const shouldShowConfirmation = (
  operationType: 'apply' | 'revert' | 'remove' | 'accept',
  changes: SchemaAlignmentChangeDetail[],
  appliedChangeIds?: Set<string>
): boolean => {
  switch (operationType) {
    case 'apply':
      // Show confirmation for destructive changes or bulk operations
      const pendingChanges = appliedChangeIds
        ? changes.filter((_, index) => !appliedChangeIds.has(`${changes[index].changeType}-${changes[index].originalColumn || changes[index].newColumn}-${index}`))
        : changes;
      return pendingChanges.length > 1 || pendingChanges.some(change => change.changeType.toLowerCase() === 'remove');

    case 'revert':
      // Always show confirmation for revert operations
      return true;

    case 'remove':
      // Always show confirmation for individual remove operations
      return true;

    case 'accept':
      // Show confirmation for bulk accept operations
      return changes.length > 1;

    default:
      return false;
  }
};

/**
 * Enhanced confirmation dialog utilities for both individual and bulk operations
 */

export interface ConfirmationOptions {
  showWarnings?: boolean;
  customMessage?: string;
  customTitle?: string;
  customButtonText?: string;
}

/**
 * Creates confirmation dialog configuration with enhanced options
 */
export const createEnhancedConfirmationConfig = (
  type: 'accept' | 'revert' | 'apply' | 'remove',
  count: number,
  change?: SchemaAlignmentChangeDetail,
  changeIndex?: number,
  options?: ConfirmationOptions
): ConfirmationDialogConfig => ({
  open: true,
  type,
  count,
  change,
  changeIndex,
  ...options
});

/**
 * Generates confirmation content with enhanced customization
 */
export const generateEnhancedConfirmationContent = (
  config: ConfirmationDialogConfig,
  changes: SchemaAlignmentChangeDetail[],
  appliedChangeIds: Set<string>,
  options?: ConfirmationOptions
): ConfirmationContent => {
  // Use custom content if provided
  if (options?.customTitle || options?.customMessage || options?.customButtonText) {
    const baseContent = generateConfirmationContent(config, changes, appliedChangeIds);
    return {
      ...baseContent,
      title: options.customTitle || baseContent.title,
      message: options.customMessage || baseContent.message,
      confirmButtonText: options.customButtonText || baseContent.confirmButtonText
    };
  }

  // Use standard content generation
  return generateConfirmationContent(config, changes, appliedChangeIds);
};

/**
 * Validates confirmation requirements for both individual and bulk operations
 */
export const validateConfirmationRequirements = (
  operationType: 'apply' | 'revert' | 'remove' | 'accept',
  changes: SchemaAlignmentChangeDetail[],
  appliedChangeIds?: Set<string>,
  forceConfirmation?: boolean
): {
  requiresConfirmation: boolean;
  reason: string;
  isDestructive: boolean;
  affectedCount: number;
} => {
  if (forceConfirmation) {
    return {
      requiresConfirmation: true,
      reason: 'Forced confirmation requested',
      isDestructive: false,
      affectedCount: changes.length
    };
  }

  switch (operationType) {
    case 'apply': {
      const pendingChanges = appliedChangeIds
        ? changes.filter((_, index) => !appliedChangeIds.has(`${changes[index].changeType}-${changes[index].originalColumn || changes[index].newColumn}-${index}`))
        : changes;

      const destructiveChanges = pendingChanges.filter(change => change.changeType.toLowerCase() === 'remove');
      const isBulk = pendingChanges.length > 1;
      const hasDestructive = destructiveChanges.length > 0;

      return {
        requiresConfirmation: isBulk || hasDestructive,
        reason: hasDestructive ? 'Contains destructive changes' : 'Bulk operation',
        isDestructive: hasDestructive,
        affectedCount: pendingChanges.length
      };
    }

    case 'revert': {
      const appliedChanges = appliedChangeIds
        ? changes.filter((_, index) => appliedChangeIds.has(`${changes[index].changeType}-${changes[index].originalColumn || changes[index].newColumn}-${index}`))
        : changes;

      return {
        requiresConfirmation: true,
        reason: 'Revert operation always requires confirmation',
        isDestructive: true,
        affectedCount: appliedChanges.length
      };
    }

    case 'remove':
      return {
        requiresConfirmation: true,
        reason: 'Remove operation is destructive',
        isDestructive: true,
        affectedCount: 1
      };

    case 'accept':
      return {
        requiresConfirmation: changes.length > 1,
        reason: 'Bulk accept operation',
        isDestructive: false,
        affectedCount: changes.length
      };

    default:
      return {
        requiresConfirmation: false,
        reason: 'Unknown operation type',
        isDestructive: false,
        affectedCount: 0
      };
  }
};

/**
 * Creates a default confirmation dialog config
 */
export const createConfirmationConfig = (
  type: 'accept' | 'revert' | 'apply' | 'remove',
  count: number,
  change?: SchemaAlignmentChangeDetail,
  changeIndex?: number
): ConfirmationDialogConfig => ({
  open: true,
  type,
  count,
  change,
  changeIndex
});

/**
 * Resets confirmation dialog to closed state
 */
export const resetConfirmationConfig = (): ConfirmationDialogConfig => ({
  open: false,
  type: 'accept',
  count: 0
});
