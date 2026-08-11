/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ValidationSidebarComponent } from '../../../components/metadata/validation-sidebar';
import { Change, ValidationError, ValidationErrorType } from '../../../lib/types';

// Mock the auth hook
jest.mock('react-oidc-context', () => ({
  useAuth: jest.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>
}));
const mockUseAuth = require('react-oidc-context').useAuth as jest.MockedFunction<any>;

// Mock the API functions
jest.mock('../../../lib/api', () => ({
  updateValidationJob: jest.fn(),
  pollValidationStatus: jest.fn(),
  submitMetadataValidation: jest.fn(),
}));

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('ValidationSidebarComponent', () => {
  const mockData = [
    ['Name', 'Age', 'City'],
    ['John', '25', 'New York'],
    ['Jane', '30', 'Boston']
  ];

  const mockChanges: Change[] = [
    {
      row: 1,
      column: 0,
      oldValue: 'John',
      newValue: 'John Doe',
      timestamp: new Date('2024-01-01T10:00:00Z')
    },
    {
      row: 2,
      column: 1,
      oldValue: '30',
      newValue: '31',
      timestamp: new Date('2024-01-01T10:01:00Z')
    }
  ];

  const mockValidationErrors: ValidationError[] = [
    {
      row: 1,
      column: 'Name',
      currentValue: 'John',
      recommendedValue: 'John Smith',
      errorType: ValidationErrorType.REQUIRED_VALUE,
      validOptions: null,
      confidenceScore: 0.85,
      confidenceLevel: 'High'
    }
  ];

  const mockOnValidationComplete = jest.fn();
  const mockOnValidationErrors = jest.fn();
  const mockOnApplyChange = jest.fn();
  const mockOnApplyAllChanges = jest.fn();
  const mockOnDisableSpreadsheet = jest.fn();

  beforeEach(() => {
    mockOnValidationComplete.mockClear();
    mockOnValidationErrors.mockClear();
    mockOnApplyChange.mockClear();
    mockOnApplyAllChanges.mockClear();
    mockOnDisableSpreadsheet.mockClear();

    // Mock useAuth to return a valid auth state
    mockUseAuth.mockReturnValue({
      user: { id_token: 'mock-id-token', access_token: 'mock-access-token' },
      isAuthenticated: true,
      isLoading: false,
      error: null,
    } as any);
  });

  it('renders sidebar with submit button', () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    expect(screen.getByText('Submit for Validation')).toBeInTheDocument();
    expect(screen.getByText('Recent Changes (0)')).toBeInTheDocument();
    expect(screen.getByText('Validation Errors')).toBeInTheDocument();
  });

  it('displays job ID when provided', () => {
    const testJobId = 'test-job-123-456';

    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        jobId={testJobId}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    expect(screen.getByText('Job ID')).toBeInTheDocument();
    expect(screen.getByText(testJobId)).toBeInTheDocument();
    expect(screen.getByText('Resubmit for Validation')).toBeInTheDocument();
  });

  it('does not display job ID section when no job ID provided', () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    expect(screen.queryByText('Job ID')).not.toBeInTheDocument();
    expect(screen.getByText('Submit for Validation')).toBeInTheDocument();
  });

  it('displays recent changes correctly', async () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={mockChanges}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    expect(screen.getByText('Recent Changes (2)')).toBeInTheDocument();

    // Recent Changes is collapsed by default, need to expand it
    const expandButton = screen.getByLabelText('Expand Recent Changes section');
    fireEvent.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText('Row 2, Name: "John" → "John Doe"')).toBeInTheDocument();
      expect(screen.getByText('Row 3, Age: "30" → "31"')).toBeInTheDocument();
    });
  });

  it('shows "No changes made yet" when no changes', async () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    // Recent Changes is collapsed by default, need to expand it
    const expandButton = screen.getByLabelText('Expand Recent Changes section');
    fireEvent.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText('No changes made yet')).toBeInTheDocument();
    });
  });

  it('displays validation errors count correctly', () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        validationErrors={mockValidationErrors}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    expect(screen.getByText('Validation Errors')).toBeInTheDocument();
  });

  it('shows "No validation issues found" when no errors', async () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        validationErrors={[]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    // Switch to validation errors tab (default is schema changes tab)
    const validationTab = screen.getByRole('tab', { name: /validation errors/i });
    fireEvent.click(validationTab);

    await waitFor(() => {
      expect(screen.getByText('No Validation Issues')).toBeInTheDocument();
    });
  });

  it('shows error when schema IDs are missing', async () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    const submitButton = screen.getByText('Submit for Validation');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Core and Program schema IDs are required for validation')).toBeInTheDocument();
    });
  });

  it('shows loading state when submitting', () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        isSubmitting={true}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    expect(screen.getByRole('button', { name: /submit for validation/i })).toBeDisabled();
  });

  it('disables submit button when submitting', () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        isSubmitting={true}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    const submitButton = screen.getByRole('button', { name: /submit for validation/i });
    expect(submitButton).toBeDisabled();
  });

  it('shows error when no data provided', async () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={[]}
        changes={[]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    const submitButton = screen.getByText('Submit for Validation');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('No data to validate')).toBeInTheDocument();
    });
  });

  it('limits recent changes to last 5 items', async () => {
    const manyChanges: Change[] = Array.from({ length: 10 }, (_, i) => ({
      row: i,
      column: 0,
      oldValue: `old${i}`,
      newValue: `new${i}`,
      timestamp: new Date(`2024-01-01T10:${i.toString().padStart(2, '0')}:00Z`)
    }));

    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={manyChanges}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    expect(screen.getByText('Recent Changes (10)')).toBeInTheDocument();

    // Recent Changes is collapsed by default, need to expand it
    const expandButton = screen.getByLabelText('Expand Recent Changes section');
    fireEvent.click(expandButton);

    await waitFor(() => {
      // Should show the last 5 changes (most recent first)
      expect(screen.getByText('Row 10, Name: "old9" → "new9"')).toBeInTheDocument();
      expect(screen.getByText('Row 9, Name: "old8" → "new8"')).toBeInTheDocument();
      expect(screen.getByText('Row 8, Name: "old7" → "new7"')).toBeInTheDocument();
      expect(screen.getByText('Row 7, Name: "old6" → "new6"')).toBeInTheDocument();
      expect(screen.getByText('Row 6, Name: "old5" → "new5"')).toBeInTheDocument();

      // Should not show older changes
      expect(screen.queryByText('Row 1, Name: "old0" → "new0"')).not.toBeInTheDocument();
    });
  });

  it('formats change text correctly with column names', async () => {
    const change: Change = {
      row: 1,
      column: 2,
      oldValue: 'New York',
      newValue: 'Boston',
      timestamp: new Date()
    };

    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[change]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    // Recent Changes is collapsed by default, need to expand it
    const expandButton = screen.getByLabelText('Expand Recent Changes section');
    fireEvent.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText('Row 2, City: "New York" → "Boston"')).toBeInTheDocument();
    });
  });

  it('handles invalid column index gracefully', async () => {
    const change: Change = {
      row: 1,
      column: 99, // Invalid column index
      oldValue: 'old',
      newValue: 'new',
      timestamp: new Date()
    };

    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[change]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    // Recent Changes is collapsed by default, need to expand it
    const expandButton = screen.getByLabelText('Expand Recent Changes section');
    fireEvent.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText('Row 2, Col 99: "old" → "new"')).toBeInTheDocument();
    });
  });

  it('renders children in validation issues section', async () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        validationErrors={mockValidationErrors}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      >
        <div data-testid="error-card">Mock Error Card</div>
      </ValidationSidebarComponent>
    );

    // Switch to validation errors tab (default is schema changes tab)
    const validationTab = screen.getByRole('tab', { name: /validation errors/i });
    fireEvent.click(validationTab);

    await waitFor(() => {
      expect(screen.getByTestId('error-card')).toBeInTheDocument();
      expect(screen.getByText('Mock Error Card')).toBeInTheDocument();
    });
  });

  it('does not submit when already submitting', async () => {
    renderWithTheme(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        isSubmitting={true}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    const submitButton = screen.getByRole('button', { name: /submit for validation/i });
    fireEvent.click(submitButton);

    // Should not trigger any validation because button is disabled
    expect(submitButton).toBeDisabled();
  });
});
