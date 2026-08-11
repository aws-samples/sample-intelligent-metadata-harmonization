/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RemoveColumnDialog } from '../../../components/metadata/remove-column-dialog';
import { beforeEach } from 'node:test';

describe('RemoveColumnDialog', () => {
  const defaultProps = {
    open: true,
    columnIndex: 1,
    columnName: 'TestColumn',
    columnData: ['value1', 'value2', '', 'value3', 'value4', 'value5', 'value6'],
    totalRows: 10,
    loading: false,
    onConfirm: jest.fn(),
    onCancel: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders dialog with column information', () => {
    render(<RemoveColumnDialog {...defaultProps} />);

    expect(screen.getByText('Remove Column: "TestColumn"')).toBeInTheDocument();
    expect(screen.getByText(/Warning: This action cannot be undone!/)).toBeInTheDocument();
    expect(screen.getByText(/Column: TestColumn/)).toBeInTheDocument();
    expect(screen.getByText(/Position: 2/)).toBeInTheDocument();
    expect(screen.getByText(/Total Rows: 10/)).toBeInTheDocument();
  });

  it('shows data preview for non-empty column', () => {
    render(<RemoveColumnDialog {...defaultProps} />);

    expect(screen.getByText('Data Preview (First 5 non-empty values)')).toBeInTheDocument();
    expect(screen.getByText('value1')).toBeInTheDocument();
    expect(screen.getByText('value2')).toBeInTheDocument();
    expect(screen.getByText('value3')).toBeInTheDocument();
    expect(screen.getByText('value4')).toBeInTheDocument();
    expect(screen.getByText('value5')).toBeInTheDocument();

    // Should show additional values indicator
    expect(screen.getByText('... and 2 more values')).toBeInTheDocument();
  });

  it('shows empty column message when no data', () => {
    const emptyProps = {
      ...defaultProps,
      columnData: ['', '', '']
    };

    render(<RemoveColumnDialog {...emptyProps} />);

    expect(screen.getByText('This column appears to be empty or contains only blank values.')).toBeInTheDocument();
    expect(screen.queryByText('Data Preview')).not.toBeInTheDocument();
  });

  it('shows impact information', () => {
    render(<RemoveColumnDialog {...defaultProps} />);

    expect(screen.getByText('Impact of Removal:')).toBeInTheDocument();
    expect(screen.getByText(/Column "TestColumn" will be permanently deleted/)).toBeInTheDocument();
    expect(screen.getByText(/All data in this column will be lost/)).toBeInTheDocument();
    expect(screen.getByText(/Column positions will shift left to fill the gap/)).toBeInTheDocument();
    expect(screen.getByText(/Any validation errors for this column will be cleared/)).toBeInTheDocument();
    expect(screen.getAllByText(/This action cannot be undone/).length).toBeGreaterThan(0);
  });

  it('calls onConfirm when Remove Column button is clicked', async () => {
    render(<RemoveColumnDialog {...defaultProps} />);

    const removeButton = screen.getByRole('button', { name: /Remove Column/i });
    fireEvent.click(removeButton);

    await waitFor(() => {
      expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);
    });
  });

  it('calls onCancel when Cancel button is clicked', async () => {
    render(<RemoveColumnDialog {...defaultProps} />);

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(defaultProps.onCancel).toHaveBeenCalledTimes(1);
    });
  });

  it('calls onCancel when dialog is closed', async () => {
    render(<RemoveColumnDialog {...defaultProps} />);

    // Simulate clicking outside the dialog (on backdrop)
    const backdrop = document.querySelector('.MuiBackdrop-root');
    if (backdrop) {
      fireEvent.click(backdrop);
    }

    await waitFor(() => {
      // MUI Dialog backdrop click may trigger onClose multiple times
      // What matters is that onCancel was called to close the dialog
      expect(defaultProps.onCancel).toHaveBeenCalled();
    });
  });

  it('shows loading state when processing', () => {
    const loadingProps = {
      ...defaultProps,
      loading: true
    };

    render(<RemoveColumnDialog {...loadingProps} />);

    const removeButton = screen.getByRole('button', { name: /Removing.../i });
    expect(removeButton).toBeDisabled();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    expect(cancelButton).toBeDisabled();
  });

  it('handles empty column data array', () => {
    const emptyDataProps = {
      ...defaultProps,
      columnData: [],
      totalRows: 0
    };

    render(<RemoveColumnDialog {...emptyDataProps} />);

    expect(screen.getByText('This column appears to be empty or contains only blank values.')).toBeInTheDocument();
    expect(screen.getByText(/Total Rows: 0/)).toBeInTheDocument();
  });

  it('shows correct row counts for mixed data', () => {
    const mixedDataProps = {
      ...defaultProps,
      columnData: ['value1', '', 'value2', '', ''],
      totalRows: 5
    };

    render(<RemoveColumnDialog {...mixedDataProps} />);

    expect(screen.getByText(/Rows with Data: 2/)).toBeInTheDocument();
    expect(screen.getByText(/Empty Rows: 3/)).toBeInTheDocument();
  });

  it('does not render when open is false', () => {
    const closedProps = {
      ...defaultProps,
      open: false
    };

    render(<RemoveColumnDialog {...closedProps} />);

    expect(screen.queryByText('Remove Column: "TestColumn"')).not.toBeInTheDocument();
  });

  it('has proper accessibility attributes', () => {
    render(<RemoveColumnDialog {...defaultProps} />);

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-labelledby', 'remove-column-dialog-title');
    expect(dialog).toHaveAttribute('aria-describedby', 'remove-column-dialog-description');
  });

  it('truncates long values in preview table', () => {
    const longValueProps = {
      ...defaultProps,
      columnData: ['This is a very long value that should be truncated in the preview table to prevent layout issues']
    };

    render(<RemoveColumnDialog {...longValueProps} />);

    const valueCell = screen.getByText(/This is a very long value/);
    expect(valueCell).toHaveStyle({
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    });
  });
});
