/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SchemaChangesPanel } from '../../../components/metadata/schema-changes-panel';
import { SchemaAlignmentChangeDetail } from '../../../lib/types';

describe('SchemaChangesPanel', () => {
  const mockSchemaChanges: SchemaAlignmentChangeDetail[] = [
    {
      changeType: 'rename',
      originalColumn: 'old_name',
      newColumn: 'new_name',
      reason: 'Column "old_name" was renamed to "new_name"',
      rowCountAffected: 100
    },
    {
      changeType: 'add',
      newColumn: 'added_column',
      reason: 'Column "added_column" was added',
      rowCountAffected: 100
    },
    {
      changeType: 'remove',
      originalColumn: 'removed_column',
      reason: 'Column "removed_column" was removed',
      rowCountAffected: 100
    },
    {
      changeType: 'rename',
      originalColumn: 'another_old',
      newColumn: 'another_new',
      reason: 'Column "another_old" was renamed to "another_new"',
      rowCountAffected: 100
    },
  ];

  const defaultProps = {
    changes: mockSchemaChanges,
    onAcceptChange: jest.fn(),
    onRevertChange: jest.fn(),
    onApplyColumnRename: jest.fn(),
    onApplyColumnAddition: jest.fn(),
    onApplyColumnRemoval: jest.fn()
  };

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders schema changes correctly', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    // Component should render change cards
    expect(screen.getByText('old_name')).toBeInTheDocument();
    expect(screen.getByText('new_name')).toBeInTheDocument();
    expect(screen.getByText('added_column')).toBeInTheDocument();
    expect(screen.getByText('removed_column')).toBeInTheDocument();
  });

  it('displays all change cards', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    // Should render all 4 changes
    expect(screen.getByText('old_name')).toBeInTheDocument();
    expect(screen.getByText('added_column')).toBeInTheDocument();
    expect(screen.getByText('removed_column')).toBeInTheDocument();
    expect(screen.getByText('another_old')).toBeInTheDocument();
  });

  it('shows empty state when no changes exist', () => {
    render(<SchemaChangesPanel {...defaultProps} changes={[]} />);

    expect(screen.getByText('No Schema Changes')).toBeInTheDocument();
    expect(screen.getByText('Your data structure matches the target schema perfectly.')).toBeInTheDocument();
  });

  it('renders different change types with appropriate icons and colors', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    // Check that all column names are rendered
    expect(screen.getByText('old_name')).toBeInTheDocument();
    expect(screen.getByText('new_name')).toBeInTheDocument();
    expect(screen.getByText('added_column')).toBeInTheDocument();
    expect(screen.getByText('removed_column')).toBeInTheDocument();
    expect(screen.getByText('another_old')).toBeInTheDocument();
    expect(screen.getByText('another_new')).toBeInTheDocument();

    // Check that change type labels are rendered
    const renameLabels = screen.getAllByText('Rename');
    expect(renameLabels.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Add')).toBeInTheDocument();
    expect(screen.getByText('Remove')).toBeInTheDocument();
  });

  it('displays column names correctly for renamed columns', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    // Check original and new column names for renames
    expect(screen.getByText('old_name')).toBeInTheDocument();
    expect(screen.getByText('new_name')).toBeInTheDocument();
    expect(screen.getByText('another_old')).toBeInTheDocument();
    expect(screen.getByText('another_new')).toBeInTheDocument();
  });

  it('displays column names correctly for added columns', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    expect(screen.getByText('added_column')).toBeInTheDocument();
  });

  it('displays column names correctly for removed columns', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    expect(screen.getByText('removed_column')).toBeInTheDocument();
  });

  it('shows apply buttons for pending changes', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    // All changes should have Apply buttons when none are applied
    expect(screen.getAllByText('Apply Rename').length).toBeGreaterThan(0);
    expect(screen.getByText('Apply Addition')).toBeInTheDocument();
    expect(screen.getByText('Apply Removal')).toBeInTheDocument();
  });

  it('shows applied status when changes are marked as applied', () => {
    const appliedChangeIds = new Set(['rename-old_name-0']);

    render(<SchemaChangesPanel {...defaultProps} appliedChangeIds={appliedChangeIds} />);

    // Should show Applied status for the applied change
    expect(screen.getByText('Applied')).toBeInTheDocument();
  });

  it('shows revert button for applied changes', () => {
    const appliedChangeIds = new Set(['rename-old_name-0']);

    render(<SchemaChangesPanel {...defaultProps} appliedChangeIds={appliedChangeIds} />);

    // Should have Revert button for applied change
    const revertButtons = screen.getAllByText('Revert');
    expect(revertButtons.length).toBeGreaterThan(0);
  });

  it('calls onApplyColumnRename when Apply Rename button is clicked', async () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    const applyRenameButtons = screen.getAllByText('Apply Rename');
    fireEvent.click(applyRenameButtons[0]);

    await waitFor(() => {
      expect(defaultProps.onApplyColumnRename).toHaveBeenCalledWith('old_name', 'new_name');
    });
  });

  it('calls onRevertChange when revert button is clicked', async () => {
    const appliedChangeIds = new Set(['rename-old_name-0']);

    render(<SchemaChangesPanel {...defaultProps} appliedChangeIds={appliedChangeIds} />);

    const revertButtons = screen.getAllByText('Revert');
    fireEvent.click(revertButtons[0]);

    await waitFor(() => {
      expect(defaultProps.onRevertChange).toHaveBeenCalledWith('rename-old_name-0');
    });
  });

  it('shows bulk actions with Apply All button', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    // Should show Apply All button
    expect(screen.getByText('Apply All')).toBeInTheDocument();
  });

  it('shows Revert All button when changes are applied', async () => {
    const appliedChangeIds = new Set(['rename-old_name-0', 'add-added_column-1']);

    render(<SchemaChangesPanel {...defaultProps} appliedChangeIds={appliedChangeIds} />);

    expect(screen.getByText('Revert All')).toBeInTheDocument();
  });

  it('displays correct summary statistics', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    // Should show counts of change types
    expect(screen.getByText(/0\/4 applied/)).toBeInTheDocument();
    expect(screen.getByText(/2R/)).toBeInTheDocument(); // 2 renames
    expect(screen.getByText(/1A/)).toBeInTheDocument(); // 1 addition
    expect(screen.getByText(/1D/)).toBeInTheDocument(); // 1 deletion (remove)
  });

  it('shows Apply All button when all changes are pending', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    expect(screen.getByText('Apply All')).toBeInTheDocument();
  });

  it('does not show Apply button for applied changes', () => {
    const allAppliedIds = new Set([
      'rename-old_name-0',
      'add-added_column-1',
      'remove-removed_column-2',
      'rename-another_old-3'
    ]);

    render(<SchemaChangesPanel {...defaultProps} appliedChangeIds={allAppliedIds} />);

    expect(screen.queryByText('Apply')).not.toBeInTheDocument();
    expect(screen.getAllByText('Revert')).toHaveLength(4);
  });

  it('handles mixed change states correctly', () => {
    // Test with some applied and some pending changes
    const partiallyAppliedIds = new Set(['rename-old_name-0', 'add-added_column-1']);

    render(<SchemaChangesPanel {...defaultProps} appliedChangeIds={partiallyAppliedIds} />);

    // Should have Apply buttons for pending changes (remove and second rename)
    expect(screen.getByText('Apply Removal')).toBeInTheDocument();
    expect(screen.getAllByText('Apply Rename').length).toBeGreaterThanOrEqual(1);

    // Should have Revert buttons for applied changes
    const revertButtons = screen.getAllByText('Revert');
    expect(revertButtons.length).toBeGreaterThan(0);

    // Should show both bulk action buttons
    expect(screen.getByText('Apply All')).toBeInTheDocument();
    expect(screen.getByText('Revert All')).toBeInTheDocument();
  });

  it('renders with proper Material UI styling and accessibility', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    // Check that Apply buttons are rendered with proper labels
    expect(screen.getAllByText('Apply Rename').length).toBeGreaterThan(0);
    expect(screen.getByText('Apply Addition')).toBeInTheDocument();
    expect(screen.getByText('Apply Removal')).toBeInTheDocument();

    // Check that cards with changes are rendered
    expect(screen.getByText('old_name')).toBeInTheDocument();
    expect(screen.getByText('new_name')).toBeInTheDocument();
  });

  it('maintains proper component structure for different change types', () => {
    render(<SchemaChangesPanel {...defaultProps} />);

    // Each change should render its column names
    const columnNames = [
      'old_name',
      'new_name',
      'added_column',
      'removed_column',
      'another_old',
      'another_new'
    ];

    columnNames.forEach(name => {
      expect(screen.getByText(name)).toBeInTheDocument();
    });
  });
});
