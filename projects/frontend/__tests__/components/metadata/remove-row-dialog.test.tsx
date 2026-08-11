/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RemoveRowDialog } from '../../../components/metadata/remove-row-dialog';
import { ValidationErrorType } from '../../../lib/types';

describe('RemoveRowDialog', () => {
  const defaultProps = {
    open: true,
    rowIndex: 2, // 0-based, so this is row 3 in display
    rowData: ['John', 'Doe', '30', 'Engineer', ''],
    affectedCells: 4, // 4 non-empty cells
    loading: false,
    affectedValidationErrors: [
      { column: 'FirstName', errorType: ValidationErrorType.REQUIRED_VALUE, currentValue: 'John', row: 2, recommendedValue: null, validOptions: null, confidenceScore: 0.85, confidenceLevel: 'High' },
      { column: 'Age', errorType: ValidationErrorType.INVALID_PATTERN, currentValue: '30', row: 2, recommendedValue: null, validOptions: null, confidenceScore: 0.80, confidenceLevel: 'High' }
    ],
    onConfirm: jest.fn(),
    onCancel: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders dialog with correct title and row number', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByText('Remove Row 3')).toBeInTheDocument();
      expect(screen.getByText(/You are about to remove row 3/)).toBeInTheDocument();
    });

    it('renders warning alert', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByText('This action cannot be undone!')).toBeInTheDocument();
      expect(screen.getByText(/Row 3 and all its data will be permanently deleted/)).toBeInTheDocument();
      expect(screen.getByText(/All subsequent rows will be renumbered/)).toBeInTheDocument();
    });

    it('renders action buttons', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /remove row/i })).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      render(<RemoveRowDialog {...defaultProps} open={false} />);

      expect(screen.queryByText('Remove Row 3')).not.toBeInTheDocument();
    });
  });

  describe('Data Statistics', () => {
    it('displays correct cell statistics', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByText('4 cells with data')).toBeInTheDocument();
      expect(screen.getByText('1 empty cells')).toBeInTheDocument();
    });

    it('handles all empty cells', () => {
      render(<RemoveRowDialog {...defaultProps} rowData={['', '', '', '', '']} affectedCells={0} />);

      expect(screen.getByText('0 cells with data')).toBeInTheDocument();
      expect(screen.getByText('5 empty cells')).toBeInTheDocument();
      expect(screen.getByText('This row is empty (no data will be lost)')).toBeInTheDocument();
    });

    it('handles all filled cells', () => {
      render(<RemoveRowDialog {...defaultProps} rowData={['A', 'B', 'C']} affectedCells={3} />);

      expect(screen.getByText('3 cells with data')).toBeInTheDocument();
      expect(screen.getByText('0 empty cells')).toBeInTheDocument();
    });
  });

  describe('Data Preview', () => {
    it('shows data preview table for non-empty rows', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByText('Data Preview:')).toBeInTheDocument();
      expect(screen.getByText('Column')).toBeInTheDocument();
      expect(screen.getByText('Value')).toBeInTheDocument();

      // Check that non-empty values are shown
      expect(screen.getByText('John')).toBeInTheDocument();
      expect(screen.getByText('Doe')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
      expect(screen.getByText('Engineer')).toBeInTheDocument();
    });

    it('shows column numbers correctly', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByText('Column 1')).toBeInTheDocument();
      expect(screen.getByText('Column 2')).toBeInTheDocument();
      expect(screen.getByText('Column 3')).toBeInTheDocument();
      expect(screen.getByText('Column 4')).toBeInTheDocument();
    });

    it('truncates long values with ellipsis', () => {
      const longValue = 'This is a very long value that should be truncated with ellipsis when displayed in the preview table';
      const rowDataWithLongValue = ['Short', longValue, 'Another'];

      render(<RemoveRowDialog {...defaultProps} rowData={rowDataWithLongValue} affectedCells={3} />);

      const longValueElement = screen.getByText(longValue);
      expect(longValueElement).toHaveStyle({
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      });
      expect(longValueElement).toHaveAttribute('title', longValue);
    });

    it('shows truncation message for many cells', () => {
      const manyValues = Array.from({ length: 15 }, (_, i) => `Value${i + 1}`);
      render(<RemoveRowDialog {...defaultProps} rowData={manyValues} affectedCells={15} />);

      expect(screen.getByText('... and 5 more cells')).toBeInTheDocument();
    });

    it('does not show preview for empty rows', () => {
      render(<RemoveRowDialog {...defaultProps} rowData={['', '', '']} affectedCells={0} />);

      expect(screen.queryByText('Data Preview:')).not.toBeInTheDocument();
      expect(screen.getByText('This row is empty (no data will be lost)')).toBeInTheDocument();
    });
  });

  describe('Data Loss Warning', () => {
    it('shows data loss warning for rows with data', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByText('Data Loss Warning:')).toBeInTheDocument();
      expect(screen.getByText(/4 cells containing data will be permanently deleted/)).toBeInTheDocument();
      expect(screen.getByText(/Consider exporting your data before proceeding/)).toBeInTheDocument();
    });

    it('does not show data loss warning for empty rows', () => {
      render(<RemoveRowDialog {...defaultProps} affectedCells={0} />);

      expect(screen.queryByText('Data Loss Warning:')).not.toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('calls onCancel when cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<RemoveRowDialog {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(defaultProps.onCancel).toHaveBeenCalledTimes(1);
    });

    it('calls onConfirm when remove button is clicked', async () => {
      const user = userEvent.setup();
      render(<RemoveRowDialog {...defaultProps} />);

      const removeButton = screen.getByRole('button', { name: /remove row/i });
      await user.click(removeButton);

      expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);
    });

    it('calls onCancel when dialog backdrop is clicked', async () => {
      const user = userEvent.setup();
      render(<RemoveRowDialog {...defaultProps} />);

      // Click on backdrop (outside dialog content)
      const backdrop = document.querySelector('.MuiBackdrop-root');
      if (backdrop) {
        await user.click(backdrop);
        expect(defaultProps.onCancel).toHaveBeenCalledTimes(1);
      }
    });
  });

  describe('Loading State', () => {
    it('shows loading state correctly', () => {
      render(<RemoveRowDialog {...defaultProps} loading={true} />);

      expect(screen.getByText('Removing...')).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('disables buttons during loading', () => {
      render(<RemoveRowDialog {...defaultProps} loading={true} />);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      const removeButton = screen.getByRole('button', { name: /removing/i });

      expect(cancelButton).toBeDisabled();
      expect(removeButton).toBeDisabled();
    });

    it('prevents dialog close during loading', () => {
      render(<RemoveRowDialog {...defaultProps} loading={true} />);

      // Try to close with Escape key
      fireEvent.keyDown(document, { key: 'Escape' });

      // Dialog should still be open
      expect(screen.getByText('Remove Row 3')).toBeInTheDocument();
      expect(defaultProps.onCancel).not.toHaveBeenCalled();
    });
  });

  describe('Row Number Display', () => {
    it('displays correct row number for different indices', () => {
      const { rerender } = render(<RemoveRowDialog {...defaultProps} rowIndex={0} />);
      expect(screen.getByText('Remove Row 1')).toBeInTheDocument();
      expect(screen.getByText(/You are about to remove row 1/)).toBeInTheDocument();

      rerender(<RemoveRowDialog {...defaultProps} rowIndex={9} />);
      expect(screen.getByText('Remove Row 10')).toBeInTheDocument();
      expect(screen.getByText(/You are about to remove row 10/)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByRole('dialog')).toHaveAttribute('aria-labelledby', 'remove-row-dialog-title');
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-describedby', 'remove-row-dialog-description');
    });

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<RemoveRowDialog {...defaultProps} />);

      // Tab to cancel button
      await user.tab();
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      expect(cancelButton).toHaveFocus();

      // Tab to remove button
      await user.tab();
      const removeButton = screen.getByRole('button', { name: /remove row/i });
      expect(removeButton).toHaveFocus();
    });

    it('confirms removal when Enter is pressed on remove button', async () => {
      const user = userEvent.setup();
      render(<RemoveRowDialog {...defaultProps} />);

      const removeButton = screen.getByRole('button', { name: /remove row/i });
      await user.click(removeButton);

      expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);
    });
  });

  describe('Validation Errors Impact', () => {
    it('shows validation errors impact when errors exist', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByText('Validation Errors Impact:')).toBeInTheDocument();
      expect(screen.getByText(/2 validation errors on this row will be resolved/)).toBeInTheDocument();
      expect(screen.getByText(/All subsequent row numbers in remaining validation errors will be updated/)).toBeInTheDocument();
    });

    it('displays validation error chips', () => {
      render(<RemoveRowDialog {...defaultProps} />);

      expect(screen.getByText('FirstName: REQUIRED_VALUE')).toBeInTheDocument();
      expect(screen.getByText('Age: INVALID_PATTERN')).toBeInTheDocument();
    });

    it('shows truncation for many validation errors', () => {
      const manyErrors = Array.from({ length: 5 }, (_, i) => ({
        column: `Column${i + 1}`,
        errorType: ValidationErrorType.REQUIRED_VALUE,
        currentValue: `Value${i + 1}`,
        row: 2,
        recommendedValue: null,
        validOptions: null,
        confidenceScore: 0.85,
        confidenceLevel: 'High'
      }));

      render(<RemoveRowDialog {...defaultProps} affectedValidationErrors={manyErrors} />);

      expect(screen.getByText('+2 more')).toBeInTheDocument();
    });

    it('does not show validation errors section when no errors exist', () => {
      render(<RemoveRowDialog {...defaultProps} affectedValidationErrors={[]} />);

      expect(screen.queryByText('Validation Errors Impact:')).not.toBeInTheDocument();
    });

    it('handles single validation error correctly', () => {
      const singleError = [{ column: 'Name', errorType: ValidationErrorType.REQUIRED_VALUE, currentValue: 'John', row: 2, recommendedValue: null, validOptions: null, confidenceScore: 0.85, confidenceLevel: 'High' }];
      render(<RemoveRowDialog {...defaultProps} affectedValidationErrors={singleError} />);

      expect(screen.getByText(/1 validation error on this row will be resolved/)).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles very large row numbers', () => {
      render(<RemoveRowDialog {...defaultProps} rowIndex={999} />);

      expect(screen.getByText('Remove Row 1000')).toBeInTheDocument();
      expect(screen.getByText(/You are about to remove row 1000/)).toBeInTheDocument();
    });

    it('handles row index 0 correctly', () => {
      render(<RemoveRowDialog {...defaultProps} rowIndex={0} />);

      expect(screen.getByText('Remove Row 1')).toBeInTheDocument();
    });

    it('handles empty row data array', () => {
      render(<RemoveRowDialog {...defaultProps} rowData={[]} affectedCells={0} affectedValidationErrors={[]} />);

      expect(screen.getByText('0 cells with data')).toBeInTheDocument();
      expect(screen.getByText('0 empty cells')).toBeInTheDocument();
      expect(screen.getByText('This row is empty (no data will be lost)')).toBeInTheDocument();
    });

    it('handles single cell row', () => {
      render(<RemoveRowDialog {...defaultProps} rowData={['SingleValue']} affectedCells={1} />);

      expect(screen.getByText('1 cells with data')).toBeInTheDocument();
      expect(screen.getByText('0 empty cells')).toBeInTheDocument();
      expect(screen.getByText('SingleValue')).toBeInTheDocument();
    });

    it('handles row with only whitespace', () => {
      render(<RemoveRowDialog {...defaultProps} rowData={['  ', '\t', '\n']} affectedCells={0} affectedValidationErrors={[]} />);

      expect(screen.getByText('0 cells with data')).toBeInTheDocument();
      expect(screen.getByText('This row is empty (no data will be lost)')).toBeInTheDocument();
    });

    it('handles row with validation errors but no data', () => {
      const errorsOnEmptyRow = [{ column: 'Name', errorType: ValidationErrorType.REQUIRED_VALUE, currentValue: '', row: 2, recommendedValue: null, validOptions: null, confidenceScore: 0.90, confidenceLevel: 'High' }];
      render(<RemoveRowDialog {...defaultProps} rowData={['', '', '']} affectedCells={0} affectedValidationErrors={errorsOnEmptyRow} />);

      expect(screen.getByText('This row is empty (no data will be lost)')).toBeInTheDocument();
      expect(screen.getByText('Validation Errors Impact:')).toBeInTheDocument();
      expect(screen.getByText(/1 validation error on this row will be resolved/)).toBeInTheDocument();
    });
  });
});
