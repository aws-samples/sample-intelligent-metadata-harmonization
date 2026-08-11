/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MetadataEditorComponent } from '../../components/metadata/metadata-editor';
import { SchemaAlignmentResults, ValidationError } from '../../lib/types';

// Mock the child components
jest.mock('../../components/metadata/spreadsheet-editor', () => ({
  SpreadsheetEditorComponent: ({ data }: any) => (
    <div data-testid="spreadsheet-editor">
      <div data-testid="spreadsheet-data">{JSON.stringify(data)}</div>
    </div>
  )
}));

jest.mock('../../components/metadata/validation-sidebar', () => ({
  ValidationSidebarComponent: ({ schemaAlignmentResults, appliedSchemaChangeIds }: any) => (
    <div data-testid="validation-sidebar">
      <div data-testid="schema-changes-count">
        {schemaAlignmentResults?.schemaAlignmentResults?.length || 0}
      </div>
      <div data-testid="applied-changes-count">
        {appliedSchemaChangeIds?.size || 0}
      </div>
    </div>
  )
}));

describe('MetadataEditorComponent - Manual Schema Changes', () => {
  const mockOriginalData = [
    ['old_column', 'existing_column'],
    ['value1', 'data1'],
    ['value2', 'data2']
  ];

  const mockAlignedData = [
    ['new_column', 'existing_column', 'added_column'],
    ['value1', 'data1', ''],
    ['value2', 'data2', '']
  ];

  const mockSchemaAlignmentResults: SchemaAlignmentResults = {
    summary: {
      jobId: 'test-job-123',
      version: 1,
      timestamp: '2024-01-01T00:00:00Z',
      originalDataCsv: 'old_column,existing_column\nvalue1,data1\nvalue2,data2',
      alignedDataCsv: 'new_column,existing_column,added_column\nvalue1,data1,\nvalue2,data2,',
      totalChanges: 2,
      columnsRenamed: 1,
      columnsAdded: 1,
      columnsRemoved: 0,
      rowsOriginal: 2,
      rowsAligned: 2
    },
    schemaAlignmentResults: [
      {
        changeType: 'rename',
        originalColumn: 'old_column',
        newColumn: 'new_column',
        reason: 'Column name standardization',
        rowCountAffected: 2
      },
      {
        changeType: 'add',
        newColumn: 'added_column',
        reason: 'Required field missing',
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

  it('should use original data, not aligned data, when schema alignment results are provided', async () => {
    render(
      <MetadataEditorComponent
        csvData={mockOriginalData}
        schemaAlignmentResults={mockSchemaAlignmentResults}
        {...mockCallbacks}
      />
    );

    // Wait for component to process the schema alignment results
    await waitFor(() => {
      expect(screen.getByTestId('spreadsheet-editor')).toBeInTheDocument();
    });

    // Verify that the spreadsheet is showing original data, not aligned data
    const spreadsheetData = screen.getByTestId('spreadsheet-data');
    const displayedData = JSON.parse(spreadsheetData.textContent || '[]');

    // Should show original data structure
    expect(displayedData).toEqual(mockOriginalData);
    expect(displayedData[0]).toEqual(['old_column', 'existing_column']); // Original headers
    expect(displayedData[0]).not.toEqual(['new_column', 'existing_column', 'added_column']); // Not aligned headers
  });

  it('should not auto-apply schema changes when schema alignment results are provided', async () => {
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

    // Verify that schema changes are detected
    const schemaChangesCount = screen.getByTestId('schema-changes-count');
    expect(schemaChangesCount.textContent).toBe('2'); // 2 changes detected

    // Verify that NO changes are marked as applied (should be 0, not 2)
    const appliedChangesCount = screen.getByTestId('applied-changes-count');
    expect(appliedChangesCount.textContent).toBe('0'); // No changes auto-applied
  });

  it('should maintain original data structure even when aligned data is available', async () => {
    render(
      <MetadataEditorComponent
        csvData={mockOriginalData}
        schemaAlignmentResults={mockSchemaAlignmentResults}
        {...mockCallbacks}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('spreadsheet-editor')).toBeInTheDocument();
    });

    const spreadsheetData = screen.getByTestId('spreadsheet-data');
    const displayedData = JSON.parse(spreadsheetData.textContent || '[]');

    // Verify original structure is preserved
    expect(displayedData).toHaveLength(3); // Header + 2 data rows
    expect(displayedData[0]).toHaveLength(2); // Original 2 columns, not 3
    expect(displayedData[0]).toContain('old_column'); // Original column name
    expect(displayedData[0]).not.toContain('new_column'); // Not renamed
    expect(displayedData[0]).not.toContain('added_column'); // Not added
  });

  it('should reset applied changes to empty when new schema alignment results are received', async () => {
    // First render with some applied changes (simulating previous state)
    const { rerender } = render(
      <MetadataEditorComponent
        csvData={mockOriginalData}
        {...mockCallbacks}
      />
    );

    // Now provide schema alignment results - should reset applied changes
    rerender(
      <MetadataEditorComponent
        csvData={mockOriginalData}
        schemaAlignmentResults={mockSchemaAlignmentResults}
        {...mockCallbacks}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('validation-sidebar')).toBeInTheDocument();
    });

    // Verify that applied changes are reset to 0
    const appliedChangesCount = screen.getByTestId('applied-changes-count');
    expect(appliedChangesCount.textContent).toBe('0');
  });

  it('should preserve original data when no schema alignment results are provided', async () => {
    render(
      <MetadataEditorComponent
        csvData={mockOriginalData}
        {...mockCallbacks}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('spreadsheet-editor')).toBeInTheDocument();
    });

    const spreadsheetData = screen.getByTestId('spreadsheet-data');
    const displayedData = JSON.parse(spreadsheetData.textContent || '[]');

    // Should exactly match the input data
    expect(displayedData).toEqual(mockOriginalData);
  });
});
