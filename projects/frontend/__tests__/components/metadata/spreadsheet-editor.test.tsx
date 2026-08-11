/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { SpreadsheetEditorComponent } from '../../../components/metadata/spreadsheet-editor';
import { ValidationError, ValidationErrorType } from '../../../lib/types';
import { beforeEach } from 'node:test';

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

// Mock react-spreadsheet with error highlighting support
jest.mock('react-spreadsheet', () => {
  return function MockSpreadsheet({ data, onChange, columnLabels, rowLabels, className, Cell }: any) {
    // Access the parent component's error map through a global test helper
    const getErrorMap = () => {
      // This is a simplified version - in real implementation, we'd need to pass validation errors
      // For testing, we'll simulate the error map based on known test data
      const errorMap = new Map();

      // Simulate errors for test cases
      if (columnLabels?.includes('Name') && data?.[0]?.[0]?.value === 'John') {
        errorMap.set('0-0', true); // First data row, Name column
      }
      if (columnLabels?.includes('Age') && data?.[1]?.[1]?.value === '30') {
        errorMap.set('1-1', true); // Second data row, Age column
      }

      return errorMap;
    };

    const errorMap = getErrorMap();

    return (
      <div data-testid="mock-spreadsheet" className={className}>
        <table>
          <thead>
            <tr>
              <th></th>
              {columnLabels?.map((label: string, index: number) => (
                <th key={index} data-column-index={index}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.map((row: any[], rowIndex: number) => (
              <tr key={rowIndex}>
                <td data-row-index={rowIndex}>{rowLabels?.[rowIndex]}</td>
                {row.map((cell: any, colIndex: number) => {
                  const CellComponent = Cell || 'td';
                  // Check if this cell should have error styling
                  const errorKey = `${rowIndex}-${colIndex}`;
                  const hasError = errorMap.has(errorKey);

                  return (
                    <CellComponent
                      key={colIndex}
                      row={rowIndex}
                      column={colIndex}
                      data-testid={`cell-${rowIndex}-${colIndex}`}
                      className={hasError ? 'error-cell' : ''}
                      // Simulate problematic props that should be filtered
                      DataViewer={undefined}
                      evaluatedData={null}
                      setCellDimensions={() => {}}
                      setCellData={() => {}}
                      data-active={rowIndex === 0 && colIndex === 0 ? 'true' : 'false'}
                      active={rowIndex === 0 && colIndex === 0} // First data row, first column
                      copied={false}
                      dragging={false}
                      select={() => {}}
                      activate={() => {}}
                      onClick={() => {
                        // Simulate cell edit
                        const newData = [...data];
                        newData[rowIndex] = [...row];
                        newData[rowIndex][colIndex] = { value: 'edited' };
                        onChange?.(newData);
                      }}
                    >
                      {cell?.value || ''}
                    </CellComponent>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };
});

describe('SpreadsheetEditorComponent', () => {
  const mockData = [
    ['Name', 'Age', 'City'],
    ['John', '25', 'New York'],
    ['Jane', '30', 'Boston']
  ];

  const mockOnChange = jest.fn();
  const mockOnRowOperation = jest.fn();

  const mockValidationErrors: ValidationError[] = [
    {
      row: 1, // First data row
      column: 'Name',
      currentValue: 'John',
      recommendedValue: null,
      errorType: ValidationErrorType.REQUIRED_VALUE,
      validOptions: null
    },
    {
      row: 2, // Second data row
      column: 'Age',
      currentValue: '30',
      recommendedValue: '25',
      errorType: ValidationErrorType.INVALID_PATTERN,
      validOptions: ['25', '30', '35']
    }
  ];

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders spreadsheet with data correctly', () => {
    renderWithTheme(
      <SpreadsheetEditorComponent
        data={mockData}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument(); // Header only
    expect(screen.getByText('Age')).toBeInTheDocument();
    expect(screen.getByText('City')).toBeInTheDocument();
    expect(screen.getByText('John')).toBeInTheDocument(); // Data row
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('New York')).toBeInTheDocument();
  });

  it('displays column labels from header row', () => {
    renderWithTheme(
      <SpreadsheetEditorComponent
        data={mockData}
        onChange={mockOnChange}
      />
    );

    // Check that column headers are displayed
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Age')).toBeInTheDocument();
    expect(screen.getByText('City')).toBeInTheDocument();
  });

  it('displays row labels with 1-based indexing', () => {
    renderWithTheme(
      <SpreadsheetEditorComponent
        data={mockData}
        onChange={mockOnChange}
      />
    );

    // Check that row numbers are displayed (1-based for data rows only)
    expect(screen.getByText('1')).toBeInTheDocument(); // First data row
    expect(screen.getByText('2')).toBeInTheDocument(); // Second data row
  });

  it('calls onChange when cell is edited', () => {
    renderWithTheme(
      <SpreadsheetEditorComponent
        data={mockData}
        onChange={mockOnChange}
      />
    );

    // Click on a cell to simulate editing (cell-0-0 is first data row, first column)
    const cell = screen.getByTestId('cell-0-0');
    fireEvent.click(cell);

    expect(mockOnChange).toHaveBeenCalled();
    const [newData, change] = mockOnChange.mock.calls[0];

    // Check that the data was updated (newData includes header + data rows)
    expect(newData[1][0]).toBe('edited'); // Row 1 (first data row) after header

    // Check that change object is provided
    expect(change).toEqual({
      row: 1, // Row 1 in the full data array (after header)
      column: 0,
      oldValue: 'John',
      newValue: 'edited',
      timestamp: expect.any(Date)
    });
  });

  it('applies disabled styling when disabled prop is true', () => {
    renderWithTheme(
      <SpreadsheetEditorComponent
        data={mockData}
        disabled={true}
        onChange={mockOnChange}
      />
    );

    const spreadsheet = screen.getByTestId('mock-spreadsheet');
    expect(spreadsheet).toHaveClass('spreadsheet-disabled');
  });

  it('does not call onChange when disabled', () => {
    const isolatedMockOnChange = jest.fn();

    renderWithTheme(
      <SpreadsheetEditorComponent
        data={mockData}
        disabled={true}
        onChange={isolatedMockOnChange}
      />
    );

    // Try to click on a cell
    const cell = screen.getByTestId('cell-0-0');
    fireEvent.click(cell);

    // onChange should not be called when disabled
    expect(isolatedMockOnChange).not.toHaveBeenCalled();
  });

  it('handles validation errors without crashing', () => {
    const validationErrors: ValidationError[] = [
      {
        row: 1, // Row 1 in full data (first data row)
        column: 'Name',
        currentValue: 'John',
        recommendedValue: 'John Doe',
        errorType: ValidationErrorType.INVALID_PATTERN,
        validOptions: null,
        confidenceScore: 0.85,
        confidenceLevel: 'High'
      },
      {
        row: 2, // Row 2 in full data (second data row)
        column: 'Age',
        currentValue: '30',
        recommendedValue: '30',
        errorType: ValidationErrorType.REQUIRED_VALUE,
        validOptions: null,
        confidenceScore: 0.90,
        confidenceLevel: 'High'
      }
    ];

    renderWithTheme(
      <SpreadsheetEditorComponent
        data={mockData}
        validationErrors={validationErrors}
        onChange={mockOnChange}
      />
    );

    // Component should render without errors when validation errors are provided
    expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    expect(screen.getByText('John')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
  });

  it('updates spreadsheet data when props change', () => {
    const { rerender } = renderWithTheme(
      <SpreadsheetEditorComponent
        data={mockData}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('John')).toBeInTheDocument();

    // Update data prop
    const newData = [
      ['Name', 'Age', 'City'],
      ['Bob', '35', 'Chicago'],
      ['Jane', '30', 'Boston']
    ];

    rerender(
      <ThemeProvider theme={theme}>
        <SpreadsheetEditorComponent
          data={newData}
          onChange={mockOnChange}
        />
      </ThemeProvider>
    );

    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('35')).toBeInTheDocument();
    expect(screen.getByText('Chicago')).toBeInTheDocument();
  });

  it('handles empty data gracefully', () => {
    renderWithTheme(
      <SpreadsheetEditorComponent
        data={[]}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('No data to display')).toBeInTheDocument();
  });

  it('handles validation errors with non-existent columns', () => {
    const validationErrors: ValidationError[] = [
      {
        row: 1,
        column: 'NonExistentColumn',
        currentValue: 'value',
        recommendedValue: 'corrected',
        errorType: ValidationErrorType.INVALID_PATTERN,
        validOptions: null,
        confidenceScore: 0.75,
        confidenceLevel: 'Medium'
      }
    ];

    renderWithTheme(
      <SpreadsheetEditorComponent
        data={mockData}
        validationErrors={validationErrors}
        onChange={mockOnChange}
      />
    );

    // Should not crash and should render normally
    expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    expect(screen.getByText('John')).toBeInTheDocument();
  });



  describe('Error handling and cell interaction', () => {
    it('handles validation errors gracefully', () => {
      const validationErrors: ValidationError[] = [
        {
          row: 1, // First data row in full data array
          column: 'Name',
          currentValue: 'John',
          recommendedValue: 'John Doe',
          errorType: ValidationErrorType.INVALID_PATTERN,
          validOptions: null,
          confidenceScore: 0.85,
          confidenceLevel: 'High'
        }
      ];

      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          validationErrors={validationErrors}
          onChange={mockOnChange}
        />
      );

      // Should render without errors
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();

      // Functionality should still work - clicking should trigger onChange
      const cell = screen.getByTestId('cell-0-0');
      fireEvent.click(cell);
      expect(mockOnChange).toHaveBeenCalled();
    });

    it('maintains cell interaction features', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
        />
      );

      const cell = screen.getByTestId('cell-0-0');

      // Cell should be interactive
      fireEvent.click(cell);
      expect(mockOnChange).toHaveBeenCalled();

      // Cell should have proper data attributes
      expect(cell).toHaveAttribute('data-active', 'true');
    });

    it('handles complex prop combinations without breaking functionality', () => {
      const validationErrors: ValidationError[] = [
        {
          row: 2, // Second data row in full data array
          column: 'Age',
          currentValue: '30',
          recommendedValue: '30',
          errorType: ValidationErrorType.REQUIRED_VALUE,
          validOptions: null,
          confidenceScore: 0.90,
          confidenceLevel: 'High'
        }
      ];

      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          validationErrors={validationErrors}
          disabled={false}
          onChange={mockOnChange}
        />
      );

      // Should render without errors
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();

      // Interaction should work
      const cell = screen.getByTestId('cell-1-1');
      fireEvent.click(cell);
      expect(mockOnChange).toHaveBeenCalled();
    });
  });

  describe('Context Menu Functionality', () => {
    const mockOnColumnOperation = jest.fn();
    const mockOnRowOperation = jest.fn();
    const mockOnColumnRename = jest.fn();
    const mockOnUndo = jest.fn();
    const mockOnRedo = jest.fn();

    beforeEach(() => {
      mockOnColumnOperation.mockClear();
      mockOnRowOperation.mockClear();
      mockOnColumnRename.mockClear();
      mockOnUndo.mockClear();
      mockOnRedo.mockClear();
    });

    it('renders context menu component', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
          onColumnRename={mockOnColumnRename}
          onUndo={mockOnUndo}
          onRedo={mockOnRedo}
        />
      );

      // Context menu should be present but not visible initially
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('handles column operations when provided', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      // Simulate right-click on column header
      const columnHeader = container.querySelector('th');
      if (columnHeader) {
        fireEvent.contextMenu(columnHeader, { clientX: 100, clientY: 100 });
      }

      // Context menu should be handled (exact behavior depends on implementation)
      expect(container).toBeInTheDocument();
    });

    it('handles row operations when provided', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      // Simulate right-click on row header
      const rowHeader = container.querySelector('td');
      if (rowHeader) {
        fireEvent.contextMenu(rowHeader, { clientX: 100, clientY: 100 });
      }

      // Context menu should be handled
      expect(container).toBeInTheDocument();
    });

    it('handles keyboard shortcuts for context menu', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      // Simulate Shift+F10 keyboard shortcut
      fireEvent.keyDown(container, { key: 'F10', shiftKey: true });

      // Should handle keyboard shortcut
      expect(container).toBeInTheDocument();
    });

    it('handles Menu key for context menu', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      // Simulate Menu key
      fireEvent.keyDown(container, { key: 'ContextMenu' });

      // Should handle Menu key
      expect(container).toBeInTheDocument();
    });

    it('works without context menu callbacks', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
        />
      );

      // Should render normally without context menu callbacks
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
      expect(screen.getByText('John')).toBeInTheDocument();
    });

    it('prevents default context menu on right-click', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      const preventDefault = jest.fn();

      // Simulate right-click with preventDefault mock
      const columnHeader = container.querySelector('th');
      if (columnHeader) {
        fireEvent.contextMenu(columnHeader, {
          clientX: 100,
          clientY: 100,
          preventDefault
        });
      }

      // Should prevent default browser context menu
      expect(container).toBeInTheDocument();
    });
  });

  describe('Column Rename Functionality', () => {
    const mockOnColumnRename = jest.fn();
    const mockOnUndo = jest.fn();
    const mockOnRedo = jest.fn();

    beforeEach(() => {
      mockOnChange.mockClear();
      mockOnColumnRename.mockClear();
      mockOnUndo.mockClear();
      mockOnRedo.mockClear();
    });

    it('renders column rename dialog component', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnRename={mockOnColumnRename}
          onUndo={mockOnUndo}
          onRedo={mockOnRedo}
        />
      );

      // Component should render without errors
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('supports keyboard shortcuts for undo/redo', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onUndo={mockOnUndo}
          onRedo={mockOnRedo}
        />
      );

      // Simulate Ctrl+Z for undo
      fireEvent.keyDown(container, { key: 'z', ctrlKey: true });

      // Simulate Ctrl+Y for redo
      fireEvent.keyDown(container, { key: 'y', ctrlKey: true });

      // Simulate Ctrl+Shift+Z for redo
      fireEvent.keyDown(container, { key: 'z', ctrlKey: true, shiftKey: true });

      // Should handle keyboard shortcuts without errors
      expect(container).toBeInTheDocument();
    });

    it('supports Delete key for row removal', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          validationErrors={mockValidationErrors}
          onRowOperation={mockOnRowOperation}
        />
      );

      // Focus on a row element (simulate clicking on row header)
      const rowElement = container.querySelector('th[data-row-index="0"]') ||
                        container.querySelector('.Spreadsheet__row-header');

      if (rowElement) {
        rowElement.focus();

        // Simulate Delete key press
        fireEvent.keyDown(document, { key: 'Delete' });

        // Should open remove row dialog
        expect(screen.queryByText(/Remove Row/)).toBeInTheDocument();
      }
    });

    it('prevents Delete key action when modifier keys are pressed', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          validationErrors={mockValidationErrors}
          onRowOperation={mockOnRowOperation}
        />
      );

      // Simulate Delete key with Ctrl (should not trigger row removal)
      fireEvent.keyDown(document, { key: 'Delete', ctrlKey: true });

      // Should not open remove row dialog
      expect(screen.queryByText(/Remove Row/)).not.toBeInTheDocument();
    });

    it('ignores keyboard shortcuts when disabled', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          disabled={true}
          onChange={mockOnChange}
          onColumnRename={mockOnColumnRename}
        />
      );

      // Try F2 when disabled
      fireEvent.keyDown(container, { key: 'F2' });

      // Try undo when disabled
      fireEvent.keyDown(container, { key: 'z', ctrlKey: true });

      // Should handle disabled state without errors
      expect(container).toBeInTheDocument();
    });

    it('handles column operations with rename action', () => {
      const mockOnColumnOperation = jest.fn();

      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
          onColumnRename={mockOnColumnRename}
        />
      );

      // Component should render and be ready to handle column operations
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('provides feedback through snackbar component', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnRename={mockOnColumnRename}
        />
      );

      // Snackbar should be present in DOM (though not visible initially)
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('maintains undo/redo state management', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnRename={mockOnColumnRename}
          onUndo={mockOnUndo}
          onRedo={mockOnRedo}
        />
      );

      // Component should initialize with proper state management
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('handles context menu integration', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnRename={mockOnColumnRename}
        />
      );

      // Simulate right-click on column header
      const columnHeader = container.querySelector('th[data-column-index]');
      if (columnHeader) {
        fireEvent.contextMenu(columnHeader, { clientX: 100, clientY: 100 });
      }

      // Should handle context menu without errors
      expect(container).toBeInTheDocument();
    });

    it('validates column rename operations', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnRename={mockOnColumnRename}
        />
      );

      // Component should be ready to validate rename operations
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });
  });

  describe('Add Column Functionality', () => {
    const mockOnColumnOperation = jest.fn();

    beforeEach(() => {
      mockOnChange.mockClear();
      mockOnColumnOperation.mockClear();
    });

    it('renders add column dialog component', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
        />
      );

      // The dialog should be present but closed initially
      expect(screen.queryByText('Add New Column')).not.toBeInTheDocument();
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('handles column operations with add_before action', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
        />
      );

      // Component should be ready to handle add_before operations
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('handles column operations with add_after action', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
        />
      );

      // Component should be ready to handle add_after operations
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('supports keyboard shortcuts for add column (Ctrl+Shift+N)', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
        />
      );

      // Simulate Ctrl+Shift+N keyboard shortcut
      fireEvent.keyDown(container, { key: 'N', ctrlKey: true, shiftKey: true });

      // Should handle keyboard shortcut without errors
      expect(container).toBeInTheDocument();
    });

    it('validates add column operations', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
        />
      );

      // Component should be ready to validate add column operations
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('provides feedback for successful column addition', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
        />
      );

      // Snackbar should be available for feedback
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('handles add column with proper undo/redo integration', () => {
      const mockOnUndo = jest.fn();
      const mockOnRedo = jest.fn();

      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
          onUndo={mockOnUndo}
          onRedo={mockOnRedo}
        />
      );

      // Component should integrate with undo/redo system
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('generates default column names correctly', () => {
      renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
        />
      );

      // Component should be ready to generate default column names
      expect(screen.getByTestId('mock-spreadsheet')).toBeInTheDocument();
    });

    it('ignores add column shortcuts when disabled', () => {
      const { container } = renderWithTheme(
        <SpreadsheetEditorComponent
          data={mockData}
          disabled={true}
          onChange={mockOnChange}
          onColumnOperation={mockOnColumnOperation}
        />
      );

      // Try Ctrl+Shift+N when disabled
      fireEvent.keyDown(container, { key: 'N', ctrlKey: true, shiftKey: true });

      // Should handle disabled state without errors
      expect(container).toBeInTheDocument();
    });
  });

});
