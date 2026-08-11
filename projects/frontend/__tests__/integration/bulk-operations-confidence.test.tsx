/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BulkOperationsDialog } from '../../components/metadata/bulk-operations-dialog';
import { SchemaAlignmentChangeDetail } from '../../lib/types';
import {
  BulkOperationResult,
  SelectiveBulkConfig,
  BulkOperationPreview,
  calculateConfidenceDistribution
} from '../../lib/transformation-operations';

// Mock changes with confidence information
const mockChangesWithConfidence: Array<{ change: SchemaAlignmentChangeDetail; index: number }> = [
  {
    change: {
      changeType: 'rename',
      originalColumn: 'old_name',
      newColumn: 'new_name',
      reason: 'Target: new_name | Match: old_name | Confidence: High | Reasoning: Exact semantic match',
      confidenceScore: 0.9,
      confidenceLevel: 'High'
    },
    index: 0
  },
  {
    change: {
      changeType: 'add',
      newColumn: 'added_column',
      reason: 'Target: added_column | Confidence: High | Reasoning: Required by schema',
      confidenceScore: 0.9,
      confidenceLevel: 'High'
    },
    index: 1
  },
  {
    change: {
      changeType: 'remove',
      originalColumn: 'removed_column',
      reason: 'Source: removed_column | Confidence: Medium | Reasoning: Not in target schema',
      confidenceScore: 0.65,
      confidenceLevel: 'Medium'
    },
    index: 2
  }
];

describe('Bulk Operations with Confidence Information', () => {
  const mockOnExecuteBulkOperation = jest.fn();
  const mockOnPreviewBulkOperation = jest.fn();
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock preview function to return confidence distribution
    mockOnPreviewBulkOperation.mockImplementation((config: SelectiveBulkConfig): BulkOperationPreview => {
      const selectedChanges = mockChangesWithConfidence
        .filter(({ change, index }) => {
          const changeId = `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`;
          return config.selectedChangeIds.has(changeId);
        })
        .map(({ change }) => change);

      const confidenceDistribution = calculateConfidenceDistribution(selectedChanges);

      return {
        affectedChanges: selectedChanges,
        impact: {
          totalRowsAffected: 100,
          columnsAffected: selectedChanges.length,
          destructiveOperations: selectedChanges.filter(c => c.changeType === 'remove').length,
          estimatedDuration: 1000
        },
        confidenceDistribution,
        conflicts: [],
        warnings: [],
        safeToExecute: true
      };
    });

    // Mock execute function to return confidence distribution
    mockOnExecuteBulkOperation.mockImplementation(async (config: SelectiveBulkConfig): Promise<BulkOperationResult> => {
      const selectedChanges = mockChangesWithConfidence
        .filter(({ change, index }) => {
          const changeId = `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`;
          return config.selectedChangeIds.has(changeId);
        })
        .map(({ change }) => change);

      const confidenceDistribution = calculateConfidenceDistribution(selectedChanges);

      return {
        success: true,
        progress: {
          total: selectedChanges.length,
          completed: selectedChanges.length,
          failed: 0,
          errors: [],
          cancelled: false,
          canCancel: false,
          startTime: new Date(),
          operationResults: [],
          cancel: () => {},
          currentOperation: 'Completed'
        },
        summary: {
          totalOperations: selectedChanges.length,
          successfulOperations: selectedChanges.length,
          failedOperations: 0,
          cancelledOperations: 0,
          totalDuration: 1000,
          averageOperationTime: 100
        },
        confidenceDistribution
      };
    });
  });

  const defaultProps = {
    open: true,
    onClose: mockOnClose,
    changes: mockChangesWithConfidence,
    appliedChangeIds: new Set<string>(),
    operationType: 'apply' as const,
    onExecuteBulkOperation: mockOnExecuteBulkOperation,
    onPreviewBulkOperation: mockOnPreviewBulkOperation
  };

  it('should display confidence levels for each change in the selection list', () => {
    render(<BulkOperationsDialog {...defaultProps} />);

    // Check that confidence indicators are displayed for each change
    const highConfidenceChips = screen.getAllByText('High Confidence');
    expect(highConfidenceChips.length).toBe(2); // Two high confidence changes

    const mediumConfidenceChips = screen.getAllByText('Medium Confidence');
    expect(mediumConfidenceChips.length).toBe(1); // One medium confidence change

    // Check that confidence tooltips are present
    const infoIcons = screen.getAllByTestId('InfoOutlinedIcon');
    expect(infoIcons.length).toBeGreaterThan(0);
  });

  it('should show confidence distribution in preview', async () => {
    render(<BulkOperationsDialog {...defaultProps} />);

    // Click preview button
    const previewButton = screen.getByText('Preview');
    fireEvent.click(previewButton);

    await waitFor(() => {
      // Check that confidence distribution is displayed
      expect(screen.getByText('Confidence Distribution of Selected Operations')).toBeInTheDocument();

      // Check that confidence chips are displayed
      expect(screen.getByText('High: 2')).toBeInTheDocument();
      expect(screen.getByText('Medium: 1')).toBeInTheDocument();
      expect(screen.getByText('Low: 0')).toBeInTheDocument();
    });
  });

  it('should show confidence distribution in operation results', async () => {
    render(<BulkOperationsDialog {...defaultProps} />);

    // Execute the bulk operation - use more specific selector
    const executeButton = screen.getByRole('button', { name: /Apply 3 Selected/ });
    fireEvent.click(executeButton);

    await waitFor(() => {
      // Check that confidence distribution is displayed in results
      expect(screen.getByText('Confidence Distribution of Applied Changes')).toBeInTheDocument();

      // Verify the confidence distribution matches what was applied
      expect(screen.getByText('High: 2')).toBeInTheDocument();
      expect(screen.getByText('Medium: 1')).toBeInTheDocument();
    });
  });

  it('should calculate correct confidence distribution for selected changes', () => {
    const selectedChanges = mockChangesWithConfidence.map(({ change }) => change);
    const distribution = calculateConfidenceDistribution(selectedChanges);

    expect(distribution.high).toBe(2); // rename and add operations
    expect(distribution.medium).toBe(1); // remove operation
    expect(distribution.low).toBe(0);
    expect(distribution.averageScore).toBeCloseTo(0.82, 2); // (0.9 + 0.9 + 0.65) / 3
  });

  it('should update confidence distribution when selection changes', async () => {
    render(<BulkOperationsDialog {...defaultProps} />);

    // Initially all changes are selected
    expect(screen.getByText('Select Changes (3 of 3)')).toBeInTheDocument();

    // Uncheck one change (the medium confidence one - remove operation which is the 3rd item, index 2)
    const checkboxes = screen.getAllByRole('checkbox');
    const removeCheckbox = checkboxes.find((cb, index) => {
      // Find the checkbox associated with the remove operation
      const listItem = cb.closest('li');
      return listItem && listItem.textContent?.includes('removed_column');
    });

    if (removeCheckbox) {
      fireEvent.click(removeCheckbox);
    }

    await waitFor(() => {
      // Selection count should update
      expect(screen.getByText('Select Changes (2 of 3)')).toBeInTheDocument();
    });

    // Click preview to see updated confidence distribution
    const previewButton = screen.getByText('Preview');
    fireEvent.click(previewButton);

    await waitFor(() => {
      // Should now show only high confidence operations
      expect(screen.getByText('High: 2')).toBeInTheDocument();
      expect(screen.getByText('Medium: 0')).toBeInTheDocument();
    });
  });
});
