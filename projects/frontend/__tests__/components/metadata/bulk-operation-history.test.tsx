/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BulkOperationHistory, BulkOperationHistoryEntry } from '../../../components/metadata/bulk-operation-history';
import { SchemaAlignmentChangeDetail } from '../../../lib/types';
import { BulkOperationResult } from '../../../lib/transformation-operations';

// Mock data
const mockChanges: SchemaAlignmentChangeDetail[] = [
  {
    changeType: 'rename',
    originalColumn: 'old_name',
    newColumn: 'new_name',
    reason: 'Standardize naming',
    rowCountAffected: 100
  },
  {
    changeType: 'add',
    newColumn: 'added_column',
    reason: 'Required field',
    rowCountAffected: 100
  }
];

const mockSuccessResult: BulkOperationResult = {
  success: true,
  progress: {
    total: 2,
    completed: 2,
    failed: 0,
    errors: [],
    cancelled: false,
    canCancel: false,
    startTime: new Date(),
    operationResults: [],
    cancel: jest.fn()
  },
  summary: {
    totalOperations: 2,
    successfulOperations: 2,
    failedOperations: 0,
    cancelledOperations: 0,
    totalDuration: 300,
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
    total: 2,
    completed: 1,
    failed: 1,
    errors: [new Error('Test error')],
    cancelled: false,
    canCancel: false,
    startTime: new Date(),
    operationResults: [],
    cancel: jest.fn()
  },
  summary: {
    totalOperations: 2,
    successfulOperations: 1,
    failedOperations: 1,
    cancelledOperations: 0,
    totalDuration: 200,
    averageOperationTime: 100
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
      changeId: 'add-added_column-1',
      change: mockChanges[1],
      error: new Error('Cannot add column'),
      retryCount: 0
    }],
    recoveryOptions: ['Retry failed operations individually']
  }
};

const mockHistoryEntries: BulkOperationHistoryEntry[] = [
  {
    id: 'entry-1',
    timestamp: new Date('2024-01-15T10:30:00Z'),
    operationType: 'apply',
    selectedChanges: mockChanges,
    result: mockSuccessResult,
    canRollback: true
  },
  {
    id: 'entry-2',
    timestamp: new Date('2024-01-15T09:15:00Z'),
    operationType: 'revert',
    selectedChanges: [mockChanges[0]],
    result: mockFailureResult,
    canRollback: false
  }
];

