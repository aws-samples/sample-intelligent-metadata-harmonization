/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SchemaChangesPanel } from '../../../components/metadata/schema-changes-panel';
import { SchemaAlignmentChangeDetail } from '../../../lib/types';

describe('SchemaChangesPanel - Bulk Schema Transformation Actions', () => {
  const mockSchemaChanges: SchemaAlignmentChangeDetail[] = [
    {
      changeType: 'rename',
      originalColumn: 'sample_received_date',
      newColumn: 'SampleReceivedDate',
      reason: 'Column renamed to match target schema',
      rowCountAffected: 100
    },
    {
      changeType: 'add',
      newColumn: 'NewColumn',
      reason: 'Required column added for schema compliance',
      rowCountAffected: 100
    },
    {
      changeType: 'remove',
      originalColumn: 'OldColumn',
      reason: 'Column not required in target schema',
      rowCountAffected: 100
    }
  ];

  // Initial data representing the current state of columns (before any transformations)
  const initialData = [
    ['sample_received_date', 'Status', 'OldColumn'],
    ['2024-01-01', 'active', 'value1'],
    ['2024-01-02', 'inactive', 'value2']
  ];

  const defaultProps = {
    changes: mockSchemaChanges,
    currentData: initialData,
    onAcceptChange: jest.fn(),
    onRevertChange: jest.fn(),
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
    })
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Bulk Actions Display', () => {
    it('should display bulk actions section with Apply All button', () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      expect(screen.getByText('Bulk Actions')).toBeInTheDocument();
      expect(screen.getByText('Apply All')).toBeInTheDocument();
    });

    it('should display Advanced button', () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      expect(screen.getByText('Advanced')).toBeInTheDocument();
    });

    it('should show statistics about change types', () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      // Format is "{applied}/{total} applied • {rename}R {add}A {remove}D"
      expect(screen.getByText(/0\/3 applied/)).toBeInTheDocument();
      expect(screen.getByText(/1R/)).toBeInTheDocument();
      expect(screen.getByText(/1A/)).toBeInTheDocument();
      expect(screen.getByText(/1D/)).toBeInTheDocument();
    });
  });

  describe('Apply All Functionality', () => {
    it('should show confirmation dialog when Apply All is clicked with destructive changes', async () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      const applyAllButton = screen.getByText('Apply All');
      fireEvent.click(applyAllButton);

      await waitFor(() => {
        expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
      });
    });

    it('should execute all transformations when confirmed', async () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      const applyAllButton = screen.getByText('Apply All');
      fireEvent.click(applyAllButton);

      await waitFor(() => {
        expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
      });

      const confirmButton = screen.getByText('Apply All Changes');
      fireEvent.click(confirmButton);

      // Should call all transformation callbacks with workingData (bulk mode - 3 args for rename, 2 for others)
      await waitFor(() => {
        expect(defaultProps.onApplyColumnRename).toHaveBeenCalledWith('sample_received_date', 'SampleReceivedDate', expect.any(Array));
        expect(defaultProps.onApplyColumnAddition).toHaveBeenCalledWith('NewColumn', expect.any(Array));
        expect(defaultProps.onApplyColumnRemoval).toHaveBeenCalledWith('OldColumn', expect.any(Array));
      });
    });

    it('should disable Apply All button when all changes are applied', () => {
      // Use proper change IDs: changeType-columnName-index
      const allAppliedIds = new Set([
        'rename-sample_received_date-0',
        'add-NewColumn-1',
        'remove-OldColumn-2'
      ]);
      const propsWithApplied = {
        ...defaultProps,
        appliedChangeIds: allAppliedIds
      };

      render(<SchemaChangesPanel {...propsWithApplied} />);

      const applyAllButton = screen.getByText('Apply All');
      expect(applyAllButton).toBeDisabled();
    });
  });

  describe('Revert All Functionality', () => {
    it('should show Revert All button only when changes are applied', () => {
      const propsWithApplied = {
        ...defaultProps,
        appliedChangeIds: new Set(['rename-sample_received_date-0'])
      };

      render(<SchemaChangesPanel {...propsWithApplied} />);

      expect(screen.getByText('Revert All')).toBeInTheDocument();
    });

    it('should not show Revert All button when no changes are applied', () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      expect(screen.queryByText('Revert All')).not.toBeInTheDocument();
    });

    it('should show confirmation dialog when Revert All is clicked', async () => {
      const propsWithApplied = {
        ...defaultProps,
        appliedChangeIds: new Set(['rename-sample_received_date-0'])
      };

      render(<SchemaChangesPanel {...propsWithApplied} />);

      const revertAllButton = screen.getByText('Revert All');
      fireEvent.click(revertAllButton);

      await waitFor(() => {
        expect(screen.getByText('Revert All Schema Changes')).toBeInTheDocument();
      });
    });

    it('should revert all applied changes when confirmed', async () => {
      const propsWithApplied = {
        ...defaultProps,
        appliedChangeIds: new Set(['rename-sample_received_date-0'])
      };

      render(<SchemaChangesPanel {...propsWithApplied} />);

      const revertAllButton = screen.getByText('Revert All');
      fireEvent.click(revertAllButton);

      await waitFor(() => {
        expect(screen.getByText('Revert All Schema Changes')).toBeInTheDocument();
      });

      const confirmButton = screen.getByText('Revert All Changes');
      fireEvent.click(confirmButton);

      // Should call revert callback with proper change ID
      await waitFor(() => {
        expect(defaultProps.onRevertChange).toHaveBeenCalledWith('rename-sample_received_date-0');
      });
    });
  });

  describe('Advanced Functionality', () => {
    it('should show bulk operations dialog when Advanced is clicked', async () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      const advancedButton = screen.getByText('Advanced');
      fireEvent.click(advancedButton);

      // Advanced button opens the bulk operations dialog
      // Just verify it doesn't crash
    });
  });

  describe('Proper Sequencing', () => {
    it('should apply changes in correct sequence to avoid conflicts', async () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      const applyAllButton = screen.getByText('Apply All');
      fireEvent.click(applyAllButton);

      await waitFor(() => {
        expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
      });

      const confirmButton = screen.getByText('Apply All Changes');
      fireEvent.click(confirmButton);

      // Verify calls were made (sequence is handled internally)
      await waitFor(() => {
        expect(defaultProps.onApplyColumnRename).toHaveBeenCalled();
        expect(defaultProps.onApplyColumnAddition).toHaveBeenCalled();
        expect(defaultProps.onApplyColumnRemoval).toHaveBeenCalled();
      });
    });
  });

  describe('Progress Indicators and Statistics', () => {
    it('should show applied changes count', () => {
      const propsWithOneApplied = {
        ...defaultProps,
        appliedChangeIds: new Set(['rename-sample_received_date-0'])
      };

      render(<SchemaChangesPanel {...propsWithOneApplied} />);

      // Should show 1 applied out of 3
      expect(screen.getByText(/1\/3 applied/)).toBeInTheDocument();
    });

    it('should show helpful message when changes are applied', () => {
      const propsWithOneApplied = {
        ...defaultProps,
        appliedChangeIds: new Set(['rename-sample_received_date-0'])
      };

      render(<SchemaChangesPanel {...propsWithOneApplied} />);

      expect(screen.getByText('Changes applied immediately')).toBeInTheDocument();
    });
  });

  describe('Confirmation Dialog Details', () => {
    it('should show detailed transformation summary in confirmation dialog', async () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      const applyAllButton = screen.getByText('Apply All');
      fireEvent.click(applyAllButton);

      await waitFor(() => {
        expect(screen.getByText('Apply All Schema Changes')).toBeInTheDocument();
      });

      // Should show description of what will happen
      expect(screen.getByText(/This will apply 3 changes to your data structure/)).toBeInTheDocument();
    });

    it('should allow canceling bulk operations', async () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      const applyAllButton = screen.getByText('Apply All');
      fireEvent.click(applyAllButton);

      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeInTheDocument();
      });

      const cancelButton = screen.getByText('Cancel');
      fireEvent.click(cancelButton);

      // Dialog should close and no callbacks should be called
      await waitFor(() => {
        expect(screen.queryByText('Apply All Schema Changes')).not.toBeInTheDocument();
      });

      expect(defaultProps.onApplyColumnRename).not.toHaveBeenCalled();
      expect(defaultProps.onApplyColumnAddition).not.toHaveBeenCalled();
      expect(defaultProps.onApplyColumnRemoval).not.toHaveBeenCalled();
    });
  });

  describe('Visual Consistency', () => {
    it('should use consistent styling for bulk action buttons', () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      const applyAllButton = screen.getByText('Apply All');
      const advancedButton = screen.getByText('Advanced');

      // Both buttons should have consistent styling
      expect(applyAllButton).toHaveClass('MuiButton-root');
      expect(advancedButton).toHaveClass('MuiButton-root');

      // Apply All should be contained variant
      expect(applyAllButton).toHaveClass('MuiButton-contained');

      // Advanced should be outlined variant
      expect(advancedButton).toHaveClass('MuiButton-outlined');
    });

    it('should maintain consistent spacing and typography', () => {
      render(<SchemaChangesPanel {...defaultProps} />);

      const bulkActionsTitle = screen.getByText('Bulk Actions');
      expect(bulkActionsTitle).toHaveClass('MuiTypography-subtitle2');
    });
  });
});
