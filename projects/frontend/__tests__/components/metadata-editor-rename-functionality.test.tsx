/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MetadataEditorComponent } from '../../components/metadata/metadata-editor';
import { SchemaAlignmentResults } from '../../lib/types';

interface MockSpreadsheetEditorProps {
  data: string[][];
}

interface MockValidationSidebarProps {
  schemaAlignmentResults?: SchemaAlignmentResults;
  appliedSchemaChangeIds?: Set<string>;
  onApplyColumnRename?: (originalColumn: string, newColumn: string) => void;
  onApplyColumnAddition?: (newColumn: string) => void;
  onApplyColumnRemoval?: (columnName: string) => void;
}

// Mock the child components with React state support
jest.mock('../../components/metadata/spreadsheet-editor', () => ({
  SpreadsheetEditorComponent: ({ data }: MockSpreadsheetEditorProps) => {
    // Use a key to force re-render when data changes
    const dataKey = JSON.stringify(data[0]);
    return (
      <div data-testid="spreadsheet-editor" key={dataKey}>
        <div data-testid="spreadsheet-headers">{JSON.stringify(data[0])}</div>
        <div data-testid="spreadsheet-data">{JSON.stringify(data)}</div>
      </div>
    );
  }
}));

jest.mock('../../components/metadata/validation-sidebar', () => ({
  ValidationSidebarComponent: ({
    schemaAlignmentResults,
    appliedSchemaChangeIds,
    onApplyColumnRename,
    onApplyColumnAddition,
    onApplyColumnRemoval
  }: MockValidationSidebarProps) => {
    const applyAllChanges = () => {
      if (!schemaAlignmentResults?.schemaAlignmentResults) return;

      // Apply all schema changes in sequence
      schemaAlignmentResults.schemaAlignmentResults.forEach((change) => {
        if (change.changeType === 'rename' && onApplyColumnRename) {
          onApplyColumnRename(change.originalColumn || '', change.newColumn || '');
        } else if (change.changeType === 'add' && onApplyColumnAddition) {
          onApplyColumnAddition(change.newColumn || '');
        } else if (change.changeType === 'remove' && onApplyColumnRemoval) {
          onApplyColumnRemoval(change.originalColumn || '');
        }
      });
    };

    return (
      <div data-testid="validation-sidebar">
        <div data-testid="schema-changes-count">
          {schemaAlignmentResults?.schemaAlignmentResults?.length || 0}
        </div>
        <div data-testid="applied-changes-count">
          {appliedSchemaChangeIds?.size || 0}
        </div>
        <button
          data-testid="apply-rename-button"
          onClick={() => {
            const change = schemaAlignmentResults?.schemaAlignmentResults?.find((c) => c.changeType === 'rename');
            if (change && onApplyColumnRename) {
              onApplyColumnRename(change.originalColumn || '', change.newColumn || '');
            }
          }}
        >
          Apply Rename
        </button>
        <button
          data-testid="apply-all-button"
          onClick={applyAllChanges}
        >
          Accept All
        </button>
        <button
          data-testid="apply-first-rename"
          onClick={() => {
            const change = schemaAlignmentResults?.schemaAlignmentResults?.[0];
            if (change?.changeType === 'rename' && onApplyColumnRename) {
              onApplyColumnRename(change.originalColumn || '', change.newColumn || '');
            }
          }}
        >
          Apply First Rename
        </button>
        <button
          data-testid="apply-second-rename"
          onClick={() => {
            const change = schemaAlignmentResults?.schemaAlignmentResults?.[1];
            if (change?.changeType === 'rename' && onApplyColumnRename) {
              onApplyColumnRename(change.originalColumn || '', change.newColumn || '');
            }
          }}
        >
          Apply Second Rename
        </button>
      </div>
    );
  }
}));

