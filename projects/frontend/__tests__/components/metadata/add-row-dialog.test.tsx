/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AddRowDialog } from '../../../components/metadata/add-row-dialog';

describe('AddRowDialog', () => {
  const defaultProps = {
    open: true,
    referenceRowIndex: 2, // 0-based, so this is row 3 in display
    insertPosition: 'below' as const,
    loading: false,
    onConfirm: jest.fn(),
    onCancel: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders dialog with correct title and reference row number', () => {
      render(<AddRowDialog {...defaultProps} />);

      expect(screen.getByText('Add New Row')).toBeInTheDocument();
      expect(screen.getByText(/Add a new empty row to your data/)).toBeInTheDocument();
      expect(screen.getByText(/Choose where to insert the new row relative to row 3/)).toBeInTheDocument();
    });

    it('renders position options with correct labels', () => {
      render(<AddRowDialog {...defaultProps} />);

      expect(screen.getByText('Above row 3')).toBeInTheDocument();
      expect(screen.getByText('Below row 3')).toBeInTheDocument();
      expect(screen.getByText('Insert the new row before the current row')).toBeInTheDocument();
      expect(screen.getByText('Insert the new row after the current row')).toBeInTheDocument();
    });

    it('renders action buttons', () => {
      render(<AddRowDialog {...defaultProps} />);

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /add row/i })).toBeInTheDocument();
    });

    it('renders informational note', () => {
      render(<AddRowDialog {...defaultProps} />);

      expect(screen.getByText(/The new row will be empty initially/)).toBeInTheDocument();
      expect(screen.getByText(/All subsequent row numbers will be updated automatically/)).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      render(<AddRowDialog {...defaultProps} open={false} />);

      expect(screen.queryByText('Add New Row')).not.toBeInTheDocument();
    });
  });

  describe('Position Selection', () => {
    it('selects initial position correctly', () => {
      render(<AddRowDialog {...defaultProps} insertPosition="above" />);

      const aboveRadio = screen.getByRole('radio', { name: /above row 3/i });
      const belowRadio = screen.getByRole('radio', { name: /below row 3/i });

      expect(aboveRadio).toBeChecked();
      expect(belowRadio).not.toBeChecked();
    });

    it('allows changing position selection', async () => {
      const user = userEvent.setup();
      render(<AddRowDialog {...defaultProps} insertPosition="below" />);

      const aboveRadio = screen.getByRole('radio', { name: /above row 3/i });
      const belowRadio = screen.getByRole('radio', { name: /below row 3/i });

      expect(belowRadio).toBeChecked();
      expect(aboveRadio).not.toBeChecked();

      await user.click(aboveRadio);

      expect(aboveRadio).toBeChecked();
      expect(belowRadio).not.toBeChecked();
    });

    it('resets position when dialog reopens', () => {
      const { rerender } = render(<AddRowDialog {...defaultProps} insertPosition="below" />);

      // Change selection
      const aboveRadio = screen.getByRole('radio', { name: /above row 3/i });
      fireEvent.click(aboveRadio);
      expect(aboveRadio).toBeChecked();

      // Close and reopen with different initial position
      rerender(<AddRowDialog {...defaultProps} open={false} />);
      rerender(<AddRowDialog {...defaultProps} open={true} insertPosition="above" />);

      const newAboveRadio = screen.getByRole('radio', { name: /above row 3/i });
      const newBelowRadio = screen.getByRole('radio', { name: /below row 3/i });

      expect(newAboveRadio).toBeChecked();
      expect(newBelowRadio).not.toBeChecked();
    });
  });

  describe('User Interactions', () => {
    it('calls onCancel when cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<AddRowDialog {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(defaultProps.onCancel).toHaveBeenCalledTimes(1);
    });

    it('calls onConfirm with selected position when add button is clicked', async () => {
      const user = userEvent.setup();
      render(<AddRowDialog {...defaultProps} insertPosition="below" />);

      const addButton = screen.getByRole('button', { name: /add row/i });
      await user.click(addButton);

      expect(defaultProps.onConfirm).toHaveBeenCalledWith('below');
    });

    it('calls onConfirm with changed position', async () => {
      const user = userEvent.setup();
      render(<AddRowDialog {...defaultProps} insertPosition="below" />);

      // Change position to above
      const aboveRadio = screen.getByRole('radio', { name: /above row 3/i });
      await user.click(aboveRadio);

      // Confirm
      const addButton = screen.getByRole('button', { name: /add row/i });
      await user.click(addButton);

      expect(defaultProps.onConfirm).toHaveBeenCalledWith('above');
    });

    it('calls onCancel when dialog backdrop is clicked', async () => {
      const user = userEvent.setup();
      render(<AddRowDialog {...defaultProps} />);

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
      render(<AddRowDialog {...defaultProps} loading={true} />);

      expect(screen.getByText('Adding...')).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('disables buttons during loading', () => {
      render(<AddRowDialog {...defaultProps} loading={true} />);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      const addButton = screen.getByRole('button', { name: /adding/i });

      expect(cancelButton).toBeDisabled();
      expect(addButton).toBeDisabled();
    });

    it('disables radio buttons during loading', () => {
      render(<AddRowDialog {...defaultProps} loading={true} />);

      const aboveRadio = screen.getByRole('radio', { name: /above row 3/i });
      const belowRadio = screen.getByRole('radio', { name: /below row 3/i });

      expect(aboveRadio).toBeDisabled();
      expect(belowRadio).toBeDisabled();
    });

    it('prevents dialog close during loading', () => {
      render(<AddRowDialog {...defaultProps} loading={true} />);

      // Try to close with Escape key
      fireEvent.keyDown(document, { key: 'Escape' });

      // Dialog should still be open
      expect(screen.getByText('Add New Row')).toBeInTheDocument();
      expect(defaultProps.onCancel).not.toHaveBeenCalled();
    });
  });

  describe('Row Number Display', () => {
    it('displays correct row number for different indices', () => {
      const { rerender } = render(<AddRowDialog {...defaultProps} referenceRowIndex={0} />);
      expect(screen.getByText(/relative to row 1/)).toBeInTheDocument();
      expect(screen.getByText('Above row 1')).toBeInTheDocument();
      expect(screen.getByText('Below row 1')).toBeInTheDocument();

      rerender(<AddRowDialog {...defaultProps} referenceRowIndex={9} />);
      expect(screen.getByText(/relative to row 10/)).toBeInTheDocument();
      expect(screen.getByText('Above row 10')).toBeInTheDocument();
      expect(screen.getByText('Below row 10')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<AddRowDialog {...defaultProps} />);

      expect(screen.getByRole('dialog')).toHaveAttribute('aria-labelledby', 'add-row-dialog-title');
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-describedby', 'add-row-dialog-description');
      expect(screen.getByRole('radiogroup')).toHaveAttribute('aria-label', 'insert position');
    });

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<AddRowDialog {...defaultProps} />);

      // The default position is 'below', so that radio should be checked initially
      const belowRadio = screen.getByRole('radio', { name: /below row 3/i });
      expect(belowRadio).toBeChecked();

      // Tab to the radio group - the checked radio should get focus
      await user.tab();
      expect(belowRadio).toHaveFocus();

      // Arrow up to first radio button
      await user.keyboard('{ArrowUp}');
      const aboveRadio = screen.getByRole('radio', { name: /above row 3/i });
      expect(aboveRadio).toHaveFocus();
      expect(aboveRadio).toBeChecked();
    });

    it('confirms addition when Enter is pressed on add button', async () => {
      const user = userEvent.setup();
      render(<AddRowDialog {...defaultProps} />);

      // Focus on add button and press Enter
      const addButton = screen.getByRole('button', { name: /add row/i });
      await user.click(addButton);

      expect(defaultProps.onConfirm).toHaveBeenCalledWith('below');
    });
  });

  describe('Edge Cases', () => {
    it('handles very large row numbers', () => {
      render(<AddRowDialog {...defaultProps} referenceRowIndex={999} />);

      expect(screen.getByText(/relative to row 1000/)).toBeInTheDocument();
      expect(screen.getByText('Above row 1000')).toBeInTheDocument();
      expect(screen.getByText('Below row 1000')).toBeInTheDocument();
    });

    it('handles row index 0 correctly', () => {
      render(<AddRowDialog {...defaultProps} referenceRowIndex={0} />);

      expect(screen.getByText(/relative to row 1/)).toBeInTheDocument();
    });
  });
});
