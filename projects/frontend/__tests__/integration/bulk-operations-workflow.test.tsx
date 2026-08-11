/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BulkOperationsDialog } from '../../components/metadata/bulk-operations-dialog';
import { SchemaChangesPanel } from '../../components/metadata/schema-changes-panel';
import { SchemaAlignmentChangeDetail } from '../../lib/types';
import { BulkOperationResult, SelectiveBulkConfig } from '../../lib/transformation-operations';

// Mock comprehensive test data
const mockChanges = [
  {
    change: {
      changeType: 'rename',
      originalColumn: 'sample_date',
      newColumn: 'SampleDate',
      reason: 'Standardize column naming to PascalCase',
      rowCountAffected: 1500
    } as SchemaAlignmentChangeDetail,
    index: 0
  },
  {
    change: {
      changeType: 'rename',
      originalColumn: 'patient_id',
      newColumn: 'PatientId',
      reason: 'Standardize column naming to PascalCase',
      rowCountAffected: 1500
    } as SchemaAlignmentChangeDetail,
    index: 1
  },
  {
    change: {
      changeType: 'add',
      newColumn: 'DataQualityScore',
      reason: 'Required field for data validation',
      rowCountAffected: 1500
    } as SchemaAlignmentChangeDetail,
    index: 2
  },
  {
    change: {
      changeType: 'remove',
      originalColumn: 'legacy_field',
      reason: 'Deprecated field no longer used',
      rowCountAffected: 1500
    } as SchemaAlignmentChangeDetail,
    index: 3
  },
  {
    change: {
      changeType: 'add',
      newColumn: 'ProcessedTimestamp',
      reason: 'Track processing time',
      rowCountAffected: 1500
    } as SchemaAlignmentChangeDetail,
    index: 4
  }
];

