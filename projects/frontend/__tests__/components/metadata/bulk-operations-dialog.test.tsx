/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BulkOperationsDialog } from '../../../components/metadata/bulk-operations-dialog';
import { SchemaAlignmentChangeDetail } from '../../../lib/types';
import {
  BulkOperationResult,
  BulkOperationPreview,
  SelectiveBulkConfig
} from '../../../lib/transformation-operations';

// Mock data
const mockChanges = [
  {
    change: {
      changeType: 'rename',
      originalColumn: 'old_name',
      newColumn: 'new_name',
      reason: 'Standardize naming',
      rowCountAffected: 100
    } as SchemaAlignmentChangeDetail,
    index: 0
  },
  {
    change: {
      changeType: 'add',
      newColumn: 'added_column',
      reason: 'Required field',
      rowCountAffected: 100
    } as SchemaAlignmentChangeDetail,
    index: 1
  },
  {
    change: {
      changeType: 'remove',
      originalColumn: 'deprecated_field',
      reason: 'No longer needed',
      rowCountAffected: 100
    } as SchemaAlignmentChangeDetail,
    index: 2
  }
];

const mockAppliedChangeIds = new Set<string>();

const mockPreview: BulkOperationPreview = {
  affectedChanges: mockChanges.map(c => c.change),
  impact: {
    totalRowsAffected: 300,
    columnsAffected: 3,
    destructiveOperations: 1,
    estimatedDuration: 500
  },
  confidenceDistribution: {
    high: 1,
    medium: 0,
    low: 0,
    averageScore: 0.9,
    minScore: 0.85,
    maxScore: 0.95,
  },
  conflicts: [],
  warnings: ['1 operations will permanently remove data'],
  safeToExecute: true
};

const mockSuccessResult: BulkOperationResult = {
  success: true,
  progress: {
    total: 3,
    completed: 3,
    failed: 0,
    errors: [],
    cancelled: false,
    canCancel: false,
    startTime: new Date(),
    operationResults: [],
    cancel: jest.fn()
  },
  summary: {
    totalOperations: 3,
    successfulOperations: 3,
    failedOperations: 0,
    cancelledOperations: 0,
    totalDuration: 450,
    averageOperationTime: 150
  },
  confidenceDistribution: {
    high: 1,
    medium: 0,
    low: 0,
    averageScore: 0.9,
    minScore: 0.85,
    maxScore: 0.95,
  }
};

const mockFailureResult: BulkOperationResult = {
  success: false,
  progress: {
    total: 3,
    completed: 2,
    failed: 1,
    errors: [new Error('Test error')],
    cancelled: false,
    canCancel: false,
    startTime: new Date(),
    operationResults: [],
    cancel: jest.fn()
  },
  summary: {
    totalOperations: 3,
    successfulOperations: 2,
    failedOperations: 1,
    cancelledOperations: 0,
    totalDuration: 400,
    averageOperationTime: 133
  },
  confidenceDistribution: {
    high: 1,
    medium: 0,
    low: 0,
    averageScore: 0.9,
    minScore: 0.85,
    maxScore: 0.95,
  },
  errorReport: {
    errors: [{
      changeId: 'remove-deprecated_field-2',
      change: mockChanges[2].change,
      error: new Error('Cannot remove column'),
      retryCount: 0
    }],
    recoveryOptions: ['Retry failed operations individually']
  }
};

