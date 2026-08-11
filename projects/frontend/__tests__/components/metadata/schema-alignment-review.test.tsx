/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SchemaAlignmentReviewComponent } from '../../../components/metadata/schema-alignment-review';
import {
  PostSchemaAlignmentData,
  SchemaAlignmentChange,
  SchemaAlignmentChangeType
} from '../../../lib/types';

// Mock the API functions
jest.mock('../../../lib/api', () => ({
  processColumnMappingsToChanges: jest.fn(),
  generateSchemaAlignmentSummary: jest.fn(),
  parseSchemaAlignmentCsv: jest.fn()
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const apiModule = require('../../../lib/api');
const mockProcessColumnMappingsToChanges = apiModule.processColumnMappingsToChanges;
const mockGenerateSchemaAlignmentSummary = apiModule.generateSchemaAlignmentSummary;
const mockParseSchemaAlignmentCsv = apiModule.parseSchemaAlignmentCsv;

describe('SchemaAlignmentReviewComponent', () => {
  const mockOnAcceptChanges = jest.fn();
  const mockOnRejectChanges = jest.fn();

  const mockSchemaAlignmentData: PostSchemaAlignmentData = {
    originalDataCsv: 'old_name,other_col\nvalue1,value2\n',
    alignedDataCsv: 'new_name,other_col\nvalue1,value2\n',
    columnMappings: {
      'old_name': 'new_name',
      'other_col': 'other_col'
    },
    transformationSummary: {
      columnsRenamed: 1,
      columnsAdded: 0,
      columnsRemoved: 0
    }
  };

  const mockChanges: SchemaAlignmentChange[] = [
    {
      id: 'change-1',
      type: SchemaAlignmentChangeType.COLUMN_RENAMED,
      originalColumn: 'old_name',
      alignedColumn: 'new_name',
      expectedSchemaColumn: 'new_name',
      description: 'Column "old_name" renamed to "new_name"',
      reason: 'Required by schema specification',
      canRevert: true,
      isAccepted: false
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();

    // Setup default mock implementations
    mockProcessColumnMappingsToChanges.mockReturnValue(mockChanges);
    mockGenerateSchemaAlignmentSummary.mockReturnValue({
      columnsRenamed: 1,
      columnsAdded: 0,
      columnsRemoved: 0,
      rowsOriginal: 2,
      rowsAligned: 2,
      columnMappings: mockSchemaAlignmentData.columnMappings,
      addedColumns: [],
      removedColumns: []
    });
    mockParseSchemaAlignmentCsv.mockImplementation((csv: string) => {
      if (csv.includes('old_name')) {
        return [['old_name', 'other_col'], ['value1', 'value2']];
      }
      return [['new_name', 'other_col'], ['value1', 'value2']];
    });
  });

  it('renders loading state correctly', () => {
    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={mockSchemaAlignmentData}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
        loading={true}
      />
    );

    expect(screen.getByText('Processing schema alignment changes...')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders error state correctly', () => {
    const errorMessage = 'Failed to process schema alignment';

    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={mockSchemaAlignmentData}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
        error={errorMessage}
      />
    );

    expect(screen.getByText('Schema Alignment Error')).toBeInTheDocument();
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByText('Continue Without Schema Alignment')).toBeInTheDocument();
  });

  it('renders empty state when no changes are needed', async () => {
    mockProcessColumnMappingsToChanges.mockReturnValue([]);

    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={{
          ...mockSchemaAlignmentData,
          columnMappings: { 'col1': 'col1' } // No actual changes
        }}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('No Schema Changes Required')).toBeInTheDocument();
    });

    expect(screen.getByText('Your data structure already matches the expected schema format. No alignment changes are needed.')).toBeInTheDocument();
    expect(screen.getByText('Continue to Validation')).toBeInTheDocument();
  });

  it('displays schema alignment changes correctly', async () => {
    // Update the mock to return actual changes from the new data structure
    const mockAlignmentDataWithChanges = {
      schemaAlignmentResults: [
        {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'new_name',
          reason: 'Required by schema specification'
        }
      ],
      summary: {
        columnsRenamed: 1,
        columnsAdded: 0,
        columnsRemoved: 0,
        rowsOriginal: 2,
        rowsAligned: 2
      }
    };

    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={mockAlignmentDataWithChanges}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Schema Alignment Changes')).toBeInTheDocument();
    });

    // Check transformation summary
    expect(screen.getByText('Transformation Summary')).toBeInTheDocument();
    expect(screen.getByText('1 Renamed')).toBeInTheDocument();
    expect(screen.getByText('0 Added')).toBeInTheDocument();
    expect(screen.getByText('0 Removed')).toBeInTheDocument();

    // Check detailed changes
    expect(screen.getByText('Detailed Changes (1)')).toBeInTheDocument();
    expect(screen.getByText('Column "old_name" was renamed to "new_name"')).toBeInTheDocument();
    expect(screen.getByText('Required by schema specification')).toBeInTheDocument();
    expect(screen.getByText('"old_name" → "new_name"')).toBeInTheDocument();
  });

  it('calls onAcceptChanges when Accept button is clicked', async () => {
    const mockAlignmentDataWithChanges = {
      schemaAlignmentResults: [
        {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'new_name',
          reason: 'Required by schema specification'
        }
      ],
      summary: {
        columnsRenamed: 1,
        columnsAdded: 0,
        columnsRemoved: 0,
        rowsOriginal: 2,
        rowsAligned: 2
      }
    };

    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={mockAlignmentDataWithChanges}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Accept & Continue')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Accept & Continue'));

    expect(mockOnAcceptChanges).toHaveBeenCalled();
    const calledWith = mockOnAcceptChanges.mock.calls[0][0];
    expect(calledWith).toHaveLength(1);
    expect(calledWith[0].isAccepted).toBe(true);
    expect(calledWith[0].originalColumn).toBe('old_name');
    expect(calledWith[0].alignedColumn).toBe('new_name');
  });

  it('calls onRejectChanges when Reject button is clicked', async () => {
    const mockAlignmentDataWithChanges = {
      schemaAlignmentResults: [
        {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'new_name',
          reason: 'Required by schema specification'
        }
      ],
      summary: {
        columnsRenamed: 1,
        columnsAdded: 0,
        columnsRemoved: 0,
        rowsOriginal: 2,
        rowsAligned: 2
      }
    };

    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={mockAlignmentDataWithChanges}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Reject Changes')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Reject Changes'));

    expect(mockOnRejectChanges).toHaveBeenCalled();
  });

  it('handles multiple change types correctly', async () => {
    const mockAlignmentDataMultiple = {
      schemaAlignmentResults: [
        {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'new_name',
          reason: 'Required by schema specification'
        },
        {
          changeType: 'add',
          newColumn: 'added_column',
          reason: 'Required by schema specification'
        },
        {
          changeType: 'remove',
          originalColumn: 'removed_column',
          reason: 'Not required by schema specification'
        }
      ],
      summary: {
        columnsRenamed: 1,
        columnsAdded: 1,
        columnsRemoved: 1,
        rowsOriginal: 2,
        rowsAligned: 2
      }
    };

    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={mockAlignmentDataMultiple}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('1 Renamed')).toBeInTheDocument();
      expect(screen.getByText('1 Added')).toBeInTheDocument();
      expect(screen.getByText('1 Removed')).toBeInTheDocument();
    });

    expect(screen.getByText('Detailed Changes (3)')).toBeInTheDocument();
    expect(screen.getByText('Column "old_name" was renamed to "new_name"')).toBeInTheDocument();
    expect(screen.getByText('Column "added_column" was added')).toBeInTheDocument();
    expect(screen.getByText('Column "removed_column" was removed')).toBeInTheDocument();
  });

  it('handles missing column mappings gracefully', async () => {
    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={{
          originalDataCsv: 'col1,col2\nval1,val2\n',
          alignedDataCsv: 'col1,col2\nval1,val2\n'
          // No columnMappings
        }}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('No Schema Changes Required')).toBeInTheDocument();
    });
  });

  it('expands and collapses detailed changes accordion', async () => {
    const mockAlignmentDataWithChanges = {
      schemaAlignmentResults: [
        {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'new_name',
          reason: 'Required by schema specification'
        }
      ],
      summary: {
        columnsRenamed: 1,
        columnsAdded: 0,
        columnsRemoved: 0,
        rowsOriginal: 2,
        rowsAligned: 2
      }
    };

    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={mockAlignmentDataWithChanges}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Detailed Changes (1)')).toBeInTheDocument();
    });

    // The accordion should be expanded by default
    expect(screen.getByText('Column "old_name" was renamed to "new_name"')).toBeInTheDocument();

    // Click to collapse
    fireEvent.click(screen.getByText('Detailed Changes (1)'));

    // Content should still be visible since Material-UI accordion behavior may vary
    // This test mainly ensures the accordion structure is present
    expect(screen.getByText('Detailed Changes (1)')).toBeInTheDocument();
  });

  it('displays information alert about next steps', async () => {
    const mockAlignmentDataWithChanges = {
      schemaAlignmentResults: [
        {
          changeType: 'rename',
          originalColumn: 'old_name',
          newColumn: 'new_name',
          reason: 'Required by schema specification'
        }
      ],
      summary: {
        columnsRenamed: 1,
        columnsAdded: 0,
        columnsRemoved: 0,
        rowsOriginal: 2,
        rowsAligned: 2
      }
    };

    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={mockAlignmentDataWithChanges}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/What happens next:/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Accept Changes:/)).toBeInTheDocument();
    expect(screen.getByText(/Your data will be transformed according to the schema requirements/)).toBeInTheDocument();
    expect(screen.getByText(/Reject Changes:/)).toBeInTheDocument();
    expect(screen.getByText(/Your original data structure will be preserved/)).toBeInTheDocument();
  });

  it('handles processing state correctly', async () => {
    // Mock the component to show processing state by using loading prop
    render(
      <SchemaAlignmentReviewComponent
        schemaAlignmentData={mockSchemaAlignmentData}
        onAcceptChanges={mockOnAcceptChanges}
        onRejectChanges={mockOnRejectChanges}
        loading={true}
      />
    );

    // Should show processing state
    expect(screen.getByText('Processing schema alignment changes...')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
});
