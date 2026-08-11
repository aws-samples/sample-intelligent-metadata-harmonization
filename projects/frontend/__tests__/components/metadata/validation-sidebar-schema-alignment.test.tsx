/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ValidationSidebarComponent } from '../../../components/metadata/validation-sidebar';
import {
  ValidationJobStatus,
  ValidationError,
  ValidationErrorType,
  SchemaAlignmentResults,
  SchemaAlignmentChangeDetail
} from '../../../lib/types';

// Mock the API functions
jest.mock('../../../lib/api', () => ({
  updateValidationJob: jest.fn(),
  pollValidationStatus: jest.fn(),
  submitMetadataValidation: jest.fn(),
}));

// Mock react-oidc-context
jest.mock('react-oidc-context', () => ({
  useAuth: () => ({
    user: { access_token: 'mock-token' }
  })
}));

describe('ValidationSidebarComponent - Schema Alignment Integration', () => {
  const mockData = [
    ['Name', 'Age', 'Email'],
    ['John', '25', 'john@example.com'],
    ['Jane', '30', 'jane@example.com']
  ];

  const mockChanges = [
    {
      row: 1,
      column: 0,
      oldValue: 'John',
      newValue: 'John Doe',
      timestamp: new Date()
    }
  ];

  const mockValidationErrors: ValidationError[] = [
    {
      row: 1,
      column: 'Email',
      currentValue: 'invalid-email',
      validOptions: null,
      recommendedValue: 'valid@example.com',
      errorType: ValidationErrorType.INVALID_PATTERN
    }
  ];

  const mockSchemaAlignmentResults: SchemaAlignmentResults = {
    schemaAlignmentResults: [
      {
        changeType: 'rename',
        originalColumn: 'Name',
        newColumn: 'FullName',
        reason: 'Column renamed to match target schema',
        rowCountAffected: 2
      },
      {
        changeType: 'add',
        newColumn: 'Status',
        reason: 'Required column added for schema compliance',
        rowCountAffected: 2
      },
      {
        changeType: 'remove',
        originalColumn: 'Age',
        reason: 'Column not required in target schema',
        rowCountAffected: 2
      }
    ],
    summary: {
      jobId: 'test-job-123',
      version: 1,
      timestamp: '2024-01-01T00:00:00Z',
      originalDataCsv: 'Name,Age,Email\nJohn,25,john@example.com',
      alignedDataCsv: 'FullName,Email,Status\nJohn,john@example.com,',
      totalChanges: 3,
      columnsRenamed: 1,
      columnsAdded: 1,
      columnsRemoved: 1,
      rowsOriginal: 2,
      rowsAligned: 2
    }
  };

  const defaultProps = {
    data: mockData,
    changes: mockChanges,
    validationErrors: mockValidationErrors,
    schemaAlignmentResults: mockSchemaAlignmentResults,
    jobId: 'test-job-123',
    coreSchemaId: 'core-schema-1',
    programSchemaId: 'program-schema-1',
    onValidationComplete: jest.fn(),
    onValidationErrors: jest.fn(),
    onApplyChange: jest.fn(),
    onApplyAllChanges: jest.fn(),
    onDisableSpreadsheet: jest.fn(),
    onAcceptSchemaChange: jest.fn(),
    onRevertSchemaChange: jest.fn(),
    onApplyColumnRename: jest.fn(),
    onApplyColumnAddition: jest.fn(),
    onApplyColumnRemoval: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Tab Order and Structure', () => {
    it('should display Schema Changes tab first and Validation Errors tab second', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(2);

      // Schema Changes should be first tab
      expect(tabs[0]).toHaveTextContent('Schema Changes');
      // Validation Errors should be second tab
      expect(tabs[1]).toHaveTextContent('Validation Errors');
    });

    it('should start with Schema Changes tab active by default', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
      expect(schemaTab).toHaveAttribute('aria-selected', 'true');

      const validationTab = screen.getByRole('tab', { name: /validation errors/i });
      expect(validationTab).toHaveAttribute('aria-selected', 'false');
    });

    it('should allow switching between tabs', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      const validationTab = screen.getByRole('tab', { name: /validation errors/i });
      fireEvent.click(validationTab);

      expect(validationTab).toHaveAttribute('aria-selected', 'true');

      const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
      expect(schemaTab).toHaveAttribute('aria-selected', 'false');
    });
  });

  describe('Badge Counts', () => {
    it('should display correct badge count for schema changes', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
      // Should show badge with count of 3 (from mockSchemaAlignmentResults)
      expect(schemaTab).toHaveTextContent('3');
    });

    it('should display correct badge count for validation errors', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      const validationTab = screen.getByRole('tab', { name: /validation errors/i });
      // Should show badge with count of 1 (from mockValidationErrors)
      expect(validationTab).toHaveTextContent('1');
    });

    it('should show zero badge when no schema alignment results', () => {
      const propsWithoutSchemaResults = {
        ...defaultProps,
        schemaAlignmentResults: null
      };

      render(<ValidationSidebarComponent {...propsWithoutSchemaResults} />);

      // Badge with 0 content should be invisible in Material-UI
      const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
      expect(schemaTab).toBeInTheDocument();
      // The badge should have the invisible class when count is 0
      const badge = schemaTab.querySelector('.MuiBadge-badge');
      expect(badge).toHaveClass('MuiBadge-invisible');
    });

    it('should show zero badge when no validation errors', () => {
      const propsWithoutErrors = {
        ...defaultProps,
        validationErrors: null
      };

      render(<ValidationSidebarComponent {...propsWithoutErrors} />);

      // Badge with 0 content should be invisible in Material-UI
      const validationTab = screen.getByRole('tab', { name: /validation errors/i });
      expect(validationTab).toBeInTheDocument();
      // The badge should have the invisible class when count is 0
      const badge = validationTab.querySelector('.MuiBadge-badge');
      expect(badge).toHaveClass('MuiBadge-invisible');
    });
  });

  describe('Schema Changes Panel Integration', () => {
    it('should pass SchemaAlignmentChangeDetail array to SchemaChangesPanel', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      // Schema Changes tab should be active by default
      // The schema changes panel should show the changes, but the exact text rendering
      // depends on the SchemaChangeCard component. Let's verify the panel is showing changes.
      // Check for key elements that indicate schema changes are being displayed
      expect(screen.getByText('Schema Changes')).toBeInTheDocument();

      // Look for the column names that are part of the schema changes (there may be multiple)
      const nameElements = screen.getAllByText(/Name/);
      expect(nameElements.length).toBeGreaterThan(0);

      const fullNameElements = screen.getAllByText(/FullName/);
      expect(fullNameElements.length).toBeGreaterThan(0);
    });

    it('should handle schema change callbacks', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      // Find and click an Apply Rename button (first change is a rename)
      const applyRenameButton = screen.getByText('Apply Rename');
      fireEvent.click(applyRenameButton);

      // Should call the manual schema transformation callback for rename
      expect(defaultProps.onApplyColumnRename).toHaveBeenCalledWith('Name', 'FullName');
    });

    it('should handle schema revert callbacks', async () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      // First apply a change to get a revert button
      const applyRenameButton = screen.getByText('Apply Rename');
      fireEvent.click(applyRenameButton);

      // Wait for the button state to update
      await waitFor(() => {
        const revertButton = screen.queryByText('Revert');
        expect(revertButton).toBeInTheDocument();
      });

      // Now find and click the Revert button
      const revertButton = screen.getByText('Revert');
      fireEvent.click(revertButton);

      // The callback should have been called
      expect(defaultProps.onRevertSchemaChange).toHaveBeenCalled();
    });
  });

  describe('Validation Errors Panel Integration', () => {
    it('should display validation errors when switching to validation tab', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      // Switch to validation errors tab
      const validationTab = screen.getByRole('tab', { name: /validation errors/i });
      fireEvent.click(validationTab);

      expect(screen.getByText('Row 1, Column "Email"')).toBeInTheDocument();
      expect(screen.getByText('Current: "invalid-email"')).toBeInTheDocument();
      expect(screen.getByText('Recommended: "valid@example.com"')).toBeInTheDocument();
    });

    it('should handle validation error callbacks', async () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      // Switch to validation errors tab
      const validationTab = screen.getByRole('tab', { name: /validation errors/i });
      fireEvent.click(validationTab);

      await waitFor(() => {
        // Wait for content to load
        expect(screen.getByText('Row 1, Column "Email"')).toBeInTheDocument();
      });

      // Find and click Accept Recommendation button
      const acceptButton = screen.getByText('Accept Recommendation');
      fireEvent.click(acceptButton);

      expect(defaultProps.onApplyChange).toHaveBeenCalledWith(mockValidationErrors[0]);
    });
  });

  describe('Empty States', () => {
    it('should handle empty schema alignment results gracefully', () => {
      const propsWithEmptySchema = {
        ...defaultProps,
        schemaAlignmentResults: {
          schemaAlignmentResults: [],
          summary: {
            ...mockSchemaAlignmentResults.summary,
            totalChanges: 0
          }
        }
      };

      render(<ValidationSidebarComponent {...propsWithEmptySchema} />);

      expect(screen.getByText('No Schema Changes')).toBeInTheDocument();
      expect(screen.getByText('Your data structure matches the target schema perfectly.')).toBeInTheDocument();
    });

    it('should handle null schema alignment results', () => {
      const propsWithNullSchema = {
        ...defaultProps,
        schemaAlignmentResults: null
      };

      render(<ValidationSidebarComponent {...propsWithNullSchema} />);

      expect(screen.getByText('No Schema Changes')).toBeInTheDocument();
    });
  });

  describe('Data Structure Compatibility', () => {
    it('should handle SchemaAlignmentResults structure correctly', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      // Verify that the component shows schema changes tab
      expect(screen.getByText('Schema Changes')).toBeInTheDocument();

      // The badge count is shown separately from the text
      // Just verify that the schema changes are rendered by checking for the column names
      const nameElements = screen.getAllByText(/Name/);
      expect(nameElements.length).toBeGreaterThan(0);

      const fullNameElements = screen.getAllByText(/FullName/);
      expect(fullNameElements.length).toBeGreaterThan(0);
    });

    it('should display row count affected information', () => {
      render(<ValidationSidebarComponent {...defaultProps} />);

      // All changes affect 2 rows according to mock data
      const rowCountTexts = screen.getAllByText('Affects 2 rows');
      expect(rowCountTexts).toHaveLength(3); // One for each change
    });
  });

  describe('Callback Integration', () => {
    it('should pass correct SchemaAlignmentResults to onValidationErrors callback', async () => {
      const { updateValidationJob, pollValidationStatus } = require('../../../lib/api');

      // Mock successful API responses for resubmission (since jobId is provided)
      updateValidationJob.mockResolvedValue({
        success: true,
        jobId: 'test-job-456'
      });

      pollValidationStatus.mockResolvedValue({
        success: true,
        status: ValidationJobStatus.COMPLETED_WITH_ERRORS,
        latestResults: {
          validationResults: {
            validationResults: mockValidationErrors
          },
          schemaAlignmentResults: mockSchemaAlignmentResults
        }
      });

      render(<ValidationSidebarComponent {...defaultProps} />);

      // Click submit button (should be "Resubmit for Validation" since jobId is provided)
      const submitButton = screen.getByRole('button', { name: /resubmit for validation/i });
      fireEvent.click(submitButton);

      // Wait for polling to complete
      await waitFor(() => {
        expect(defaultProps.onValidationErrors).toHaveBeenCalledWith(
          mockValidationErrors,
          'test-job-456',
          mockSchemaAlignmentResults
        );
      }, { timeout: 3000 });
    });
  });
});