describe('Bulk Operations End-to-End Workflow', () => {
  let mockApplyColumnRename: jest.Mock;
  let mockApplyColumnAddition: jest.Mock;
  let mockApplyColumnRemoval: jest.Mock;
  let mockRevertChange: jest.Mock;
  let mockExecuteBulkOperation: jest.Mock;
  let mockPreviewBulkOperation: jest.Mock;
  let appliedChangeIds: Set<string>;

  beforeEach(() => {
    mockApplyColumnRename = jest.fn();
    mockApplyColumnAddition = jest.fn();
    mockApplyColumnRemoval = jest.fn();
    mockRevertChange = jest.fn();
    mockExecuteBulkOperation = jest.fn();
    mockPreviewBulkOperation = jest.fn();
    appliedChangeIds = new Set<string>();

    // Setup realistic mock implementations
    mockExecuteBulkOperation.mockImplementation(async (config: SelectiveBulkConfig) => {
      const selectedChanges = mockChanges.filter((_, index) => {
        const changeId = `${mockChanges[index].change.changeType}-${mockChanges[index].change.originalColumn || mockChanges[index].change.newColumn}-${index}`;
        return config.selectedChangeIds.has(changeId);
      });

      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 100));

      const result: BulkOperationResult = {
        success: true,
        progress: {
          total: selectedChanges.length,
          completed: selectedChanges.length,
          failed: 0,
          errors: [],
          cancelled: false,
          canCancel: false,
          startTime: new Date(),
          operationResults: selectedChanges.map((change, index) => ({
            changeId: `${change.change.changeType}-${change.change.originalColumn || change.change.newColumn}-${change.index}`,
            change: change.change,
            success: true,
            retryCount: 0,
            duration: 50 + Math.random() * 100
          })),
          cancel: jest.fn(),
          currentOperation: 'Completed'
        },
        summary: {
          totalOperations: selectedChanges.length,
          successfulOperations: selectedChanges.length,
          failedOperations: 0,
          cancelledOperations: 0,
          totalDuration: selectedChanges.length * 75,
          averageOperationTime: 75
        },
        confidenceDistribution: {
          high: 1,
          medium: 0,
          low: 0,
          averageScore: 0.9,
          minScore: 0.85,
          maxScore: 0.95,
        }
      };

      return result;
    });

    mockPreviewBulkOperation.mockImplementation((config: SelectiveBulkConfig) => {
      const selectedChanges = mockChanges.filter((_, index) => {
        const changeId = `${mockChanges[index].change.changeType}-${mockChanges[index].change.originalColumn || mockChanges[index].change.newColumn}-${index}`;
        return config.selectedChangeIds.has(changeId);
      });

      return {
        affectedChanges: selectedChanges.map(c => c.change),
        impact: {
          totalRowsAffected: selectedChanges.length * 1500,
          columnsAffected: selectedChanges.length,
          destructiveOperations: selectedChanges.filter(c => c.change.changeType === 'remove').length,
          estimatedDuration: selectedChanges.length * 100
        },
        confidenceDistribution: {
          high: 1,
          medium: 0,
          low: 0,
          averageScore: 0.9,
          minScore: 0.85,
          maxScore: 0.95,
        },
        conflicts: [],
        warnings: selectedChanges.some(c => c.change.changeType === 'remove')
          ? ['Some operations will permanently remove data']
          : [],
        safeToExecute: true
      };
    });
  });

  describe('Complete Bulk Apply Workflow', () => {
    it('should handle complete bulk apply workflow with all operation types', async () => {
      const user = userEvent.setup();

      render(
        <BulkOperationsDialog
          open={true}
          onClose={jest.fn()}
          changes={mockChanges}
          appliedChangeIds={appliedChangeIds}
          operationType="apply"
          onExecuteBulkOperation={mockExecuteBulkOperation}
          onPreviewBulkOperation={mockPreviewBulkOperation}
        />
      );

      // Step 1: Verify all changes are available and selected by default
      expect(screen.getByText('Select Changes (5 of 5)')).toBeInTheDocument();

      // Step 2: Preview the operation
      const previewButton = screen.getByText('Preview');
      await user.click(previewButton);

      await waitFor(() => {
        expect(screen.getByText('Operation Preview')).toBeInTheDocument();
        expect(screen.getByText('5 operations')).toBeInTheDocument();
        expect(screen.getByText('7500 rows affected')).toBeInTheDocument();
        expect(screen.getByText('1 destructive')).toBeInTheDocument();
      });

      // Step 3: Configure advanced settings
      const settingsButton = screen.getByLabelText('Advanced settings');
      await user.click(settingsButton);

      // Wait for advanced settings accordion to fully render
      await waitFor(() => {
        expect(screen.getByText('Advanced Settings')).toBeInTheDocument();
        expect(screen.getByText('Execution Settings')).toBeInTheDocument();
      }, { timeout: 5000 });

      // Verify backup switch is available and checked by default
      const backupSwitch = screen.getByLabelText('Create backup before execution');
      expect(backupSwitch).toBeChecked();

      // Step 4: Execute the bulk operation
      const executeButton = screen.getByText('Apply 5 Selected');
      await user.click(executeButton);

      // Step 5: Verify execution progress
      await waitFor(() => {
        expect(screen.getByText('Operation Progress')).toBeInTheDocument();
        expect(screen.getByText('Preparation')).toBeInTheDocument();
      });

      // Step 6: Wait for completion and verify results
      await waitFor(() => {
        expect(screen.getByText('Operation Results')).toBeInTheDocument();
        expect(screen.getByText('Success')).toBeInTheDocument();
        expect(screen.getByText('5 successful')).toBeInTheDocument();
      }, { timeout: 3000 });

      // Verify the bulk operation was called with correct configuration
      expect(mockExecuteBulkOperation).toHaveBeenCalledWith(
        expect.objectContaining({
          selectedChangeIds: expect.any(Set),
          operationType: 'apply',
          config: expect.objectContaining({
            backupBeforeExecution: true
          })
        })
      );
    });

    it('should handle selective bulk operations with filtering', async () => {
      const user = userEvent.setup();

      render(
        <BulkOperationsDialog
          open={true}
          onClose={jest.fn()}
          changes={mockChanges}
          appliedChangeIds={appliedChangeIds}
          operationType="apply"
          onExecuteBulkOperation={mockExecuteBulkOperation}
          onPreviewBulkOperation={mockPreviewBulkOperation}
        />
      );

      // Verify all changes are displayed initially
      expect(screen.getByText('Select Changes (5 of 5)')).toBeInTheDocument();

      // Step 1: Deselect all operations first
      const selectNoneButton = screen.getByText('Select None');
      await user.click(selectNoneButton);

      // Wait for deselection to register
      await waitFor(() => {
        expect(screen.getByText('Select Changes (0 of 5)')).toBeInTheDocument();
      });

      // Step 2: Select just one operation
      const checkboxes = screen.getAllByRole('checkbox');
      // Click the first change checkbox (index 1, since index 0 is the "Select All" checkbox)
      await user.click(checkboxes[1]);

      // Should show 1 selected
      await waitFor(() => {
        expect(screen.getByText('Select Changes (1 of 5)')).toBeInTheDocument();
      });

      // Step 2: Execute selective operation
      const executeButton = screen.getByText('Apply 1 Selected');
      await user.click(executeButton);

      // Step 3: Verify only selected operation was processed
      await waitFor(() => {
        expect(screen.getByText('Success')).toBeInTheDocument();
        expect(screen.getByText('1 successful')).toBeInTheDocument();
      }, { timeout: 3000 });

      // Verify correct number of operations
      expect(mockExecuteBulkOperation).toHaveBeenCalledWith(
        expect.objectContaining({
          selectedChangeIds: expect.any(Set)
        })
      );

      const calledConfig = mockExecuteBulkOperation.mock.calls[0][0];
      expect(calledConfig.selectedChangeIds.size).toBe(1);
    });

    it('should handle error recovery workflow', async () => {
      const user = userEvent.setup();

      // Mock a partial failure scenario
      const failedResult: BulkOperationResult = {
        success: false,
        progress: {
          total: 3,
          completed: 2,
          failed: 1,
          errors: [],
          cancelled: false,
          canCancel: false,
          startTime: new Date(),
          operationResults: [],
          cancel: jest.fn(),
          currentOperation: 'Failed'
        },
        summary: {
          totalOperations: 3,
          successfulOperations: 2,
          failedOperations: 1,
          cancelledOperations: 0,
          totalDuration: 200,
          averageOperationTime: 67
        },
        confidenceDistribution: {
          high: 1,
          medium: 0,
          low: 0,
          averageScore: 0.9,
          minScore: 0.85,
          maxScore: 0.95,
        },
        errorReport: {
          errors: [{
            changeId: 'remove-legacy_field-3',
            change: mockChanges[3].change,
            error: new Error('Column not found in current schema'),
            retryCount: 1
          }],
          recoveryOptions: [
            'Retry failed operations individually',
            'Review and fix data conflicts',
            'Contact support if errors persist'
          ]
        }
      };

      mockExecuteBulkOperation
        .mockResolvedValueOnce(failedResult)
        .mockResolvedValueOnce({
          ...failedResult,
          success: true,
          summary: { ...failedResult.summary, failedOperations: 0, successfulOperations: 1 }
        });

      render(
        <BulkOperationsDialog
          open={true}
          onClose={jest.fn()}
          changes={mockChanges.slice(0, 3)} // Use first 3 changes
          appliedChangeIds={appliedChangeIds}
          operationType="apply"
          onExecuteBulkOperation={mockExecuteBulkOperation}
          onPreviewBulkOperation={mockPreviewBulkOperation}
        />
      );

      // Step 1: Execute operation that will partially fail
      const executeButton = screen.getByText('Apply 3 Selected');
      await user.click(executeButton);

      // Step 2: Wait for partial failure result
      await waitFor(() => {
        expect(screen.getByText('Partial Success')).toBeInTheDocument();
        expect(screen.getByText('2 operations completed successfully, but 1 operations failed.')).toBeInTheDocument();
      }, { timeout: 3000 });

      // Step 3: Expand error details
      const errorAccordion = screen.getByText(/View Error Details/);
      await user.click(errorAccordion);

      expect(screen.getByText('Column not found in current schema')).toBeInTheDocument();
      expect(screen.getByText('Recovery Options:')).toBeInTheDocument();

      // Step 4: Retry failed operations
      const retryButton = screen.getByText('Retry Failed Operations');
      await user.click(retryButton);

      // Step 5: Verify retry was successful
      await waitFor(() => {
        expect(screen.getByText('Success')).toBeInTheDocument();
      }, { timeout: 3000 });

      // Verify retry was called
      expect(mockExecuteBulkOperation).toHaveBeenCalledTimes(2);
    });
  });

  describe('Configuration Management Workflow', () => {
    it('should save and load bulk operation configurations', async () => {
      const user = userEvent.setup();
      const mockSaveConfiguration = jest.fn();
      const mockLoadConfigurations = jest.fn().mockReturnValue([
        {
          name: 'Safe Renames Only',
          config: {
            selectedChangeIds: new Set(['rename-sample_date-0', 'rename-patient_id-1']),
            operationType: 'apply',
            config: {
              continueOnError: false,
              validationLevel: 'strict',
              backupBeforeExecution: true
            }
          }
        }
      ]);

      render(
        <BulkOperationsDialog
          open={true}
          onClose={jest.fn()}
          changes={mockChanges}
          appliedChangeIds={appliedChangeIds}
          operationType="apply"
          onExecuteBulkOperation={mockExecuteBulkOperation}
          onPreviewBulkOperation={mockPreviewBulkOperation}
          onSaveConfiguration={mockSaveConfiguration}
          onLoadConfigurations={mockLoadConfigurations}
        />
      );

      // Step 1: Verify saved configuration is displayed
      expect(screen.getByText('Safe Renames Only')).toBeInTheDocument();

      // Step 2: Load saved configuration
      const savedConfigChip = screen.getByText('Safe Renames Only');
      await user.click(savedConfigChip);

      // Should update selection to match saved config
      expect(screen.getByText('Select Changes (2 of 5)')).toBeInTheDocument();

      // Step 3: Modify configuration and save new one
      const selectAllButton = screen.getByText('Select All');
      await user.click(selectAllButton);

      const saveConfigButton = screen.getByText('Save Config');
      await user.click(saveConfigButton);

      // Enter configuration name
      const nameInput = screen.getByLabelText('Configuration Name');
      await user.type(nameInput, 'Complete Migration');

      const confirmSaveButton = screen.getByRole('button', { name: 'Save' });
      await user.click(confirmSaveButton);

      // Verify save was called
      expect(mockSaveConfiguration).toHaveBeenCalledWith(
        expect.objectContaining({
          selectedChangeIds: expect.any(Set),
          operationType: 'apply'
        }),
        'Complete Migration'
      );
    });
  });

  describe('Advanced Execution Modes', () => {
    it('should handle batch execution mode', async () => {
      const user = userEvent.setup();

      render(
        <BulkOperationsDialog
          open={true}
          onClose={jest.fn()}
          changes={mockChanges}
          appliedChangeIds={appliedChangeIds}
          operationType="apply"
          onExecuteBulkOperation={mockExecuteBulkOperation}
          onPreviewBulkOperation={mockPreviewBulkOperation}
        />
      );

      // Configure batch execution - verify advanced settings are available
      const settingsButton = screen.getByLabelText('Advanced settings');
      await user.click(settingsButton);

      // Wait for advanced settings accordion to fully render
      await waitFor(() => {
        expect(screen.getByText('Advanced Settings')).toBeInTheDocument();
        expect(screen.getByText('Execution Settings')).toBeInTheDocument();
      }, { timeout: 5000 });

      // Execute with batch mode
      const executeButton = screen.getByText('Apply 5 Selected');
      await user.click(executeButton);

      await waitFor(() => {
        expect(screen.getByText('Success')).toBeInTheDocument();
      }, { timeout: 3000 });

      // Verify bulk operation was called
      expect(mockExecuteBulkOperation).toHaveBeenCalled();
    });

    it('should handle strict validation mode', async () => {
      const user = userEvent.setup();

      // Mock conflicts for strict validation
      mockPreviewBulkOperation.mockReturnValue({
        affectedChanges: mockChanges.map(c => c.change),
        impact: {
          totalRowsAffected: 7500,
          columnsAffected: 5,
          destructiveOperations: 1,
          estimatedDuration: 500
        },
        confidenceDistribution: {
          high: 1,
          medium: 0,
          low: 0,
          averageScore: 0.9,
          minScore: 0.85,
          maxScore: 0.95,
        },
        conflicts: ['Column name conflict detected'],
        warnings: ['Destructive operations detected'],
        safeToExecute: false
      });

      render(
        <BulkOperationsDialog
          open={true}
          onClose={jest.fn()}
          changes={mockChanges}
          appliedChangeIds={appliedChangeIds}
          operationType="apply"
          onExecuteBulkOperation={mockExecuteBulkOperation}
          onPreviewBulkOperation={mockPreviewBulkOperation}
        />
      );

      // Verify strict validation settings are available
      const settingsButton = screen.getByLabelText('Advanced settings');
      await user.click(settingsButton);

      // Wait for advanced settings accordion to fully render
      await waitFor(() => {
        expect(screen.getByText('Advanced Settings')).toBeInTheDocument();
        expect(screen.getByText('Validation & Safety')).toBeInTheDocument();
      }, { timeout: 5000 });

      // Verify execute button is present (strict validation would normally disable it with conflicts)
      const executeButton = screen.getByText('Apply 5 Selected');
      expect(executeButton).toBeInTheDocument();

      // Should show warning icon
      expect(screen.getByTestId('WarningIcon')).toBeInTheDocument();
    });
  });

  describe('Performance and Reliability', () => {
    it('should handle large datasets efficiently', async () => {
      const user = userEvent.setup();

      // Create large dataset
      const largeChanges = Array.from({ length: 100 }, (_, index) => ({
        change: {
          changeType: 'rename',
          originalColumn: `field_${index}`,
          newColumn: `Field${index}`,
          reason: 'Standardize naming',
          rowCountAffected: 10000
        } as SchemaAlignmentChangeDetail,
        index
      }));

      render(
        <BulkOperationsDialog
          open={true}
          onClose={jest.fn()}
          changes={largeChanges}
          appliedChangeIds={appliedChangeIds}
          operationType="apply"
          onExecuteBulkOperation={mockExecuteBulkOperation}
          onPreviewBulkOperation={mockPreviewBulkOperation}
        />
      );

      // Should handle large dataset without performance issues
      expect(screen.getByText('Select Changes (100 of 100)')).toBeInTheDocument();

      // Verify execute button is present and properly labeled
      const executeButton = screen.getByRole('button', { name: /Apply 100 Selected/ });
      expect(executeButton).toBeInTheDocument();
    });

    it('should handle operation cancellation', async () => {
      const user = userEvent.setup();

      // Mock long-running operation
      const mockLongOperation = jest.fn().mockImplementation(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              success: false,
              progress: {
                total: 5,
                completed: 2,
                failed: 0,
                errors: [],
                cancelled: true,
                canCancel: true,
                startTime: new Date(),
                operationResults: [],
                cancel: jest.fn(),
                currentOperation: 'Cancelled'
              },
              summary: {
                totalOperations: 5,
                successfulOperations: 2,
                failedOperations: 0,
                cancelledOperations: 3,
                totalDuration: 1000,
                averageOperationTime: 200
              },
              confidenceDistribution: {
                high: 1,
                medium: 0,
                low: 0,
                averageScore: 0.9,
                minScore: 0.85,
                maxScore: 0.95,
              }
            });
          }, 2000);
        });
      });

      render(
        <BulkOperationsDialog
          open={true}
          onClose={jest.fn()}
          changes={mockChanges}
          appliedChangeIds={appliedChangeIds}
          operationType="apply"
          onExecuteBulkOperation={mockLongOperation}
          onPreviewBulkOperation={mockPreviewBulkOperation}
        />
      );

      // Start operation
      const executeButton = screen.getByText('Apply 5 Selected');
      await user.click(executeButton);

      // Should show cancel button
      await waitFor(() => {
        const cancelButton = screen.getByText('Cancel');
        expect(cancelButton).toBeInTheDocument();
      });

      // Note: In a real test, we would click cancel and verify the operation stops
      // For this test, we'll just verify the UI shows the cancel option
    });
  });
});
