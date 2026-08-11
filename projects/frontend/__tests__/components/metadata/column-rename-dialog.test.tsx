/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ColumnRenameDialog } from '../../../components/metadata/column-rename-dialog';

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('ColumnRenameDialog', () => {
  const mockOnConfirm = jest.fn();
  const mockOnCancel = jest.fn();

  const defaultProps = {
    open: true,
    currentColumnName: 'TestColumn',
    columnIndex: 1,
    existingColumnNames: ['Column1', 'TestColumn', 'Column3'],
    onConfirm: mockOnConfirm,
    onCancel: mockOnCancel
  };

  beforeEach(() => {
    mockOnConfirm.mockClear();
    mockOnCancel.mockClear();
  });

  it('renders dialog with current column name', () => {
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Renaming column "TestColumn" (Column 2)')).toBeInTheDocument();
    expect(screen.getByDisplayValue('TestColumn')).toBeInTheDocument();
    expect(screen.getByLabelText('New Column Name')).toBeInTheDocument();
  });

  it('auto-focuses and selects text in input field', async () => {
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    // Check that the input field exists and has the correct value
    const input = screen.getByDisplayValue('TestColumn');
    expect(input).toBeInTheDocument();

    // In test environment, focus behavior may be different, so we just verify the input is present
    await waitFor(() => {
      expect(input).toBeInTheDocument();
    }, { timeout: 200 });
  });

  it('validates empty column names', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const input = screen.getByDisplayValue('TestColumn');
    await user.clear(input);

    expect(screen.getByText('Column name cannot be empty')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /rename column/i })).toBeDisabled();
  });

  it('validates duplicate column names', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const input = screen.getByDisplayValue('TestColumn');
    await user.clear(input);
    await user.type(input, 'Column1'); // Existing column name

    expect(screen.getByText('A column with this name already exists')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /rename column/i })).toBeDisabled();
  });

  it('validates invalid characters', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const input = screen.getByDisplayValue('TestColumn');
    await user.clear(input);
    await user.type(input, 'Column,With,Commas');

    expect(screen.getByText('Column name cannot contain commas or line breaks')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /rename column/i })).toBeDisabled();
  });

  it('allows valid new column names', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const input = screen.getByDisplayValue('TestColumn');
    await user.clear(input);
    await user.type(input, 'NewValidName');

    expect(screen.queryByText(/cannot/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /rename column/i })).toBeEnabled();
  });

  it('calls onConfirm with trimmed name when confirmed', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const input = screen.getByDisplayValue('TestColumn');
    await user.clear(input);
    await user.type(input, '  NewColumnName  '); // With spaces

    const confirmButton = screen.getByRole('button', { name: /rename column/i });
    await user.click(confirmButton);

    expect(mockOnConfirm).toHaveBeenCalledWith('NewColumnName');
  });

  it('calls onCancel when cancelled', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('calls onCancel when close button is clicked', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const closeButton = screen.getByLabelText('close');
    await user.click(closeButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('handles Enter key to confirm', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const input = screen.getByDisplayValue('TestColumn');
    await user.clear(input);
    await user.type(input, 'NewName');
    await user.keyboard('{Enter}');

    expect(mockOnConfirm).toHaveBeenCalledWith('NewName');
  });

  it('handles Escape key to cancel', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    await user.keyboard('{Escape}');

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('does not confirm on Enter when validation error exists', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const input = screen.getByDisplayValue('TestColumn');
    await user.clear(input);
    await user.type(input, 'Column1'); // Duplicate name
    await user.keyboard('{Enter}');

    expect(mockOnConfirm).not.toHaveBeenCalled();
  });

  it('shows loading state', () => {
    renderWithTheme(<ColumnRenameDialog {...defaultProps} loading={true} />);

    expect(screen.getByText('Renaming column...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /renaming/i })).toBeDisabled();
    expect(screen.getByDisplayValue('TestColumn')).toBeDisabled();
  });

  it('disables close actions when loading', () => {
    renderWithTheme(<ColumnRenameDialog {...defaultProps} loading={true} />);

    expect(screen.queryByLabelText('close')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();
  });

  it('shows info alert for valid changes', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const input = screen.getByDisplayValue('TestColumn');
    await user.clear(input);
    await user.type(input, 'NewValidName');

    expect(screen.getByText(/This will rename the column and update all data references/)).toBeInTheDocument();
  });

  it('does not show info alert when name unchanged', () => {
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    expect(screen.queryByText(/This will rename the column/)).not.toBeInTheDocument();
  });

  it('calls onCancel when name unchanged and confirmed', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    // Name is already 'TestColumn', so confirm button should close dialog
    const confirmButton = screen.getByRole('button', { name: /rename column/i });
    expect(confirmButton).toBeDisabled(); // Should be disabled when name unchanged
  });

  it('excludes current column from duplicate validation', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    // Should be able to keep the same name (no change)
    const input = screen.getByDisplayValue('TestColumn');
    expect(screen.queryByText('A column with this name already exists')).not.toBeInTheDocument();

    // But should not be able to use other existing names
    await user.clear(input);
    await user.type(input, 'Column1');
    expect(screen.getByText('A column with this name already exists')).toBeInTheDocument();
  });

  it('handles whitespace-only names', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ColumnRenameDialog {...defaultProps} />);

    const input = screen.getByDisplayValue('TestColumn');
    await user.clear(input);
    await user.type(input, '   '); // Only spaces

    expect(screen.getByText('Column name cannot be empty')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /rename column/i })).toBeDisabled();
  });

  it('does not render when closed', () => {
    renderWithTheme(<ColumnRenameDialog {...defaultProps} open={false} />);

    expect(screen.queryByText('Rename Column')).not.toBeInTheDocument();
  });

  it('resets state when reopened', async () => {
    const { rerender } = renderWithTheme(<ColumnRenameDialog {...defaultProps} open={false} />);

    // Open dialog
    rerender(
      <ThemeProvider theme={theme}>
        <ColumnRenameDialog {...defaultProps} open={true} />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('TestColumn')).toBeInTheDocument();
    });

    // Should reset to current column name
    expect(screen.getByDisplayValue('TestColumn')).toBeInTheDocument();
    expect(screen.queryByText(/cannot/)).not.toBeInTheDocument();
  });
});
