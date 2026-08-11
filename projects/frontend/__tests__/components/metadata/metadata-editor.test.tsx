/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MetadataEditorComponent } from '../../../components/metadata/metadata-editor';
import { ValidationError } from '../../../lib/types';

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

// Mock the child components
jest.mock('../../../components/metadata/spreadsheet-editor', () => ({
  SpreadsheetEditorComponent: ({ data, validationErrors, disabled, onChange }: any) => (
    <div data-testid="spreadsheet-editor">
      <div>Spreadsheet Editor</div>
      <div>Data rows: {data?.length || 0}</div>
      <div>Disabled: {String(disabled || false)}</div>
      <div>Errors: {validationErrors?.length || 0}</div>
      <button
        onClick={() => onChange?.(data, {
          row: 1,
          column: 0,
          oldValue: 'old',
          newValue: 'new',
          timestamp: new Date()
        })}
      >
        Simulate Change
      </button>
    </div>
  )
}));

jest.mock('../../../components/metadata/validation-sidebar', () => ({
  ValidationSidebarComponent: ({ data, changes, validationErrors, isSubmitting, onSubmit, children }: any) => (
    <div data-testid="validation-sidebar">
      <div>Validation Sidebar</div>
      <div>Changes: {changes?.length || 0}</div>
      <div>Submitting: {String(isSubmitting || false)}</div>
      <button onClick={() => onSubmit?.(data)}>Submit</button>
      <div data-testid="error-cards-container">{children}</div>
    </div>
  )
}));

jest.mock('../../../components/metadata/error-card', () => ({
  ErrorCardComponent: ({ error, onAccept, onAcceptAll, onDismiss }: any) => (
    <div data-testid={`error-card-${error.row}-${error.column}`}>
      <div>Error: {error.errorType}</div>
      <div>Row: {error.row}, Column: {error.column}</div>
      <div>Current: {error.currentValue}</div>
      <div>Recommended: {error.recommendedValue}</div>
      <button onClick={onAccept}>Accept</button>
      <button onClick={onAcceptAll}>Accept All</button>
      <button onClick={onDismiss}>Dismiss</button>
    </div>
  )
}));

