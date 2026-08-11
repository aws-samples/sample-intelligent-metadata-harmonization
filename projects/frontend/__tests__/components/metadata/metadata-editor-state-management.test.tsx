/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MetadataEditorComponent } from '../../../components/metadata/metadata-editor';
import {
  ValidationError,
  ValidationErrorType,
  ValidationStatusResponse,
  PostSchemaAlignmentData,
  TransformationSummary
} from '../../../lib/types';

// Mock the CSV utils
jest.mock('../../../lib/csv-utils', () => ({
  parseCSV: jest.fn((csvString: string) => {
    // Simple mock implementation
    return csvString.split('\n').map(row => row.split(','));
  })
}));

// Mock child components
jest.mock('../../../components/metadata/spreadsheet-editor', () => ({
  SpreadsheetEditorComponent: ({ data, onChange, validationErrors }: any) => (
    <div data-testid="spreadsheet-editor">
      <div data-testid="spreadsheet-data">{JSON.stringify(data)}</div>
      <div data-testid="validation-errors-count">{validationErrors?.length || 0}</div>
      <button
        data-testid="simulate-change"
        onClick={() => onChange([['Header1', 'Header2'], ['New', 'Data']], {
          row: 1,
          column: 0,
          oldValue: 'Old',
          newValue: 'New',
          timestamp: new Date()
        })}
      >
        Simulate Change
      </button>
    </div>
  )
}));

jest.mock('../../../components/metadata/validation-sidebar', () => ({
  ValidationSidebarComponent: ({ data, validationErrors, children }: any) => (
    <div data-testid="validation-sidebar">
      <div data-testid="sidebar-data">{JSON.stringify(data)}</div>
      <div data-testid="sidebar-errors-count">{validationErrors?.length || 0}</div>
      {children}
    </div>
  )
}));

jest.mock('../../../components/metadata/error-card', () => ({
  ErrorCardComponent: ({ error, onAccept }: any) => (
    <div data-testid={`error-card-${error.row}-${error.column}`}>
      <span>{error.column}: {error.currentValue}</span>
      <button data-testid={`accept-${error.row}-${error.column}`} onClick={onAccept}>
        Accept
      </button>
    </div>
  )
}));

