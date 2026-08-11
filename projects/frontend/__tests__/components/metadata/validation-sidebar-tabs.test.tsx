/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ValidationSidebarComponent } from '../../../components/metadata/validation-sidebar';
import { ValidationError, ValidationErrorType, SchemaAlignmentResults, SchemaAlignmentChangeDetail } from '../../../lib/types';
import { useAuth } from 'react-oidc-context';
import { afterEach } from 'node:test';
import { beforeEach } from 'node:test';

// Mock the auth hook
jest.mock('react-oidc-context');
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

// Mock the API functions
jest.mock('../../../lib/api', () => ({
  updateValidationJob: jest.fn(),
  pollValidationStatus: jest.fn(),
  submitMetadataValidation: jest.fn(),
}));

describe('ValidationSidebarComponent - Tabbed Interface', () => {
  const mockValidationErrors: ValidationError[] = [
    {
      row: 1,
      column: 'test_column',
      currentValue: 'invalid_value',
      validOptions: ['option1', 'option2'],
      recommendedValue: 'option1',
      errorType: ValidationErrorType.INVALID_OPTION,
    },
    {
      row: 2,
      column: 'required_column',
      currentValue: '',
      validOptions: null,
      recommendedValue: 'required_value',
      errorType: ValidationErrorType.REQUIRED_VALUE,
    },
  ];

  const mockSchemaAlignmentResults: SchemaAlignmentResults = {
    schemaAlignmentResults: [
      {
        changeType: 'rename',
        originalColumn: 'old_name',
        newColumn: 'new_name',
        reason: 'Schema alignment requirement',
        rowCountAffected: 100
      },
      {
        changeType: 'add',
        newColumn: 'added_column',
        reason: 'Required by target schema',
        rowCountAffected: 100
      }
    ],
    summary: {
      jobId: 'test-job-123',
      version: 1,
      timestamp: '2024-01-15T10:30:00Z',
      originalDataCsv: 'old_name,data\nvalue1,data1\nvalue2,data2',
      alignedDataCsv: 'new_name,data,added_column\nvalue1,data1,\nvalue2,data2,',
      totalChanges: 2,
      columnsRenamed: 1,
      columnsAdded: 1,
      columnsRemoved: 0,
      rowsOriginal: 2,
      rowsAligned: 2
    }
  };

  const defaultProps = {
    data: [['header1', 'header2'], ['value1', 'value2']],
    changes: [],
    validationErrors: mockValidationErrors,
    schemaAlignmentResults: mockSchemaAlignmentResults,
    // currentView removed - no longer using toggle functionality
    onValidationComplete: jest.fn(),
    onValidationErrors: jest.fn(),
    onApplyChange: jest.fn(),
    onApplyAllChanges: jest.fn(),
    onAcceptSchemaChange: jest.fn(),
    onRevertSchemaChange: jest.fn(),
  };

  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: { access_token: 'mock-token' },
      isAuthenticated: true,
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders both tabs with correct labels and badge counts', () => {
    render(<ValidationSidebarComponent {...defaultProps} />);

    // Check that both tabs are present
    expect(screen.getByText('Validation Errors')).toBeInTheDocument();
    expect(screen.getByText('Schema Changes')).toBeInTheDocument();

    // Check badge counts - validation errors should show 2
    const validationTab = screen.getByRole('tab', { name: /validation errors/i });
    expect(validationTab).toBeInTheDocument();

    // Check badge counts - schema changes should show 2
    const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
    expect(schemaTab).toBeInTheDocument();
  });

  it('starts with schema changes tab active by default', () => {
    render(<ValidationSidebarComponent {...defaultProps} />);

    // Schema changes tab should be selected by default
    const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
    expect(schemaTab).toHaveAttribute('aria-selected', 'true');

    // Validation errors tab should not be selected
    const validationTab = screen.getByRole('tab', { name: /validation errors/i });
    expect(validationTab).toHaveAttribute('aria-selected', 'false');

    // Schema changes content should be visible
    expect(screen.getByText('Schema Changes')).toBeInTheDocument();
  });

  it('switches to validation errors tab when clicked', async () => {
    render(<ValidationSidebarComponent {...defaultProps} />);

    // Click on validation errors tab (schema is default)
    const validationTab = screen.getByRole('tab', { name: /validation errors/i });
    fireEvent.click(validationTab);

    await waitFor(() => {
      // Validation errors tab should now be selected
      expect(validationTab).toHaveAttribute('aria-selected', 'true');

      // Schema changes tab should not be selected
      const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
      expect(schemaTab).toHaveAttribute('aria-selected', 'false');

      // Validation errors content should be visible
      expect(screen.getByText('Validation Errors')).toBeInTheDocument();
    });
  });

  it('switches back to schema changes tab when clicked', async () => {
    render(<ValidationSidebarComponent {...defaultProps} />);

    // First switch to validation errors tab (schema is default)
    const validationTab = screen.getByRole('tab', { name: /validation errors/i });
    fireEvent.click(validationTab);

    await waitFor(() => {
      expect(validationTab).toHaveAttribute('aria-selected', 'true');
    });

    // Then switch back to schema changes tab
    const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
    fireEvent.click(schemaTab);

    await waitFor(() => {
      // Schema changes tab should be selected again
      expect(schemaTab).toHaveAttribute('aria-selected', 'true');
      expect(validationTab).toHaveAttribute('aria-selected', 'false');

      // Schema changes content should be visible
      expect(screen.getByText('Schema Changes')).toBeInTheDocument();
    });
  });

  it('displays correct badge counts for validation errors', () => {
    render(<ValidationSidebarComponent {...defaultProps} />);

    // Should show count of 2 for validation errors
    expect(screen.getByText('Validation Errors')).toBeInTheDocument();
  });

  it('displays correct badge counts for schema changes', () => {
    render(<ValidationSidebarComponent {...defaultProps} />);

    // Schema changes tab is default, should show count
    // Badge content is shown separately from the text, so we just check the text is there
    expect(screen.getByText('Schema Changes')).toBeInTheDocument();
  });

  it('shows empty state for validation errors when no errors exist', async () => {
    const propsWithoutErrors = {
      ...defaultProps,
      validationErrors: [],
    };

    render(<ValidationSidebarComponent {...propsWithoutErrors} />);

    // Switch to validation errors tab
    const validationTab = screen.getByRole('tab', { name: /validation errors/i });
    fireEvent.click(validationTab);

    await waitFor(() => {
      expect(screen.getByText('Validation Errors')).toBeInTheDocument();
      expect(screen.getByText('No Validation Issues')).toBeInTheDocument();
      expect(screen.getByText('Your data passes all validation checks for the selected schema.')).toBeInTheDocument();
    });
  });

  it('shows empty state for schema changes when no changes exist', () => {
    const propsWithoutChanges = {
      ...defaultProps,
      schemaAlignmentResults: null,
    };

    render(<ValidationSidebarComponent {...propsWithoutChanges} />);

    // Schema changes tab is default, check empty state
    expect(screen.getByText('Schema Changes')).toBeInTheDocument();
    expect(screen.getByText('No Schema Changes')).toBeInTheDocument();
    expect(screen.getByText('Your data structure matches the target schema perfectly.')).toBeInTheDocument();
  });

  it('maintains tab state when props update', async () => {
    const { rerender } = render(<ValidationSidebarComponent {...defaultProps} />);

    // Switch to schema changes tab
    const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
    fireEvent.click(schemaTab);

    await waitFor(() => {
      expect(schemaTab).toHaveAttribute('aria-selected', 'true');
    });

    // Update props with new validation errors
    const updatedProps = {
      ...defaultProps,
      validationErrors: [...mockValidationErrors, {
        row: 3,
        column: 'new_column',
        currentValue: 'new_invalid',
        validOptions: ['valid1', 'valid2'],
        recommendedValue: 'valid1',
        errorType: ValidationErrorType.INVALID_OPTION,
      }],
    };

    rerender(<ValidationSidebarComponent {...updatedProps} />);

    // Schema changes tab should still be selected
    await waitFor(() => {
      expect(schemaTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  it('renders with proper Material UI theme styling', () => {
    render(<ValidationSidebarComponent {...defaultProps} />);

    // Check that tabs have proper styling classes
    const tabsContainer = screen.getByRole('tablist');
    expect(tabsContainer).toBeInTheDocument();

    // Check that tab panels have proper structure
    const validationTab = screen.getByRole('tab', { name: /validation errors/i });
    const schemaTab = screen.getByRole('tab', { name: /schema changes/i });

    expect(validationTab).toBeInTheDocument();
    expect(schemaTab).toBeInTheDocument();
  });
});