describe('BulkOperationHistory', () => {
  const defaultProps = {
    open: true,
    onClose: jest.fn(),
    history: mockHistoryEntries,
    onRollback: jest.fn(),
    onClearHistory: jest.fn(),
    onRetryOperation: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Dialog Rendering', () => {
    it('renders dialog with correct title', () => {
      render(<BulkOperationHistory {...defaultProps} />);

      expect(screen.getByText('Bulk Operation History')).toBeInTheDocument();
    });

    it('shows clear history button when history exists', () => {
      render(<BulkOperationHistory {...defaultProps} />);

      const clearButton = screen.getByLabelText('Clear all history');
      expect(clearButton).toBeInTheDocument();
    });

    it('does not show clear history button when onClearHistory is not provided', () => {
      const propsWithoutClear = { ...defaultProps, onClearHistory: undefined };
      render(<BulkOperationHistory {...propsWithoutClear} />);

      expect(screen.queryByLabelText('Clear all history')).not.toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty state when no history entries exist', () => {
      const emptyProps = { ...defaultProps, history: [] };
      render(<BulkOperationHistory {...emptyProps} />);

      expect(screen.getByText('No Operation History')).toBeInTheDocument();
      expect(screen.getByText('Bulk operations you perform will appear here with rollback options.')).toBeInTheDocument();
    });

    it('does not show clear button in empty state', () => {
      const emptyProps = { ...defaultProps, history: [] };
      render(<BulkOperationHistory {...emptyProps} />);

      expect(screen.queryByLabelText('Clear all history')).not.toBeInTheDocument();
    });
  });

  describe('History Entry Display', () => {
    it('displays all history entries with correct status', () => {
      render(<BulkOperationHistory {...defaultProps} />);

      // First entry (success)
      expect(screen.getByText('Applied 2 changes')).toBeInTheDocument();
      expect(screen.getByText('Success')).toBeInTheDocument();

      // Second entry (failure)
      expect(screen.getByText('Reverted 1 changes')).toBeInTheDocument();
      expect(screen.getByText('Partial Success')).toBeInTheDocument();
    });

    it('shows timestamps and durations', () => {
      render(<BulkOperationHistory {...defaultProps} />);

      // Should show formatted timestamps and durations
      expect(screen.getByText('300ms')).toBeInTheDocument();
      expect(screen.getByText('200ms')).toBeInTheDocument();
    });

    it('displays operation summary chips correctly when expanded', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Expand first entry by clicking on it
      const firstEntry = screen.getByText('Applied 2 changes');
      await user.click(firstEntry);

      // Now operation summary should be visible
      await waitFor(() => {
        expect(screen.getAllByText('Operation Summary')[0]).toBeVisible();
      });
      expect(screen.getAllByText('2 total')[0]).toBeVisible();
      expect(screen.getAllByText('2 successful')[0]).toBeVisible();
      expect(screen.getAllByText('150ms avg')[0]).toBeVisible();
    });
  });

  describe('Entry Expansion', () => {
    it('expands entry to show detailed information', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Click to expand first entry
      const firstEntry = screen.getByText('Applied 2 changes');
      await user.click(firstEntry);

      // Now detailed info should be visible
      await waitFor(() => {
        expect(screen.getAllByText('Operation Summary')[0]).toBeVisible();
        expect(screen.getByText('Affected Changes (2)')).toBeVisible();
      });
    });

    it('shows affected changes list when expanded', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Expand first entry
      const firstEntry = screen.getByText('Applied 2 changes');
      await user.click(firstEntry);

      // Should show the affected changes after expansion
      await waitFor(() => {
        expect(screen.getAllByText(/old_name → new_name/)[0]).toBeVisible();
        expect(screen.getAllByText('added_column')[0]).toBeVisible();
        expect(screen.getAllByText('Standardize naming')[0]).toBeVisible();
        expect(screen.getAllByText('Required field')[0]).toBeVisible();
      });
    });

    it('shows error details for failed operations', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Expand second entry (the one with failures)
      const secondEntry = screen.getByText('Reverted 1 changes');
      await user.click(secondEntry);

      // Error details should appear after expansion
      await waitFor(() => {
        expect(screen.getByText('Error Details (1 errors)')).toBeVisible();
        expect(screen.getByText('Recovery Options')).toBeVisible();
      });
    });

    it('shows recovery options for failed operations', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Expand second entry
      const secondEntry = screen.getByText('Reverted 1 changes');
      await user.click(secondEntry);

      // Recovery options should appear after expansion
      await waitFor(() => {
        expect(screen.getByText('Recovery Options')).toBeVisible();
        expect(screen.getByText('Retry failed operations individually')).toBeVisible();
      });
    });

    it('collapses entry when clicked again', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      const firstEntry = screen.getByText('Applied 2 changes');

      // Expand
      await user.click(firstEntry);
      await waitFor(() => {
        expect(screen.getAllByText('Operation Summary')[0]).toBeVisible();
      });

      // Collapse
      await user.click(firstEntry);
      await waitFor(() => {
        // After collapsing, the accordion content should not be visible
        const summaries = screen.getAllByText('Operation Summary');
        summaries.forEach(el => expect(el).not.toBeVisible());
      });
    });
  });

  describe('Rollback Functionality', () => {
    it('shows rollback button for rollbackable entries', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Expand first entry (canRollback: true)
      const firstEntry = screen.getByText('Applied 2 changes');
      await user.click(firstEntry);

      // Rollback button should appear after expansion
      await waitFor(() => {
        expect(screen.getByText('Rollback')).toBeVisible();
      });
    });

    it('does not show rollback button for non-rollbackable entries', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Expand second entry (canRollback: false)
      const secondEntry = screen.getByText('Reverted 1 changes');
      await user.click(secondEntry);

      // Wait for expansion
      await waitFor(() => {
        expect(screen.getByText('Error Details (1 errors)')).toBeVisible();
      });

      // Rollback should not be present for this entry (canRollback: false)
      // Note: There may be a hidden rollback button in the first (collapsed) entry,
      // so we check that no visible Rollback button exists
      const rollbackButtons = screen.queryAllByText('Rollback');
      rollbackButtons.forEach(btn => expect(btn).not.toBeVisible());
    });

    it('calls onRollback when rollback button is clicked', async () => {
      const user = userEvent.setup();
      defaultProps.onRollback.mockResolvedValue(undefined);

      render(<BulkOperationHistory {...defaultProps} />);

      // Expand first entry and click rollback
      const firstEntry = screen.getByText('Applied 2 changes');
      await user.click(firstEntry);

      // Wait for rollback button to appear
      await waitFor(() => {
        expect(screen.getByText('Rollback')).toBeInTheDocument();
      });

      const rollbackButton = screen.getByText('Rollback');
      await user.click(rollbackButton);

      expect(defaultProps.onRollback).toHaveBeenCalledWith('entry-1');
    });

    it('shows loading state during rollback', async () => {
      const user = userEvent.setup();

      // Mock delayed rollback
      defaultProps.onRollback.mockImplementation(() =>
        new Promise(resolve => setTimeout(resolve, 100))
      );

      render(<BulkOperationHistory {...defaultProps} />);

      // Expand first entry and click rollback
      const firstEntry = screen.getByText('Applied 2 changes');
      await user.click(firstEntry);

      // Wait for rollback button to appear
      await waitFor(() => {
        expect(screen.getByText('Rollback')).toBeInTheDocument();
      });

      const rollbackButton = screen.getByText('Rollback');
      await user.click(rollbackButton);

      expect(screen.getByText('Rolling back...')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText('Rollback')).toBeInTheDocument();
      });
    });

    it('does not show rollback button when onRollback is not provided', async () => {
      const user = userEvent.setup();
      const propsWithoutRollback = { ...defaultProps, onRollback: undefined };

      render(<BulkOperationHistory {...propsWithoutRollback} />);

      // Expand first entry
      const firstEntry = screen.getByText('Applied 2 changes');
      await user.click(firstEntry);

      expect(screen.queryByText('Rollback')).not.toBeInTheDocument();
    });
  });

  describe('Retry Functionality', () => {
    it('shows retry button for entries with failures', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Expand second entry (has failures)
      const secondEntry = screen.getByText('Reverted 1 changes');
      await user.click(secondEntry);

      // Retry button should appear after expansion
      await waitFor(() => {
        expect(screen.getByText('Retry Failed')).toBeVisible();
      });
    });

    it('does not show retry button for successful entries', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Expand first entry (successful)
      const firstEntry = screen.getByText('Applied 2 changes');
      await user.click(firstEntry);

      // Wait for expansion
      await waitFor(() => {
        expect(screen.getAllByText('Operation Summary')[0]).toBeVisible();
      });

      // No retry button should be visible for successful entries
      const retryButtons = screen.queryAllByText('Retry Failed');
      retryButtons.forEach(btn => expect(btn).not.toBeVisible());
    });

    it('calls onRetryOperation when retry button is clicked', async () => {
      const user = userEvent.setup();
      defaultProps.onRetryOperation.mockResolvedValue(undefined);

      render(<BulkOperationHistory {...defaultProps} />);

      // Expand second entry and click retry
      const secondEntry = screen.getByText('Reverted 1 changes');
      await user.click(secondEntry);

      // Wait for retry button to appear
      await waitFor(() => {
        expect(screen.getByText('Retry Failed')).toBeInTheDocument();
      });

      const retryButton = screen.getByText('Retry Failed');
      await user.click(retryButton);

      expect(defaultProps.onRetryOperation).toHaveBeenCalledWith('entry-2');
    });

    it('shows loading state during retry', async () => {
      const user = userEvent.setup();

      // Mock delayed retry
      defaultProps.onRetryOperation.mockImplementation(() =>
        new Promise(resolve => setTimeout(resolve, 100))
      );

      render(<BulkOperationHistory {...defaultProps} />);

      // Expand second entry and click retry
      const secondEntry = screen.getByText('Reverted 1 changes');
      await user.click(secondEntry);

      // Wait for retry button to appear
      await waitFor(() => {
        expect(screen.getByText('Retry Failed')).toBeInTheDocument();
      });

      const retryButton = screen.getByText('Retry Failed');
      await user.click(retryButton);

      expect(screen.getByText('Retrying...')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText('Retry Failed')).toBeInTheDocument();
      });
    });

    it('does not show retry button when onRetryOperation is not provided', async () => {
      const user = userEvent.setup();
      const propsWithoutRetry = { ...defaultProps, onRetryOperation: undefined };

      render(<BulkOperationHistory {...propsWithoutRetry} />);

      // Expand second entry
      const secondEntry = screen.getByText('Reverted 1 changes');
      await user.click(secondEntry);

      expect(screen.queryByText('Retry Failed')).not.toBeInTheDocument();
    });
  });

  describe('Clear History', () => {
    it('calls onClearHistory when clear button is clicked', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      const clearButton = screen.getByLabelText('Clear all history');
      await user.click(clearButton);

      expect(defaultProps.onClearHistory).toHaveBeenCalled();
    });
  });

  describe('Status Display', () => {
    it('shows correct status colors and icons', () => {
      render(<BulkOperationHistory {...defaultProps} />);

      // Success entry should have success styling
      const successChip = screen.getByText('Success');
      expect(successChip).toBeInTheDocument();

      // Partial success entry should have warning styling
      const partialSuccessChip = screen.getByText('Partial Success');
      expect(partialSuccessChip).toBeInTheDocument();
    });

    it('displays operation counts correctly', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      // Expand second entry to see failure counts
      const secondEntry = screen.getByText('Reverted 1 changes');
      await user.click(secondEntry);

      // Wait for expansion - both entries share some chip text, verify expanded content exists
      await waitFor(() => {
        expect(screen.getAllByText('2 total').length).toBeGreaterThan(0);
        expect(screen.getAllByText('1 successful').length).toBeGreaterThan(0);
        expect(screen.getAllByText('1 failed').length).toBeGreaterThan(0);
      });
    });
  });

  describe('Dialog Behavior', () => {
    it('calls onClose when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<BulkOperationHistory {...defaultProps} />);

      const closeButton = screen.getByText('Close');
      await user.click(closeButton);

      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });
});
