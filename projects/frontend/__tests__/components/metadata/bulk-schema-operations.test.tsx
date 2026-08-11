/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SchemaChangesPanel } from '../../../components/metadata/schema-changes-panel';
import { SchemaAlignmentChangeDetail } from '../../../lib/types';

describe('SchemaChangesPanel - Bulk Operations', () => {
  const mockChanges: SchemaAlignmentChangeDetail[] = [
    {
      changeType: 'rename',
      originalColumn: 'old_name',
      newColumn: 'new_name',
      reason: 'Column renamed for schema alignment',
      rowCountAffected: 100
    },
    {
      changeType: 'add',
      newColumn: 'added_column',
      reason: 'Column added for schema compliance',
      rowCountAffected: 100
    },
    {
      changeType: 'remove',
      originalColumn: 'removed_column',
      reason: 'Column removed as not required',
      rowCountAffected: 100
    }
  ];

  // Initial data representing the current state of columns (before any transformations)
  const initialData = [
    ['old_name', 'existing_field', 'removed_column'],
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
    onRevertChange: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Bulk Apply Operations', () => {
    it('should call individual transformation callbacks when applying all changes', async () => {
      render(
        <SchemaChangesPanel
          changes={mockChanges}
          currentData={initialData}
          {...mockCallbacks}
        />
      );

      // Find and click the "Apply All" button
      const applyAllButton = screen.getByRole('button', { name: /apply all/i });
      expect(applyAllButton).toBeInTheDocument();

      fireEvent.click(applyAllButton);

      // Wait for confirmation dialog (has destructive changes)
      await waitFor(() => {
        expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
      });

      // Confirm the operation
      const confirmButton = screen.getByText('Apply All Changes');
      fireEvent.click(confirmButton);

      // Wait for the bulk operation to complete
      await waitFor(() => {
        // Verify that individual transformation callbacks were called with workingData (bulk mode)
        expect(mockCallbacks.onApplyColumnRename).toHaveBeenCalledWith('old_name', 'new_name', expect.any(Array));
        expect(mockCallbacks.onApplyColumnAddition).toHaveBeenCalledWith('added_column', expect.any(Array));
        expect(mockCallbacks.onApplyColumnRemoval).toHaveBeenCalledWith('removed_column', expect.any(Array));
      }, { timeout: 10000 });
    });

    it('should handle bulk apply with missing callbacks gracefully', async () => {
      const incompleteCallbacks = {
        ...mockCallbacks,
        onApplyColumnRename: undefined, // Missing callback
      };

      // Mock console to capture the error message
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});

      render(
        <SchemaChangesPanel
          changes={mockChanges}
          currentData={initialData}
          {...incompleteCallbacks}
        />
      );

      const applyAllButton = screen.getByRole('button', { name: /apply all/i });
      fireEvent.click(applyAllButton);

      // Should detect missing callbacks and not proceed
      // The component logs an error and aborts the operation
      await waitFor(() => {
        // Verify error was logged about missing callbacks
        expect(consoleSpy).toHaveBeenCalled();
        const errorCalls = consoleSpy.mock.calls.filter(call =>
          call[0]?.includes('Missing') || call[0]?.includes('missing')
        );
        expect(errorCalls.length).toBeGreaterThan(0);
      });

      // The operation should not proceed, so callbacks should not be called
      expect(mockCallbacks.onApplyColumnAddition).not.toHaveBeenCalled();
      expect(mockCallbacks.onApplyColumnRemoval).not.toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it('should show confirmation dialog for destructive changes', async () => {
      const destructiveChanges: SchemaAlignmentChangeDetail[] = [
        {
          changeType: 'remove',
          originalColumn: 'important_column',
          reason: 'Column will be removed',
          rowCountAffected: 1000
        }
      ];

      render(
        <SchemaChangesPanel
          changes={destructiveChanges}
          currentData={initialData}
          {...mockCallbacks}
        />
      );

      const applyAllButton = screen.getByRole('button', { name: /apply all/i });
      fireEvent.click(applyAllButton);

      // Should show confirmation dialog for destructive changes
      await waitFor(() => {
        expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
      }, { timeout: 3000 });
    });
  });

  describe('Bulk Revert Operations', () => {
    it('should call revert callback when reverting all changes', async () => {
      const appliedChangeIds = new Set(['rename-old_name-0', 'add-added_column-1']);

      render(
        <SchemaChangesPanel
          changes={mockChanges}
          currentData={initialData}
          appliedChangeIds={appliedChangeIds}
          {...mockCallbacks}
        />
      );

      const revertAllButton = screen.getByRole('button', { name: /revert all/i });
      expect(revertAllButton).toBeInTheDocument();

      fireEvent.click(revertAllButton);

      // Should show confirmation dialog first
      await waitFor(() => {
        expect(screen.getByText('Revert All Schema Changes')).toBeInTheDocument();
      });

      // Confirm the revert operation
      const confirmButton = screen.getByText('Revert All Changes');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        // Verify that revert callbacks were called for applied changes
        expect(mockCallbacks.onRevertChange).toHaveBeenCalledWith('rename-old_name-0');
        expect(mockCallbacks.onRevertChange).toHaveBeenCalledWith('add-added_column-1');
      }, { timeout: 5000 });
    });

    it('should handle empty applied changes gracefully', async () => {
      render(
        <SchemaChangesPanel
          changes={mockChanges}
          appliedChangeIds={new Set()} // No applied changes
          {...mockCallbacks}
        />
      );

      // Should not render the "Revert All" button when no changes are applied
      expect(screen.queryByRole('button', { name: /revert all/i })).not.toBeInTheDocument();

      // Should not make any revert calls
      expect(mockCallbacks.onRevertChange).not.toHaveBeenCalled();
    });
  });

  describe('Individual Operations', () => {
    it('should apply individual changes correctly', async () => {
      render(
        <SchemaChangesPanel
          changes={mockChanges}
          currentData={initialData}
          {...mockCallbacks}
        />
      );

      // Find and click individual apply buttons
      const applyButtons = screen.getAllByRole('button', { name: /apply/i });
      expect(applyButtons.length).toBeGreaterThan(0);

      // Click the first apply button (rename operation)
      fireEvent.click(applyButtons[0]);

      await waitFor(() => {
        expect(mockCallbacks.onApplyColumnRename).toHaveBeenCalledWith('old_name', 'new_name');
      });
    });

    it('should revert individual changes correctly', async () => {
      const appliedChangeIds = new Set(['rename-old_name-0']);

      render(
        <SchemaChangesPanel
          changes={mockChanges}
          currentData={initialData}
          appliedChangeIds={appliedChangeIds}
          {...mockCallbacks}
        />
      );

      // Find and click the specific individual revert button (not the bulk one)
      const revertButtons = screen.getAllByRole('button', { name: /revert/i });
      // The first one should be the individual revert button
      const individualRevertButton = revertButtons.find(button =>
        button.textContent?.includes('Revert') && !button.textContent?.includes('All')
      );

      expect(individualRevertButton).toBeInTheDocument();
      fireEvent.click(individualRevertButton!);

      await waitFor(() => {
        expect(mockCallbacks.onRevertChange).toHaveBeenCalledWith('rename-old_name-0');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle transformation errors gracefully', async () => {
      const errorCallbacks = {
        ...mockCallbacks,
        onApplyColumnRename: jest.fn().mockImplementation(() => {
          throw new Error('Transformation failed');
        })
      };

      render(
        <SchemaChangesPanel
          changes={mockChanges}
          currentData={initialData}
          {...errorCallbacks}
        />
      );

      const applyAllButton = screen.getByRole('button', { name: /apply all/i });
      fireEvent.click(applyAllButton);

      // Confirm dialog that appears due to remove operation
      await waitFor(() => {
        expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
      }, { timeout: 3000 });

      const confirmButton = screen.getByText('Apply All Changes');
      fireEvent.click(confirmButton);

      // Should handle errors and continue with other operations
      await waitFor(() => {
        expect(errorCallbacks.onApplyColumnAddition).toHaveBeenCalledWith('added_column', expect.any(Array));
        expect(errorCallbacks.onApplyColumnRemoval).toHaveBeenCalledWith('removed_column', expect.any(Array));
      }, { timeout: 5000 });
    });
  });
});
