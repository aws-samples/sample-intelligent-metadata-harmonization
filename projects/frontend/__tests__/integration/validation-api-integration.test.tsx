/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ValidationSidebarComponent } from '../../components/metadata/validation-sidebar';
import { ValidationErrorType, ValidationJobStatus } from '../../lib/types';
import * as api from '../../lib/api';

// Mock fetch globally
global.fetch = jest.fn();

// Mock react-oidc-context
jest.mock('react-oidc-context', () => ({
  AuthProvider: ({ children }: any) => <div>{children}</div>,
  useAuth: () => ({ user: { id_token: 'mock-token' }, isAuthenticated: true })
}));

// Mock the API functions
jest.mock('../../lib/api');
const mockApi = api as jest.Mocked<typeof api>;

const theme = createTheme();

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('ValidationSidebarComponent API Integration', () => {
  const mockData = [
    ['Name', 'Age', 'City'],
    ['John', '25', 'New York'],
    ['Jane', '30', 'Boston']
  ];

  const mockOnValidationComplete = jest.fn();
  const mockOnValidationErrors = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockOnValidationComplete.mockClear();
    mockOnValidationErrors.mockClear();
  });

  it('calls API when submit button is clicked with valid schema IDs', async () => {
    // Mock successful API response
    mockApi.submitMetadataValidation.mockResolvedValue({
      success: true,
      jobId: 'test-job-123',
      coreSchemaId: 'test-core-schema',
      programSchemaId: 'test-program-schema'
    });

    mockApi.pollValidationStatus.mockImplementation(async (jobId, onStatusUpdate, token, options) => {
      // Simulate polling lifecycle
      if (onStatusUpdate) {
        onStatusUpdate(ValidationJobStatus.PENDING, { success: true, jobId, userId: 'test-user', status: ValidationJobStatus.PENDING } as any);
        onStatusUpdate(ValidationJobStatus.PROCESSING, { success: true, jobId, userId: 'test-user', status: ValidationJobStatus.PROCESSING } as any);
        onStatusUpdate(ValidationJobStatus.COMPLETED, { success: true, jobId, userId: 'test-user', status: ValidationJobStatus.COMPLETED, latestResults: null } as any);
      }

      return {
        success: true,
        jobId: 'test-job-123',
        userId: 'test-user',
        status: ValidationJobStatus.COMPLETED,
        latestResults: null // No errors - successful validation
      };
    });

    renderWithProviders(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    const submitButton = screen.getByText('Submit for Validation');
    fireEvent.click(submitButton);

    // Wait for API calls to complete
    await waitFor(() => {
      expect(mockApi.submitMetadataValidation).toHaveBeenCalledWith(
        mockData,
        'test-core-schema',
        'test-program-schema',
        'mock-token' // Auth token from mock
      );
    });

    await waitFor(() => {
      expect(mockApi.pollValidationStatus).toHaveBeenCalledWith(
        'test-job-123',
        expect.any(Function), // Status update callback
        'mock-token', // Auth token from mock
        expect.objectContaining({
          pollInterval: 2000,
          maxAttempts: 150,
          timeoutMs: 300000
        })
      );
    });

    await waitFor(() => {
      expect(mockOnValidationComplete).toHaveBeenCalled();
    });
  });

  it('handles validation errors correctly', async () => {
    const mockValidationErrors = [
      {
        row: 1,
        column: 'Name',
        currentValue: 'John',
        recommendedValue: 'John Smith',
        errorType: ValidationErrorType.REQUIRED_VALUE,
        validOptions: null
      }
    ];

    const latestResults = {
      validationResults: {
        validationResults: mockValidationErrors,
        summary: {
          totalRows: 3,
          totalErrors: 1,
          errorTypes: { 'REQUIRED_VALUE': 1 }
        }
      },
      schemaAlignmentResults: null
    };

    // Mock successful API response with validation errors
    mockApi.submitMetadataValidation.mockResolvedValue({
      success: true,
      jobId: 'test-job-123',
      coreSchemaId: 'test-core-schema',
      programSchemaId: 'test-program-schema'
    });

    mockApi.pollValidationStatus.mockImplementation(async (jobId, onStatusUpdate, token, options) => {
      // Simulate polling lifecycle
      if (onStatusUpdate) {
        onStatusUpdate(ValidationJobStatus.PENDING, { success: true, jobId, userId: 'test-user', status: ValidationJobStatus.PENDING } as any);
        onStatusUpdate(ValidationJobStatus.PROCESSING, { success: true, jobId, userId: 'test-user', status: ValidationJobStatus.PROCESSING } as any);
        onStatusUpdate(ValidationJobStatus.COMPLETED, { success: true, jobId, userId: 'test-user', status: ValidationJobStatus.COMPLETED, latestResults } as any);
      }

      return {
        success: true,
        jobId: 'test-job-123',
        userId: 'test-user',
        status: ValidationJobStatus.COMPLETED,
        latestResults
      };
    });

    renderWithProviders(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    const submitButton = screen.getByText('Submit for Validation');
    fireEvent.click(submitButton);

    // Wait for API calls to complete
    await waitFor(() => {
      expect(mockOnValidationErrors).toHaveBeenCalledWith(mockValidationErrors, 'test-job-123', undefined);
    });

    expect(mockOnValidationComplete).not.toHaveBeenCalled();
  });

  it('handles API errors gracefully', async () => {
    // Mock API error
    mockApi.submitMetadataValidation.mockResolvedValue({
      success: false,
      error: 'Network error occurred'
    });

    renderWithProviders(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    const submitButton = screen.getByText('Submit for Validation');
    fireEvent.click(submitButton);

    // Wait for error to be displayed
    await waitFor(() => {
      expect(screen.getByText('Network error occurred')).toBeInTheDocument();
    });

    expect(mockOnValidationComplete).not.toHaveBeenCalled();
    expect(mockOnValidationErrors).not.toHaveBeenCalled();
  });

  it('shows resubmit button when jobId is provided', () => {
    renderWithProviders(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        jobId="existing-job-123"
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    expect(screen.getByText('Resubmit for Validation')).toBeInTheDocument();
  });

  it('calls updateValidationJob for resubmission', async () => {
    // Mock successful resubmission
    mockApi.updateValidationJob.mockResolvedValue({
      success: true,
      jobId: 'existing-job-123'
    });

    mockApi.pollValidationStatus.mockImplementation(async (jobId, onStatusUpdate, token, options) => {
      // Simulate polling lifecycle
      if (onStatusUpdate) {
        onStatusUpdate(ValidationJobStatus.PENDING, { success: true, jobId, userId: 'test-user', status: ValidationJobStatus.PENDING } as any);
        onStatusUpdate(ValidationJobStatus.PROCESSING, { success: true, jobId, userId: 'test-user', status: ValidationJobStatus.PROCESSING } as any);
        onStatusUpdate(ValidationJobStatus.COMPLETED, { success: true, jobId, userId: 'test-user', status: ValidationJobStatus.COMPLETED, latestResults: null } as any);
      }

      return {
        success: true,
        jobId: 'existing-job-123',
        userId: 'test-user',
        status: ValidationJobStatus.COMPLETED,
        latestResults: null
      };
    });

    renderWithProviders(
      <ValidationSidebarComponent
        data={mockData}
        changes={[]}
        jobId="existing-job-123"
        coreSchemaId="test-core-schema"
        programSchemaId="test-program-schema"
        onValidationComplete={mockOnValidationComplete}
        onValidationErrors={mockOnValidationErrors}
      />
    );

    const submitButton = screen.getByText('Resubmit for Validation');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockApi.updateValidationJob).toHaveBeenCalledWith(
        'existing-job-123',
        expect.any(File), // CSV file created from data
        'mock-token' // Auth token from mock
      );
    });
  });
});