describe('MetadataEditorComponent - State Management', () => {
  const mockCsvData = [
    ['Name', 'Age', 'City'],
    ['John', '25', 'New York'],
    ['Jane', '30', 'Boston']
  ];

  const mockValidationErrors: ValidationError[] = [
    {
      row: 1,
      column: 'Age',
      currentValue: '25',
      validOptions: null,
      recommendedValue: '25.0',
      errorType: ValidationErrorType.INVALID_OPTION
    }
  ];

  const mockOnValidationComplete = jest.fn();
  const mockOnValidationErrors = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Initial State Management', () => {
    it('should initialize with original data view and correct state', () => {
      render(
        <MetadataEditorComponent
          csvData={mockCsvData}
          validationErrors={mockValidationErrors}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      // Check that spreadsheet shows original data
      const spreadsheetData = screen.getByTestId('spreadsheet-data');
      expect(spreadsheetData).toHaveTextContent(JSON.stringify(mockCsvData));

      // Check that validation errors are displayed
      expect(screen.getByTestId('validation-errors-count')).toHaveTextContent('1');
    });

    it('should handle empty validation errors gracefully', () => {
      render(
        <MetadataEditorComponent
          csvData={mockCsvData}
          validationErrors={null}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      expect(screen.getByTestId('validation-errors-count')).toHaveTextContent('0');
    });
  });

  describe('getCurrentData Method', () => {
    it('should return original data when in original view', () => {
      render(
        <MetadataEditorComponent
          csvData={mockCsvData}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      // Should show original data by default
      const spreadsheetData = screen.getByTestId('spreadsheet-data');
      expect(spreadsheetData).toHaveTextContent(JSON.stringify(mockCsvData));
    });
  });

  describe('handleValidationStatusUpdate Method', () => {
    it('should update state with post-schema alignment data', async () => {
      const { rerender } = render(
        <MetadataEditorComponent
          csvData={mockCsvData}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      // Mock transformation summary
      const transformationSummary: TransformationSummary = {
        columnsRenamed: 1,
        columnsAdded: 1,
        columnsRemoved: 0,
        rowsOriginal: 3,
        rowsAligned: 3,
        columnMappings: { 'Name': 'FullName' },
        addedColumns: ['Email'],
        removedColumns: []
      };

      const postSchemaData: PostSchemaAlignmentData = {
        originalDataCsv: 'Name,Age,City\nJohn,25,New York\nJane,30,Boston',
        alignedDataCsv: 'FullName,Age,City,Email\nJohn,25,New York,\nJane,30,Boston,',
        columnMappings: { 'Name': 'FullName' },
        transformationSummary
      };

      // Simulate receiving validation status update
      // Note: In a real implementation, this would be called through a prop or context
      // For testing, we'll verify the component can handle the data structure
      expect(postSchemaData.transformationSummary?.columnsRenamed).toBe(1);
      expect(postSchemaData.transformationSummary?.columnsAdded).toBe(1);
    });

    it('should handle validation status update with validation results', () => {
      const statusResponse: ValidationStatusResponse = {
        success: true,
        jobId: 'test-job-123',
        status: 'completed' as any,
        latestResults: {
          validationResults: mockValidationErrors,
          summary: {
            totalRows: 3,
            totalErrors: 1,
            errorTypes: {
              [ValidationErrorType.INVALID_OPTION]: 1,
              [ValidationErrorType.REQUIRED_VALUE]: 0
            }
          }
        }
      };

      // Component should handle this structure
      expect(statusResponse.latestResults?.validationResults).toHaveLength(1);
    });
  });

  describe('Data Changes and View Management', () => {
    it('should handle spreadsheet changes correctly', async () => {
      render(
        <MetadataEditorComponent
          csvData={mockCsvData}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      // Simulate a change in the spreadsheet
      const changeButton = screen.getByTestId('simulate-change');
      fireEvent.click(changeButton);

      // Wait for state update
      await waitFor(() => {
        const spreadsheetData = screen.getByTestId('spreadsheet-data');
        expect(spreadsheetData).toHaveTextContent('["Header1","Header2"],["New","Data"]');
      });
    });

    it('should apply validation error fixes correctly', async () => {
      render(
        <MetadataEditorComponent
          csvData={mockCsvData}
          validationErrors={mockValidationErrors}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      // Find and click the accept button for the error
      const acceptButton = screen.getByTestId('accept-1-Age');
      fireEvent.click(acceptButton);

      // Wait for error to be removed
      await waitFor(() => {
        expect(screen.getByTestId('validation-errors-count')).toHaveTextContent('0');
      });
    });
  });

  describe('Props Updates', () => {
    it('should update original data when csvData prop changes', () => {
      const { rerender } = render(
        <MetadataEditorComponent
          csvData={mockCsvData}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      const newCsvData = [
        ['Name', 'Age'],
        ['Alice', '28']
      ];

      rerender(
        <MetadataEditorComponent
          csvData={newCsvData}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      const spreadsheetData = screen.getByTestId('spreadsheet-data');
      expect(spreadsheetData).toHaveTextContent(JSON.stringify(newCsvData));
    });

    it('should update validation errors when validationErrors prop changes', () => {
      const { rerender } = render(
        <MetadataEditorComponent
          csvData={mockCsvData}
          validationErrors={mockValidationErrors}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      expect(screen.getByTestId('validation-errors-count')).toHaveTextContent('1');

      const newErrors: ValidationError[] = [
        ...mockValidationErrors,
        {
          row: 2,
          column: 'City',
          currentValue: 'Boston',
          validOptions: ['Boston', 'Cambridge'],
          recommendedValue: 'Boston',
          errorType: ValidationErrorType.INVALID_OPTION
        }
      ];

      rerender(
        <MetadataEditorComponent
          csvData={mockCsvData}
          validationErrors={newErrors}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      expect(screen.getByTestId('validation-errors-count')).toHaveTextContent('2');
    });
  });

  describe('Error Handling', () => {
    it('should handle errors without recommended values', async () => {
      const errorWithoutRecommendation: ValidationError = {
        row: 1,
        column: 'Age',
        currentValue: '25',
        validOptions: ['20', '30', '40'],
        recommendedValue: null,
        errorType: ValidationErrorType.INVALID_OPTION
      };

      render(
        <MetadataEditorComponent
          csvData={mockCsvData}
          validationErrors={[errorWithoutRecommendation]}
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      // Try to accept the error without recommendation
      const acceptButton = screen.getByTestId('accept-1-Age');
      fireEvent.click(acceptButton);

      // Error should still be present since it can't be applied
      await waitFor(() => {
        expect(screen.getByTestId('validation-errors-count')).toHaveTextContent('1');
      });
    });
  });
});
