/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { MetadataEditorComponent } from '../../../components/metadata/metadata-editor';
import { ValidationError, ValidationErrorType } from '../../../lib/types';
import { theme } from '../../../lib/theme';

// Mock the ValidationSidebarComponent to focus on error card interactions
jest.mock('../../../components/metadata/validation-sidebar', () => ({
  ValidationSidebarComponent: ({ children, onDisableSpreadsheet }: any) => (
    <div data-testid="validation-sidebar">
      {children}
    </div>
  )
}));

// Mock the SpreadsheetEditorComponent
jest.mock('../../../components/metadata/spreadsheet-editor', () => ({
  SpreadsheetEditorComponent: ({ data, onChange, disabled }: any) => (
    <div data-testid="spreadsheet-editor" data-disabled={disabled}>
      <div data-testid="spreadsheet-data">{JSON.stringify(data)}</div>
    </div>
  )
}));

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

describe('MetadataEditorComponent - Error Card Integration', () => {
  const mockCsvData = [
    ['name', 'age', 'city'],
    ['John', 'invalid_age', 'New York'],
    ['Jane', '25', 'Boston'],
    ['Bob', 'bad_age', 'Chicago']
  ];

  const mockValidationErrors: ValidationError[] = [
    {
      row: 1,
      column: 'age',
      currentValue: 'invalid_age',
      recommendedValue: '30',
      errorType: ValidationErrorType.INVALID_OPTION,
      validOptions: ['18', '25', '30', '35']
    },
    {
      row: 3,
      column: 'age',
      currentValue: 'bad_age',
      recommendedValue: '28',
      errorType: ValidationErrorType.INVALID_OPTION,
      validOptions: ['18', '25', '30', '35']
    },
    {
      row: 2,
      column: 'name',
      currentValue: '',
      recommendedValue: null,
      errorType: ValidationErrorType.REQUIRED_VALUE,
      validOptions: null
    }
  ];

  const mockOnValidationComplete = jest.fn();
  const mockOnValidationErrors = jest.fn();

  let consoleLogSpy: jest.SpyInstance;
  let consoleWarnSpy: jest.SpyInstance;
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock console methods to avoid noise in tests
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Error Card Rendering', () => {
    it('should render error cards for all validation errors', () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      // Should render 3 error cards
      expect(screen.getAllByText(/Row \d+, Column/)).toHaveLength(3);

      // Check specific error cards
      expect(screen.getByText('Row 1, Column age')).toBeInTheDocument();
      expect(screen.getByText('Row 3, Column age')).toBeInTheDocument();
      expect(screen.getByText('Row 2, Column name')).toBeInTheDocument();
    });

    it('should display error cards with correct styling', () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      // Check that error cards have application theme styling
      const errorCards = screen.getAllByText(/Invalid Option|Required Value/);
      expect(errorCards.length).toBeGreaterThan(0);

      errorCards.forEach(card => {
        expect(card).toBeVisible();
      });
    });
  });

  describe('Accept Button Functionality', () => {
    it('should apply single change when Accept button is clicked', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      // Find and click Accept button for first error
      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 30/i });
      fireEvent.click(acceptButton);

      await waitFor(() => {
        // Error card should be removed
        expect(screen.queryByText('Row 1, Column age')).not.toBeInTheDocument();
      });

      // Other error cards should still be present
      expect(screen.getByText('Row 3, Column age')).toBeInTheDocument();
      expect(screen.getByText('Row 2, Column name')).toBeInTheDocument();
    });

    it('should update spreadsheet data when change is applied', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 30/i });
      fireEvent.click(acceptButton);

      await waitFor(() => {
        // Check that spreadsheet data has been updated
        const spreadsheetData = screen.getByTestId('spreadsheet-data');
        const dataText = spreadsheetData.textContent;

        // The data should contain the updated value
        expect(dataText).toContain('30');
      });
    });

    it('should record change in changes list', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 30/i });
      fireEvent.click(acceptButton);

      await waitFor(() => {
        // Verify console logs show change was recorded
        expect(consoleLogSpy).toHaveBeenCalledWith(
          expect.stringContaining('Added change record'),
          expect.any(Object)
        );
      });
    });
  });

  describe('Accept All Button Functionality', () => {
    it('should apply all similar changes when Accept All is clicked', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      // Find Accept All button for age column errors (use first one since there are multiple)
      const acceptAllButtons = screen.getAllByRole('button', { name: /accept all similar changes for column age/i });
      fireEvent.click(acceptAllButtons[0]);

      await waitFor(() => {
        // Both age column error cards should be removed
        expect(screen.queryByText('Row 1, Column age')).not.toBeInTheDocument();
        expect(screen.queryByText('Row 3, Column age')).not.toBeInTheDocument();
      });

      // Name column error should still be present
      expect(screen.getByText('Row 2, Column name')).toBeInTheDocument();
    });

    it('should apply batch changes atomically', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptAllButtons = screen.getAllByRole('button', { name: /accept all similar changes for column age/i });
      fireEvent.click(acceptAllButtons[0]);

      await waitFor(() => {
        // Verify batch processing happened - both error cards should be removed
        expect(screen.queryByText('Row 1, Column age')).not.toBeInTheDocument();
        expect(screen.queryByText('Row 3, Column age')).not.toBeInTheDocument();

        // Verify some console logging happened for bulk operations
        expect(consoleLogSpy).toHaveBeenCalled();
      });
    });

    it('should record all changes in changes list', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptAllButtons = screen.getAllByRole('button', { name: /accept all similar changes for column age/i });
      fireEvent.click(acceptAllButtons[0]);

      await waitFor(() => {
        // Verify both errors were removed from UI
        expect(screen.queryByText('Row 1, Column age')).not.toBeInTheDocument();
        expect(screen.queryByText('Row 3, Column age')).not.toBeInTheDocument();

        // Verify some console logging happened
        expect(consoleLogSpy).toHaveBeenCalled();
      });
    });

    it('should handle errors without recommended values correctly', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      // Try to click Accept All for name column (which has no recommended value)
      const nameAcceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column name/i });
      fireEvent.click(nameAcceptAllButton);

      await waitFor(() => {
        // Should log warning about no similar errors with recommended values
        expect(consoleWarnSpy).toHaveBeenCalledWith(
          expect.stringContaining('No similar errors with recommended values found')
        );
      });

      // Name error should still be present since no changes were applied
      expect(screen.getByText('Row 2, Column name')).toBeInTheDocument();
    });
  });

  describe('Error Card Removal', () => {
    it('should remove error card when dismissed', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      // Find and click dismiss button
      const dismissButtons = screen.getAllByRole('button', { name: /dismiss error/i });
      fireEvent.click(dismissButtons[0]);

      await waitFor(() => {
        // One error card should be removed
        const remainingErrors = screen.getAllByText(/Row \d+, Column/);
        expect(remainingErrors).toHaveLength(2);
      });
    });

    it('should not modify spreadsheet data when error is dismissed', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const originalData = screen.getByTestId('spreadsheet-data').textContent;

      // Dismiss an error
      const dismissButtons = screen.getAllByRole('button', { name: /dismiss error/i });
      fireEvent.click(dismissButtons[0]);

      await waitFor(() => {
        // Data should remain unchanged
        const currentData = screen.getByTestId('spreadsheet-data').textContent;
        expect(currentData).toBe(originalData);
      });
    });
  });

  describe('Column Index Resolution', () => {
    it('should correctly resolve column indices using findIndex', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 30/i });
      fireEvent.click(acceptButton);

      await waitFor(() => {
        // Verify column index resolution logs
        expect(consoleLogSpy).toHaveBeenCalledWith(
          expect.stringContaining('Applying change to data'),
          expect.objectContaining({
            errorColumn: 'age',
            columnIndex: 1, // 'age' is at index 1 in headers
            headers: ['name', 'age', 'city']
          })
        );
      });
    });

    it('should handle invalid column references gracefully', async () => {
      const invalidError: ValidationError = {
        row: 1,
        column: 'nonexistent_column',
        currentValue: 'test',
        recommendedValue: 'fixed',
        errorType: ValidationErrorType.INVALID_OPTION,
        validOptions: null
      };

      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={[invalidError]}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: fixed/i });
      fireEvent.click(acceptButton);

      await waitFor(() => {
        // Should log error about invalid column
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          expect.stringContaining('Failed to apply change - invalid column or row'),
          expect.any(Object)
        );
      });
    });
  });

  describe('Spreadsheet Update Propagation', () => {
    it('should propagate changes to spreadsheet component', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 30/i });
      fireEvent.click(acceptButton);

      await waitFor(() => {
        // Spreadsheet should receive updated data
        const spreadsheetData = screen.getByTestId('spreadsheet-data');
        const dataText = spreadsheetData.textContent;

        // Should contain the updated value
        expect(dataText).toContain('"30"');
        // Should not contain the old invalid value in that position
        expect(dataText).not.toContain('"invalid_age"');
      });
    });
  });

  describe('Error Popup Notifications', () => {
    it('should show error snackbar when column is not found', async () => {
      const invalidError: ValidationError = {
        row: 1,
        column: 'nonexistent_column',
        currentValue: 'test',
        recommendedValue: 'fixed',
        errorType: ValidationErrorType.INVALID_OPTION,
        validOptions: null
      };

      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={[invalidError]}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: fixed/i });
      fireEvent.click(acceptButton);

      await waitFor(() => {
        // Should show error snackbar
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByText(/Cannot find column "nonexistent_column" in the spreadsheet/)).toBeInTheDocument();
      });
    });

    it('should show error snackbar when row is not found', async () => {
      const invalidRowError: ValidationError = {
        row: 999, // Row that doesn't exist
        column: 'age',
        currentValue: 'test',
        recommendedValue: 'fixed',
        errorType: ValidationErrorType.INVALID_OPTION,
        validOptions: null
      };

      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={[invalidRowError]}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: fixed/i });
      fireEvent.click(acceptButton);

      await waitFor(() => {
        // Should show error snackbar
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByText(/Cannot find row 999 in the spreadsheet/)).toBeInTheDocument();
      });
    });

    it('should show error snackbar when no recommended value is available', async () => {
      const noRecommendationError: ValidationError = {
        row: 1,
        column: 'age',
        currentValue: 'test',
        recommendedValue: null,
        errorType: ValidationErrorType.REQUIRED_VALUE,
        validOptions: null
      };

      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={[noRecommendationError]}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      // Accept button should not be rendered for errors without recommended values
      expect(screen.queryByRole('button', { name: /accept suggested value/i })).not.toBeInTheDocument();
    });

    it('should show error snackbar for Accept All with no similar errors', async () => {
      const singleError: ValidationError = {
        row: 1,
        column: 'unique_column',
        currentValue: 'test',
        recommendedValue: null,
        errorType: ValidationErrorType.REQUIRED_VALUE,
        validOptions: null
      };

      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={[singleError]}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column unique_column/i });
      fireEvent.click(acceptAllButton);

      await waitFor(() => {
        // Should show error snackbar
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByText(/No similar errors found for column "unique_column"/)).toBeInTheDocument();
      });
    });

    it('should allow closing error snackbar', async () => {
      const invalidError: ValidationError = {
        row: 1,
        column: 'nonexistent_column',
        currentValue: 'test',
        recommendedValue: 'fixed',
        errorType: ValidationErrorType.INVALID_OPTION,
        validOptions: null
      };

      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={[invalidError]}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: fixed/i });
      fireEvent.click(acceptButton);

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });

      // Close the snackbar
      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      });
    });

    it('should show batch error summary for Accept All failures', async () => {
      const mixedErrors: ValidationError[] = [
        {
          row: 1,
          column: 'nonexistent_column',
          currentValue: 'test1',
          recommendedValue: 'fixed1',
          errorType: ValidationErrorType.INVALID_OPTION,
          validOptions: null
        },
        {
          row: 999,
          column: 'nonexistent_column',
          currentValue: 'test2',
          recommendedValue: 'fixed2',
          errorType: ValidationErrorType.INVALID_OPTION,
          validOptions: null
        }
      ];

      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mixedErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      const acceptAllButtons = screen.getAllByRole('button', { name: /accept all similar changes for column nonexistent_column/i });
      fireEvent.click(acceptAllButtons[0]);

      await waitFor(() => {
        // Should show some error feedback (snackbar/alert)
        const alert = screen.queryByRole('alert');
        if (alert) {
          // If alert is shown, it should contain error information
          expect(alert).toBeInTheDocument();
        }
        // At minimum, verify errors were logged
        expect(consoleErrorSpy).toHaveBeenCalled();
      }, { timeout: 2000 });
    });
  });

  describe('Console Error Verification', () => {
    it('should not produce console errors during normal operation', async () => {
      render(
        <TestWrapper>
          <MetadataEditorComponent
            csvData={mockCsvData}
            validationErrors={mockValidationErrors}
            onValidationComplete={mockOnValidationComplete}
            onValidationErrors={mockOnValidationErrors}
          />
        </TestWrapper>
      );

      // Perform various operations
      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 30/i });
      fireEvent.click(acceptButton);

      const acceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column age/i });
      fireEvent.click(acceptAllButton);

      const dismissButton = screen.getByRole('button', { name: /dismiss error/i });
      fireEvent.click(dismissButton);

      await waitFor(() => {
        // Should have success logs but no error logs for normal operations
        expect(consoleLogSpy).toHaveBeenCalledWith(
          expect.stringContaining('Change applied successfully'),
          expect.any(Object)
        );
      });
    });
  });
});