describe('MetadataEditorComponent - Rename Functionality', () => {
  const mockOriginalData = [
    ['old_column_name', 'existing_column'],
    ['value1', 'data1'],
    ['value2', 'data2']
  ];

  const mockSchemaAlignmentResults: SchemaAlignmentResults = {
    summary: {
      jobId: 'test-job-123',
      version: 1,
      timestamp: '2024-01-01T00:00:00Z',
      originalDataCsv: 'old_column_name,existing_column\nvalue1,data1\nvalue2,data2',
      alignedDataCsv: 'new_column_name,existing_column\nvalue1,data1\nvalue2,data2',
      totalChanges: 1,
      columnsRenamed: 1,
      columnsAdded: 0,
      columnsRemoved: 0,
      rowsOriginal: 2,
      rowsAligned: 2
    },
    schemaAlignmentResults: [
      {
        changeType: 'rename',
        originalColumn: 'old_column_name',
        newColumn: 'new_column_name',
        reason: 'Column name standardization',
        rowCountAffected: 2
      }
    ]
  };

  const mockCallbacks = {
    onValidationComplete: jest.fn(),
    onValidationErrors: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should apply individual column rename correctly', async () => {
    render(
      <MetadataEditorComponent
        csvData={mockOriginalData}
        schemaAlignmentResults={mockSchemaAlignmentResults}
        {...mockCallbacks}
      />
    );

    // Wait for component to process the schema alignment results
    await waitFor(() => {
      expect(screen.getByTestId('validation-sidebar')).toBeInTheDocument();
    });

    // Verify initial state - original column name
    const initialHeaders = screen.getByTestId('spreadsheet-headers');
    expect(JSON.parse(initialHeaders.textContent || '[]')).toEqual(['old_column_name', 'existing_column']);

    // Apply the rename
    const applyRenameButton = screen.getByTestId('apply-rename-button');
    fireEvent.click(applyRenameButton);

    // Wait for the rename to be applied
    await waitFor(() => {
      const updatedHeaders = screen.getByTestId('spreadsheet-headers');
      const headers = JSON.parse(updatedHeaders.textContent || '[]');
      expect(headers).toEqual(['new_column_name', 'existing_column']);
    });

    // Verify that the change is marked as applied
    const appliedChangesCount = screen.getByTestId('applied-changes-count');
    expect(appliedChangesCount.textContent).toBe('1');
  });

  it('should apply all changes including rename correctly', async () => {
    render(
      <MetadataEditorComponent
        csvData={mockOriginalData}
        schemaAlignmentResults={mockSchemaAlignmentResults}
        {...mockCallbacks}
      />
    );

    // Wait for component to process the schema alignment results
    await waitFor(() => {
      expect(screen.getByTestId('validation-sidebar')).toBeInTheDocument();
    });

    // Verify initial state - original column name
    const initialHeaders = screen.getByTestId('spreadsheet-headers');
    expect(JSON.parse(initialHeaders.textContent || '[]')).toEqual(['old_column_name', 'existing_column']);

    // Apply all changes
    const applyAllButton = screen.getByTestId('apply-all-button');
    fireEvent.click(applyAllButton);

    // Wait for the changes to be applied
    await waitFor(() => {
      const updatedHeaders = screen.getByTestId('spreadsheet-headers');
      const headers = JSON.parse(updatedHeaders.textContent || '[]');
      expect(headers).toEqual(['new_column_name', 'existing_column']);
    });

    // Verify that the change is marked as applied
    const appliedChangesCount = screen.getByTestId('applied-changes-count');
    expect(appliedChangesCount.textContent).toBe('1');
  });

  it('should maintain data integrity during rename', async () => {
    render(
      <MetadataEditorComponent
        csvData={mockOriginalData}
        schemaAlignmentResults={mockSchemaAlignmentResults}
        {...mockCallbacks}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('validation-sidebar')).toBeInTheDocument();
    });

    // Apply the rename
    const applyRenameButton = screen.getByTestId('apply-rename-button');
    fireEvent.click(applyRenameButton);

    // Wait for the rename to be applied
    await waitFor(() => {
      const updatedData = screen.getByTestId('spreadsheet-data');
      const data = JSON.parse(updatedData.textContent || '[]');

      // Verify that only the header changed, data rows remain the same
      expect(data).toEqual([
        ['new_column_name', 'existing_column'], // Header changed
        ['value1', 'data1'],                    // Data unchanged
        ['value2', 'data2']                     // Data unchanged
      ]);
    });
  });

  it('should handle multiple renames correctly', async () => {
    const multipleRenamesData = [
      ['old_col1', 'old_col2', 'unchanged_col'],
      ['val1', 'val2', 'val3'],
      ['val4', 'val5', 'val6']
    ];

    const multipleRenamesResults: SchemaAlignmentResults = {
      summary: {
        jobId: 'test-job-456',
        version: 1,
        timestamp: '2024-01-01T00:00:00Z',
        originalDataCsv: 'old_col1,old_col2,unchanged_col\nval1,val2,val3\nval4,val5,val6',
        alignedDataCsv: 'new_col1,new_col2,unchanged_col\nval1,val2,val3\nval4,val5,val6',
        totalChanges: 2,
        columnsRenamed: 2,
        columnsAdded: 0,
        columnsRemoved: 0,
        rowsOriginal: 2,
        rowsAligned: 2
      },
      schemaAlignmentResults: [
        {
          changeType: 'rename',
          originalColumn: 'old_col1',
          newColumn: 'new_col1',
          reason: 'Standardization',
          rowCountAffected: 2
        },
        {
          changeType: 'rename',
          originalColumn: 'old_col2',
          newColumn: 'new_col2',
          reason: 'Standardization',
          rowCountAffected: 2
        }
      ]
    };

    render(
      <MetadataEditorComponent
        csvData={multipleRenamesData}
        schemaAlignmentResults={multipleRenamesResults}
        {...mockCallbacks}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('validation-sidebar')).toBeInTheDocument();
    });

    // Verify initial state
    let updatedHeaders = screen.getByTestId('spreadsheet-headers');
    let headers = JSON.parse(updatedHeaders.textContent || '[]');
    expect(headers).toEqual(['old_col1', 'old_col2', 'unchanged_col']);

    // Apply first rename
    const applyFirstButton = screen.getByTestId('apply-first-rename');
    fireEvent.click(applyFirstButton);

    // Wait for first rename to be applied
    await waitFor(() => {
      updatedHeaders = screen.getByTestId('spreadsheet-headers');
      headers = JSON.parse(updatedHeaders.textContent || '[]');
      expect(headers).toEqual(['new_col1', 'old_col2', 'unchanged_col']);
    });

    // Apply second rename
    const applySecondButton = screen.getByTestId('apply-second-rename');
    fireEvent.click(applySecondButton);

    // Wait for second rename to be applied
    await waitFor(() => {
      updatedHeaders = screen.getByTestId('spreadsheet-headers');
      headers = JSON.parse(updatedHeaders.textContent || '[]');
      expect(headers).toEqual(['new_col1', 'new_col2', 'unchanged_col']);
    });

    // Verify that both changes are marked as applied
    const appliedChangesCount = screen.getByTestId('applied-changes-count');
    expect(appliedChangesCount.textContent).toBe('2');
  });
});
