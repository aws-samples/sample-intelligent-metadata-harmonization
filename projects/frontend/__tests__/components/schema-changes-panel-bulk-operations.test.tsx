/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SchemaChangesPanel } from '../../components/metadata/schema-changes-panel';
import { SchemaAlignmentChangeDetail } from '../../lib/types';

// Mock Material-UI components that might cause issues in tests
jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  Dialog: ({ children, open }: any) => open ? <div data-testid="dialog">{children}</div> : null,
}));

describe('SchemaChangesPanel - Bulk Operations', () => {
  const mockChanges: SchemaAlignmentChangeDetail[] = [
    {
      changeType: 'rename',
      originalColumn: 'old_name',
      newColumn: 'new_name',
      reason: 'Column name standardization',
      rowCountAffected: 100
    },
    {
      changeType: 'add',
      newColumn: 'additional_field',
      reason: 'Required field missing',
      rowCountAffected: 100
    },
    {
      changeType: 'remove',
      originalColumn: 'deprecated_field',
      reason: 'Field no longer needed',
      rowCountAffected: 100
    }
  ];

  // Initial data representing the current state of columns (before any transformations)
  const initialData = [
    ['old_name', 'existing_field', 'deprecated_field'],
    ['value1', 'data1', 'old_data1'],
    ['value2', 'data2', 'old_data2']
  ];

  const mockCallbacks = {
    onApplyColumnRename: jest.fn((originalColumn: string, newColumn: string, workingData?: string[][]) => {
      if (workingData) {
        // Bulk mode: return updated data with renamed column
        const result = workingData.map(row => [...row]);
        const colIndex = result[0].indexOf(originalColumn);
        if (colIndex !== -1) {
          result[0][colIndex] = newColumn;
        }
        return result;
      }
    }),
    onApplyColumnAddition: jest.fn((newColumn: string, workingData?: string[][]) => {
      if (workingData) {
        // Bulk mode: return updated data with added column
        return workingData.map(row => [...row, '']);
      }
    }),
    onApplyColumnRemoval: jest.fn((columnName: string, workingData?: string[][]) => {
      if (workingData) {
        // Bulk mode: return updated data with removed column
        const colIndex = workingData[0].indexOf(columnName);
        if (colIndex !== -1) {
          return workingData.map(row => row.filter((_, i) => i !== colIndex));
        }
        return workingData;
      }
    }),
    onAcceptChange: jest.fn(),
    onRevertChange: jest.fn(),
    getChangeId: jest.fn((change, index) => `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`)
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render bulk operation buttons', () => {
    render(
      <SchemaChangesPanel
        changes={mockChanges}
        currentData={initialData}
        {...mockCallbacks}
      />
    );

    expect(screen.getByText('Apply All')).toBeInTheDocument();
    expect(screen.getByText('Advanced')).toBeInTheDocument();
  });

  // Note: onApplyAllChanges and onRevertAllChanges props don't exist in the component
  // The component always uses its internal transformation manager
  // These tests have been removed as they were testing non-existent functionality

  it('should fall back to local implementation when parent callbacks not provided', async () => {
    // Use non-destructive changes to avoid confirmation dialog
    const nonDestructiveChanges: SchemaAlignmentChangeDetail[] = [
      {
        changeType: 'rename',
        originalColumn: 'old_name',
        newColumn: 'new_name',
        reason: 'Column name standardization',
        rowCountAffected: 100
      },
      {
        changeType: 'add',
        newColumn: 'additional_field',
        reason: 'Required field missing',
        rowCountAffected: 100
      }
    ];

    const localCallbacks = {
      ...mockCallbacks,
      onApplyAllChanges: undefined, // Remove parent callback
      onRevertAllChanges: undefined
    };

    render(
      <SchemaChangesPanel
        changes={nonDestructiveChanges}
        currentData={initialData}
        {...localCallbacks}
      />
    );

    const applyAllButton = screen.getByText('Apply All');
    fireEvent.click(applyAllButton);

    // Should call individual transformation methods with workingData for bulk operations
    await waitFor(() => {
      expect(mockCallbacks.onApplyColumnRename).toHaveBeenCalledWith('old_name', 'new_name', expect.any(Array));
      expect(mockCallbacks.onApplyColumnAddition).toHaveBeenCalledWith('additional_field', expect.any(Array));
    });
  });

  it('should apply changes in correct sequence (renames, adds, removes)', async () => {
    const localCallbacks = {
      ...mockCallbacks,
      onApplyAllChanges: undefined // Remove parent callback to test local implementation
    };

    render(
      <SchemaChangesPanel
        changes={mockChanges}
        currentData={initialData}
        {...localCallbacks}
      />
    );

    const applyAllButton = screen.getByText('Apply All');
    fireEvent.click(applyAllButton);

    // Should show confirmation dialog due to destructive changes
    await waitFor(() => {
      expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
    });

    // Confirm the bulk operation - find the confirmation button in the dialog
    const confirmButton = screen.getByText('Apply All Changes');
    fireEvent.click(confirmButton);

    await waitFor(() => {
      // Verify all methods were called
      expect(mockCallbacks.onApplyColumnRename).toHaveBeenCalledTimes(1);
      expect(mockCallbacks.onApplyColumnAddition).toHaveBeenCalledTimes(1);
      expect(mockCallbacks.onApplyColumnRemoval).toHaveBeenCalledTimes(1);
    });

    // Verify the sequence by checking call order
    const callOrder = [
      mockCallbacks.onApplyColumnRename.mock.invocationCallOrder[0],
      mockCallbacks.onApplyColumnAddition.mock.invocationCallOrder[0],
      mockCallbacks.onApplyColumnRemoval.mock.invocationCallOrder[0]
    ];

    // Should be in ascending order (renames first, then adds, then removes)
    expect(callOrder[0]).toBeLessThan(callOrder[1]);
    expect(callOrder[1]).toBeLessThan(callOrder[2]);
  });

  it('should show confirmation dialog for destructive bulk operations', async () => {
    const destructiveChanges = [
      {
        changeType: 'remove',
        originalColumn: 'field1',
        reason: 'Not needed',
        rowCountAffected: 50
      },
      {
        changeType: 'remove',
        originalColumn: 'field2',
        reason: 'Deprecated',
        rowCountAffected: 50
      }
    ];

    const localCallbacks = {
      ...mockCallbacks,
      onApplyAllChanges: undefined // Remove parent callback to test local implementation
    };

    render(
      <SchemaChangesPanel
        changes={destructiveChanges}
        currentData={initialData}
        {...localCallbacks}
      />
    );

    const applyAllButton = screen.getByText('Apply All');
    fireEvent.click(applyAllButton);

    // Should show confirmation dialog for destructive changes
    await waitFor(() => {
      expect(screen.getByTestId('dialog')).toBeInTheDocument();
      expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
    });
  });

  it('should handle errors in bulk operations gracefully', async () => {
    const errorCallbacks = {
      ...mockCallbacks,
      onApplyAllChanges: undefined,
      onApplyColumnRename: jest.fn(() => { throw new Error('Rename failed'); }),
      onApplyColumnAddition: jest.fn(),
      onApplyColumnRemoval: jest.fn()
    };

    // Mock console.error to avoid test output noise
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <SchemaChangesPanel
        changes={mockChanges}
        currentData={initialData}
        {...errorCallbacks}
      />
    );

    const applyAllButton = screen.getByText('Apply All');
    fireEvent.click(applyAllButton);

    // Should show confirmation dialog due to destructive changes
    await waitFor(() => {
      expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
    });

    // Confirm the bulk operation - find the confirmation button in the dialog
    const confirmButton = screen.getByText('Apply All Changes');
    fireEvent.click(confirmButton);

    await waitFor(() => {
      // Should still call other methods even if one fails
      expect(errorCallbacks.onApplyColumnRename).toHaveBeenCalledTimes(1);
      expect(errorCallbacks.onApplyColumnAddition).toHaveBeenCalledTimes(1);
      expect(errorCallbacks.onApplyColumnRemoval).toHaveBeenCalledTimes(1);
    });

    // Should log the error (the actual error format is different - the component logs transformation errors)
    expect(consoleSpy).toHaveBeenCalled();
    // Verify error was logged (format varies based on where the error is caught)
    const errorCalls = consoleSpy.mock.calls.filter(call =>
      call[0]?.includes('Failed') || call[0]?.includes('failed') || call[0]?.includes('❌')
    );
    expect(errorCalls.length).toBeGreaterThan(0);

    consoleSpy.mockRestore();
  });

  it('should update statistics correctly after bulk operations', () => {
    const appliedChangeIds = new Set(['rename-old_name-0']);

    render(
      <SchemaChangesPanel
        changes={mockChanges}
        currentData={initialData}
        appliedChangeIds={appliedChangeIds}
        {...mockCallbacks}
      />
    );

    // Should show correct statistics - format is "{applied}/{total} applied • {rename}R {add}A {remove}D"
    expect(screen.getByText(/1\/3 applied/)).toBeInTheDocument();
    expect(screen.getByText(/1R/)).toBeInTheDocument();
    expect(screen.getByText(/1A/)).toBeInTheDocument();
    expect(screen.getByText(/1D/)).toBeInTheDocument();
  });

  it('should disable Apply All button when all changes are applied', () => {
    const allAppliedIds = new Set([
      'rename-old_name-0',
      'add-additional_field-1',
      'remove-deprecated_field-2'
    ]);

    render(
      <SchemaChangesPanel
        changes={mockChanges}
        appliedChangeIds={allAppliedIds}
        {...mockCallbacks}
      />
    );

    const applyAllButton = screen.getByText('Apply All');
    expect(applyAllButton).toBeDisabled();
  });
});
