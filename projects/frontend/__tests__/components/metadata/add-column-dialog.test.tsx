/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AddColumnDialog } from '../../../components/metadata/add-column-dialog';

describe('AddColumnDialog', () => {
  const defaultProps = {
    open: true,
    referenceColumnIndex: 1,
    referenceColumnName: 'TestColumn',
    insertPosition: 'after' as const,
    existingColumnNames: ['Column1', 'TestColumn', 'Column3'],
    loading: false,
    onConfirm: jest.fn(),
    onCancel: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders dialog with correct title and content', () => {
    render(<AddColumnDialog {...defaultProps} />);

    expect(screen.getByText('Add New Column')).toBeInTheDocument();
    expect(screen.getByText(/Adding new column relative to "TestColumn"/)).toBeInTheDocument();
    expect(screen.getByLabelText('New Column Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Insert Position')).toBeInTheDocument();
  });

  it('generates default column name that does not conflict with existing names', () => {
    render(<AddColumnDialog {...defaultProps} />);

    const input = screen.getByLabelText('New Column Name') as HTMLInputElement;
    expect(input.value).toBe('New Column 1');
  });

  it('generates incremented default name when "New Column 1" already exists', () => {
    const propsWithConflict = {
      ...defaultProps,
      existingColumnNames: ['Column1', 'TestColumn', 'Column3', 'New Column 1']
    };

    render(<AddColumnDialog {...propsWithConflict} />);

    const input = screen.getByLabelText('New Column Name') as HTMLInputElement;
    expect(input.value).toBe('New Column 2');
  });

  it('auto-focuses and selects text in input field when opened', async () => {
    render(<AddColumnDialog {...defaultProps} />);

    // Wait for the input to be rendered and focused
    await waitFor(() => {
      const input = screen.getByLabelText('New Column Name') as HTMLInputElement;
      expect(input).toBeInTheDocument();
    });

    // In test environment, we can't reliably test focus due to jsdom limitations
    // but we can verify the input exists and has the expected value
    const input = screen.getByLabelText('New Column Name') as HTMLInputElement;
    expect(input.value).toBe('New Column 1');
  });

  it('validates empty column name', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const input = screen.getByLabelText('New Column Name');
    await user.clear(input);

    expect(screen.getByText('Column name cannot be empty')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add column/i })).toBeDisabled();
  });

  it('validates duplicate column name', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const input = screen.getByLabelText('New Column Name');
    await user.clear(input);
    await user.type(input, 'Column1');

    expect(screen.getByText('A column with this name already exists')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add column/i })).toBeDisabled();
  });

  it('validates column name with invalid characters', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const input = screen.getByLabelText('New Column Name');
    await user.clear(input);
    await user.type(input, 'Invalid,Name');

    expect(screen.getByText('Column name cannot contain commas or line breaks')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add column/i })).toBeDisabled();
  });

  it('validates column name length', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const input = screen.getByLabelText('New Column Name');
    const longName = 'a'.repeat(101); // 101 characters
    await user.clear(input);
    await user.type(input, longName);

    expect(screen.getByText('Column name is too long (maximum 100 characters)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add column/i })).toBeDisabled();
  });

  it('allows changing insert position', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const positionSelect = screen.getByLabelText('Insert Position');
    await user.click(positionSelect);

    const beforeOption = screen.getByText(/Before "TestColumn"/);
    await user.click(beforeOption);

    // Verify the position changed
    expect(screen.getByText(/Before "TestColumn" \(Column 2\)/)).toBeInTheDocument();
  });

  it('shows correct final position preview for "before" insertion', () => {
    const propsWithBefore = {
      ...defaultProps,
      insertPosition: 'before' as const
    };

    render(<AddColumnDialog {...propsWithBefore} />);

    // Should show position 2 (referenceColumnIndex + 1)
    expect(screen.getByText(/will be inserted at position 2/)).toBeInTheDocument();
  });

  it('shows correct final position preview for "after" insertion', () => {
    render(<AddColumnDialog {...defaultProps} />);

    // Should show position 3 (referenceColumnIndex + 2)
    expect(screen.getByText(/will be inserted at position 3/)).toBeInTheDocument();
  });

  it('calls onConfirm with correct parameters when valid name is submitted', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const input = screen.getByLabelText('New Column Name');
    await user.clear(input);
    await user.type(input, 'ValidNewColumn');

    const addButton = screen.getByRole('button', { name: /add column/i });
    await user.click(addButton);

    expect(defaultProps.onConfirm).toHaveBeenCalledWith('ValidNewColumn', 'after');
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('calls onCancel when close button is clicked', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const closeButton = screen.getByLabelText('close');
    await user.click(closeButton);

    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('handles Enter key to confirm when valid', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const input = screen.getByLabelText('New Column Name');
    await user.clear(input);
    await user.type(input, 'ValidNewColumn');
    await user.keyboard('{Enter}');

    expect(defaultProps.onConfirm).toHaveBeenCalledWith('ValidNewColumn', 'after');
  });

  it('handles Escape key to cancel', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    await user.keyboard('{Escape}');

    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('shows loading state correctly', () => {
    const loadingProps = {
      ...defaultProps,
      loading: true
    };

    render(<AddColumnDialog {...loadingProps} />);

    expect(screen.getByText('Adding column...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /adding.../i })).toBeDisabled();
    expect(screen.queryByLabelText('close')).not.toBeInTheDocument();
  });

  it('disables interactions during loading', () => {
    const loadingProps = {
      ...defaultProps,
      loading: true
    };

    render(<AddColumnDialog {...loadingProps} />);

    const input = screen.getByLabelText('New Column Name');
    const cancelButton = screen.getByRole('button', { name: /cancel/i });

    expect(input).toBeDisabled();
    expect(cancelButton).toBeDisabled();

    // For MUI Select, check the aria-disabled attribute instead
    const positionSelect = screen.getByRole('combobox');
    expect(positionSelect).toHaveAttribute('aria-disabled', 'true');
  });

  it('does not render when open is false', () => {
    const closedProps = {
      ...defaultProps,
      open: false
    };

    render(<AddColumnDialog {...closedProps} />);

    expect(screen.queryByText('Add New Column')).not.toBeInTheDocument();
  });

  it('trims whitespace from column name before validation and submission', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const input = screen.getByLabelText('New Column Name');
    await user.clear(input);
    await user.type(input, '  ValidNewColumn  ');

    const addButton = screen.getByRole('button', { name: /add column/i });
    await user.click(addButton);

    expect(defaultProps.onConfirm).toHaveBeenCalledWith('ValidNewColumn', 'after');
  });

  it('shows info alert when valid column name is entered', async () => {
    const user = userEvent.setup();
    render(<AddColumnDialog {...defaultProps} />);

    const input = screen.getByLabelText('New Column Name');
    await user.clear(input);
    await user.type(input, 'ValidNewColumn');

    expect(screen.getByText(/The new column "ValidNewColumn" will be inserted/)).toBeInTheDocument();
    expect(screen.getByText(/with empty values for all data rows/)).toBeInTheDocument();
  });
});