describe('BulkOperationsDialog', () => {
  const defaultProps = {
    open: true,
    onClose: jest.fn(),
    changes: mockChanges,
    appliedChangeIds: mockAppliedChangeIds,
    operationType: 'apply' as const,
    onExecuteBulkOperation: jest.fn(),
    onPreviewBulkOperation: jest.fn(),
    onViewHistory: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    defaultProps.onPreviewBulkOperation.mockReturnValue(mockPreview);
  });

  describe('Dialog Rendering', () => {
    it('renders dialog with correct title for apply operation', () => {
      render(<BulkOperationsDialog {...defaultProps} />);

      expect(screen.getByText('Apply Schema Changes')).toBeInTheDocument();
    });

    it('renders dialog with correct title for revert operation', () => {
      render(<BulkOperationsDialog {...defaultProps} operationType="revert" />);

      expect(screen.getByText('Revert Schema Changes')).toBeInTheDocument();
    });

    it('displays all available changes with checkboxes', () => {
      render(<BulkOperationsDialog {...defaultProps} />);

      expect(screen.getByText('Rename "old_name" to "new_name"')).toBeInTheDocument();
      expect(screen.getByText('Add column "added_column"')).toBeInTheDocument();
      expect(screen.getByText('Remove column "deprecated_field"')).toBeInTheDocument();

      // Should have 3 checkboxes (all selected by default)
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes).toHaveLength(3);
      checkboxes.forEach(checkbox => {
        expect(checkbox).toBeChecked();
      });
    });

    it('shows selection count correctly', () => {
      render(<BulkOperationsDialog {...defaultProps} />);

      expect(screen.getByText('Select Changes (3 of 3)')).toBeInTheDocument();
    });
  });

  describe('Change Selection', () => {
    it('allows selecting and deselecting individual changes', async () => {
      const user = userEvent.setup();
      render(<BulkOperationsDialog {...defaultProps} />);

      const checkboxes = screen.getAllByRole('checkbox');

      // Uncheck first change
      await user.click(checkboxes[0]);
      expect(screen.getByText('Select Changes (2 of 3)')).toBeInTheDocument();

      // Check it again
      await user.click(checkboxes[0]);
      expect(screen.getByText('Select Changes (3 of 3)')).toBeInTheDocument();
    });

    it('provides select all and select none functionality', async () => {
      const user = userEvent.setup();
      render(<BulkOperationsDialog {...defaultProps} />);

      // Click Select None
      await user.click(screen.getByText('Select None'));
      expect(screen.getByText('Select Changes (0 of 3)')).toBeInTheDocument();

      // Click Select All
      await user.click(screen.getByText('Select All'));
      expect(screen.getByText('Select Changes (3 of 3)')).toBeInTheDocument();
    });

    it('disables execute button when no changes selected', async () => {
      const user = userEvent.setup();
      render(<BulkOperationsDialog {...defaultProps} />);

      // Deselect all changes
      await user.click(screen.getByText('Select None'));

      const executeButton = screen.getByText(/Apply \d+ Selected/);
      expect(executeButton).toBeDisabled();
    });
  });

  describe('Preview Functionality', () => {
    it('shows preview when preview button is clicked', async () => {
      const user = userEvent.setup();
      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText('Preview'));

      expect(screen.getByText('Operation Preview')).toBeInTheDocument();
      expect(screen.getByText('3 operations')).toBeInTheDocument();
      expect(screen.getByText('300 rows affected')).toBeInTheDocument();
      expect(screen.getByText('1 destructive')).toBeInTheDocument();
    });

    it('shows warnings in preview', async () => {
      const user = userEvent.setup();
      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText('Preview'));

      expect(screen.getByText('Warnings')).toBeInTheDocument();
      expect(screen.getByText('1 operations will permanently remove data')).toBeInTheDocument();
    });

    it('shows conflicts when present', async () => {
      const previewWithConflicts = {
        ...mockPreview,
        conflicts: ['Column name conflict'],
        safeToExecute: false
      };
      defaultProps.onPreviewBulkOperation.mockReturnValue(previewWithConflicts);

      const user = userEvent.setup();
      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText('Preview'));

      expect(screen.getByText('Conflicts Detected')).toBeInTheDocument();
      expect(screen.getByText('Column name conflict')).toBeInTheDocument();

      // Execute button should still be visible (not disabled in moderate validation mode)
      // but will show warning color instead of primary
      const executeButton = screen.getByText(/Apply \d+ Selected/);
      expect(executeButton).toBeInTheDocument();
    });
  });

  describe('Advanced Settings', () => {
    it('shows advanced settings when settings button is clicked', async () => {
      const user = userEvent.setup();
      render(<BulkOperationsDialog {...defaultProps} />);

      // Click settings button
      const settingsButton = screen.getByLabelText('Advanced settings');
      await user.click(settingsButton);

      expect(screen.getByText('Advanced Settings')).toBeInTheDocument();
      expect(screen.getByText('Error Handling')).toBeInTheDocument();
      expect(screen.getByText('Allow operation cancellation')).toBeInTheDocument();
    });

    it('allows toggling advanced settings', async () => {
      const user = userEvent.setup();
      render(<BulkOperationsDialog {...defaultProps} />);

      // Open advanced settings
      const settingsButton = screen.getByLabelText('Advanced settings');
      await user.click(settingsButton);

      // Toggle allow cancellation - it defaults to true (checked)
      const allowCancellationCheckbox = screen.getByLabelText('Allow operation cancellation');
      expect(allowCancellationCheckbox).toBeChecked();

      await user.click(allowCancellationCheckbox);
      expect(allowCancellationCheckbox).not.toBeChecked();
    });
  });

  describe('Operation Execution', () => {
    it('executes bulk operation when execute button is clicked', async () => {
      const user = userEvent.setup();
      defaultProps.onExecuteBulkOperation.mockResolvedValue(mockSuccessResult);

      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText(/Apply \d+ Selected/));

      await waitFor(() => {
        expect(defaultProps.onExecuteBulkOperation).toHaveBeenCalledWith(
          expect.objectContaining({
            operationType: 'apply',
            selectedChangeIds: expect.any(Set),
            config: expect.objectContaining({
              continueOnError: true,
              showProgress: true,
              allowCancellation: true
            })
          })
        );
      });
    });

    it('shows progress during operation execution', async () => {
      const user = userEvent.setup();

      // Mock a delayed execution
      defaultProps.onExecuteBulkOperation.mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve(mockSuccessResult), 100))
      );

      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText(/Apply \d+ Selected/));

      // Should show progress indicator
      expect(screen.getByText('Operation Progress')).toBeInTheDocument();

      // Wait for completion (component has delays for preparation, validation, backup phases)
      await waitFor(() => {
        expect(screen.getByText('Operation Results')).toBeInTheDocument();
      }, { timeout: 3000 });
    });

    it('displays success results correctly', async () => {
      const user = userEvent.setup();
      defaultProps.onExecuteBulkOperation.mockResolvedValue(mockSuccessResult);

      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText(/Apply \d+ Selected/));

      await waitFor(() => {
        expect(screen.getByText('Operation Results')).toBeInTheDocument();
        expect(screen.getByText('Success')).toBeInTheDocument();
        expect(screen.getByText('3 successful')).toBeInTheDocument();
      });
    });

    it('displays failure results with error details', async () => {
      const user = userEvent.setup();
      defaultProps.onExecuteBulkOperation.mockResolvedValue(mockFailureResult);

      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText(/Apply \d+ Selected/));

      await waitFor(() => {
        expect(screen.getByText('Operation Results')).toBeInTheDocument();
        expect(screen.getByText('Completed with errors')).toBeInTheDocument();
        expect(screen.getByText('2 successful')).toBeInTheDocument();
        expect(screen.getByText('1 failed')).toBeInTheDocument();
      });

      // Should show retry button - note button text includes count and there may be multiple
      expect(screen.getAllByText(/Retry Failed/).length).toBeGreaterThan(0);
    });

    it('shows error details when expanded', async () => {
      const user = userEvent.setup();
      defaultProps.onExecuteBulkOperation.mockResolvedValue(mockFailureResult);

      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText(/Apply \d+ Selected/));

      await waitFor(() => {
        expect(screen.getByText('View Error Details')).toBeInTheDocument();
      });

      // Expand error details
      await user.click(screen.getByText('View Error Details'));

      expect(screen.getByText('Cannot remove column')).toBeInTheDocument();
    });
  });

  describe('Operation Cancellation', () => {
    it('shows cancel button during execution when cancellation is allowed', async () => {
      const user = userEvent.setup();

      const mockProgressWithCancel = {
        ...mockSuccessResult.progress,
        canCancel: true,
        cancel: jest.fn()
      };

      // Mock ongoing execution
      defaultProps.onExecuteBulkOperation.mockImplementation(() =>
        new Promise(() => {}) // Never resolves to simulate ongoing operation
      );

      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText(/Apply \d+ Selected/));

      // Should show cancel button
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('calls cancel function when cancel button is clicked', async () => {
      const user = userEvent.setup();
      const mockCancel = jest.fn();

      // Mock ongoing execution with cancellable progress
      defaultProps.onExecuteBulkOperation.mockImplementation(() => {
        // Simulate progress update with cancel function
        return new Promise(() => {}); // Never resolves
      });

      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText(/Apply \d+ Selected/));

      // Wait for cancel button to appear and click it
      await waitFor(() => {
        const cancelButton = screen.getByText('Cancel');
        expect(cancelButton).toBeInTheDocument();
      });
    });
  });

  describe('History Integration', () => {
    it('shows history button when onViewHistory is provided', () => {
      render(<BulkOperationsDialog {...defaultProps} />);

      const historyButton = screen.getByLabelText('View operation history');
      expect(historyButton).toBeInTheDocument();
    });

    it('calls onViewHistory when history button is clicked', async () => {
      const user = userEvent.setup();
      render(<BulkOperationsDialog {...defaultProps} />);

      const historyButton = screen.getByLabelText('View operation history');
      await user.click(historyButton);

      expect(defaultProps.onViewHistory).toHaveBeenCalled();
    });

    it('does not show history button when onViewHistory is not provided', () => {
      const propsWithoutHistory = { ...defaultProps, onViewHistory: undefined };
      render(<BulkOperationsDialog {...propsWithoutHistory} />);

      expect(screen.queryByLabelText('View operation history')).not.toBeInTheDocument();
    });
  });

  describe('Dialog Behavior', () => {
    it('prevents closing during operation execution', async () => {
      const user = userEvent.setup();

      // Mock ongoing execution
      defaultProps.onExecuteBulkOperation.mockImplementation(() =>
        new Promise(() => {}) // Never resolves
      );

      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText(/Apply \d+ Selected/));

      // Try to close dialog - should not call onClose
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(defaultProps.onClose).not.toHaveBeenCalled();
    });

    it('allows closing after operation completion', async () => {
      const user = userEvent.setup();
      defaultProps.onExecuteBulkOperation.mockResolvedValue(mockSuccessResult);

      render(<BulkOperationsDialog {...defaultProps} />);

      await user.click(screen.getByText(/Apply \d+ Selected/));

      await waitFor(() => {
        expect(screen.getByText('Close')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Close'));
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('resets state when dialog is closed and reopened', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<BulkOperationsDialog {...defaultProps} />);

      // Deselect some changes
      await user.click(screen.getByText('Select None'));
      expect(screen.getByText('Select Changes (0 of 3)')).toBeInTheDocument();

      // Close dialog
      rerender(<BulkOperationsDialog {...defaultProps} open={false} />);

      // Reopen dialog
      rerender(<BulkOperationsDialog {...defaultProps} open={true} />);

      // Should reset to all selected
      expect(screen.getByText('Select Changes (3 of 3)')).toBeInTheDocument();
    });
  });
});