describe('MetadataEditorComponent', () => {
  const mockCsvData = [
    ['Name', 'Age', 'City'],
    ['John', '25', 'New York'],
    ['Jane', '30', 'Boston']
  ];

  const mockValidationErrors: ValidationError[] = [
    {
      row: 1,
      column: 'Name',
      currentValue: 'John',
      recommendedValue: 'John Smith',
      errorType: 'INVALID_FORMAT'
    },
    {
      row: 2,
      column: 'Age',
      currentValue: '30',
      recommendedValue: '31',
      errorType: 'INVALID_VALUE'
    }
  ];

  const mockOnValidationComplete = jest.fn();
  const mockOnValidationErrors = jest.fn();

  beforeEach(() => {
    mockOnValidationComplete.mockClear();
    mockOnValidationErrors.mockClear();
  });

  it('renders both spreadsheet and sidebar components', () => {
    renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    expect(screen.getByTestId('spreadsheet-editor')).toBeInTheDocument();
    expect(screen.getByTestId('validation-sidebar')).toBeInTheDocument();
    expect(screen.getByText('Spreadsheet Editor')).toBeInTheDocument();
    expect(screen.getByText('Validation Sidebar')).toBeInTheDocument();
  });

  it('passes correct props to spreadsheet editor', () => {
    renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        validationErrors={mockValidationErrors}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    expect(screen.getByText('Data rows: 3')).toBeInTheDocument();
    expect(screen.getByText('Disabled: false')).toBeInTheDocument();
    expect(screen.getByText('Errors: 2')).toBeInTheDocument();
  });

  it('renders error cards for validation errors', () => {
    renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        validationErrors={mockValidationErrors}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    expect(screen.getByTestId('error-card-1-Name')).toBeInTheDocument();
    expect(screen.getByTestId('error-card-2-Age')).toBeInTheDocument();
    expect(screen.getByText('Error: INVALID_FORMAT')).toBeInTheDocument();
    expect(screen.getByText('Error: INVALID_VALUE')).toBeInTheDocument();
  });

  it('handles spreadsheet changes correctly', () => {
    renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    const simulateChangeButton = screen.getByText('Simulate Change');
    fireEvent.click(simulateChangeButton);

    expect(screen.getByText('Changes: 1')).toBeInTheDocument();
  });

  it('handles error acceptance correctly', () => {
    renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        validationErrors={mockValidationErrors}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    // Initially should have 2 error cards
    expect(screen.getByTestId('error-card-1-Name')).toBeInTheDocument();
    expect(screen.getByTestId('error-card-2-Age')).toBeInTheDocument();

    // Accept the first error
    const acceptButtons = screen.getAllByText('Accept');
    fireEvent.click(acceptButtons[0]);

    // Should now have only 1 error card and 1 change
    expect(screen.queryByTestId('error-card-1-Name')).not.toBeInTheDocument();
    expect(screen.getByTestId('error-card-2-Age')).toBeInTheDocument();
    expect(screen.getByText('Changes: 1')).toBeInTheDocument();
  });

  it('handles accept all correctly', () => {
    const errorsWithSameType: ValidationError[] = [
      {
        row: 1,
        column: 'Name',
        currentValue: 'John',
        recommendedValue: 'John Smith',
        errorType: 'INVALID_FORMAT'
      },
      {
        row: 2,
        column: 'Name',
        currentValue: 'Jane',
        recommendedValue: 'Jane Doe',
        errorType: 'INVALID_FORMAT'
      }
    ];

    renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        validationErrors={errorsWithSameType}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    // Accept all for the first error (should affect both errors of same type)
    const acceptAllButtons = screen.getAllByText('Accept All');
    fireEvent.click(acceptAllButtons[0]);

    // Both error cards should be removed
    expect(screen.queryByTestId('error-card-1-Name')).not.toBeInTheDocument();
    expect(screen.queryByTestId('error-card-2-Name')).not.toBeInTheDocument();
    expect(screen.getByText('Changes: 2')).toBeInTheDocument();
  });

  it('handles error dismissal correctly', () => {
    renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        validationErrors={mockValidationErrors}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    // Dismiss the first error
    const dismissButtons = screen.getAllByText('Dismiss');
    fireEvent.click(dismissButtons[0]);

    // Should now have only 1 error card and no changes
    expect(screen.queryByTestId('error-card-1-Name')).not.toBeInTheDocument();
    expect(screen.getByTestId('error-card-2-Age')).toBeInTheDocument();
    expect(screen.getByText('Changes: 0')).toBeInTheDocument();
  });

  it('renders submit button from ValidationSidebarComponent', async () => {
    renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    // Verify submit button is rendered in sidebar
    const submitButton = screen.getByText('Submit');
    expect(submitButton).toBeInTheDocument();

    // Component doesn't manage submission state internally
    expect(screen.getByText('Submitting: false')).toBeInTheDocument();
  });

  it('updates data when csvData prop changes', () => {
    const { rerender } = renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    expect(screen.getByText('Data rows: 3')).toBeInTheDocument();

    const newCsvData = [
      ['Name', 'Age'],
      ['Bob', '35']
    ];

    rerender(
      <ThemeProvider theme={theme}>
        <MetadataEditorComponent
          csvData={newCsvData}
          onValidationComplete={mockOnValidationComplete}
        />
      </ThemeProvider>
    );

    expect(screen.getByText('Data rows: 2')).toBeInTheDocument();
  });

  it('updates errors when validationErrors prop changes', () => {
    const { rerender } = renderWithTheme(
      <MetadataEditorComponent
        csvData={mockCsvData}
        validationErrors={mockValidationErrors}
        onValidationComplete={mockOnValidationComplete}
      />
    );

    expect(screen.getByText('Errors: 2')).toBeInTheDocument();

    rerender(
      <ThemeProvider theme={theme}>
        <MetadataEditorComponent
          csvData={mockCsvData}
          validationErrors={[mockValidationErrors[0]]}
          onValidationComplete={mockOnValidationComplete}
        />
      </ThemeProvider>
    );

    expect(screen.getByText('Errors: 1')).toBeInTheDocument();
  });
});
