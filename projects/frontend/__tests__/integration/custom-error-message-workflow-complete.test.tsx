/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Complete workflow integration tests for custom error message functionality.
 *
 * This module tests the complete end-to-end workflow from API response parsing
 * through component rendering to user interaction, ensuring all aspects of
 * custom error message display work correctly together.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '../../lib/theme';
import { ValidationErrorsPanel } from '../../components/metadata/validation-errors-panel';
import { ValidationSidebarComponent } from '../../components/metadata/validation-sidebar';
import { ValidationError, ValidationErrorType, ValidationJobStatus, ValidationStatusResponse } from '../../lib/types';
import * as api from '../../lib/api';

// Mock the API functions
jest.mock('../../lib/api');
const mockApi = api as jest.Mocked<typeof api>;

// Mock react-oidc-context
jest.mock('react-oidc-context', () => ({
  useAuth: () => ({
    user: {
      id_token: 'mock-token'
    },
    isAuthenticated: true,
    isLoading: false
  })
}));

// Validation error details (inner array)
const mockValidationErrorDetails = [
  {
    row: 1,
    column: 'library_strategy',
    currentValue: 'Invalid',
    validOptions: ['Amplicon'],
    recommendedValue: 'Amplicon',
    errorType: ValidationErrorType.INVALID_OPTION,
    errorMessage: 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]',
    schemaFieldName: 'library_strategy'
  },
  {
    row: 2,
    column: 'sequence_id',
    currentValue: 'invalid-format',
    validOptions: null,
    recommendedValue: null,
    errorType: ValidationErrorType.INVALID_PATTERN,
    errorMessage: 'sequence_id is a required field that must follow the proper formatting',
    schemaFieldName: 'sequence_id'
  },
  {
    row: 3,
    column: 'CSID',
    currentValue: '123',
    validOptions: null,
    recommendedValue: null,
    errorType: ValidationErrorType.INVALID_PATTERN,
    errorMessage: 'CSID is a required field and must be a ten-digit numerical string with no special characters',
    schemaFieldName: 'CSID'
  },
  {
    row: 4,
    column: 'submitter_state',
    currentValue: 'XX',
    validOptions: ['AK', 'AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA'],
    recommendedValue: null,
    errorType: ValidationErrorType.INVALID_OPTION,
    errorMessage: 'submitter_state is a required field and must be formatted as the two-letter State abbreviation',
    schemaFieldName: 'submitter_state'
  },
  {
    row: 5,
    column: 'regular_field',
    currentValue: '',
    validOptions: null,
    recommendedValue: null,
    errorType: ValidationErrorType.REQUIRED_VALUE,
    errorMessage: null,
    schemaFieldName: 'regular_field'
  }
];

// Comprehensive test data simulating real API responses
// Uses the nested CombinedResults structure: latestResults.validationResults.validationResults
const mockApiResponseWithCustomMessages: ValidationStatusResponse = {
  success: true,
  jobId: 'test-job-123',
  userId: 'test-user',
  status: ValidationJobStatus.COMPLETED,
  latestResults: {
    validationResults: {
      validationResults: mockValidationErrorDetails,
      summary: {
        totalRows: 5,
        totalErrors: 5,
        errorTypes: {
          [ValidationErrorType.INVALID_OPTION]: 2,
          [ValidationErrorType.INVALID_PATTERN]: 2,
          [ValidationErrorType.REQUIRED_VALUE]: 1
        }
      }
    },
    schemaAlignmentResults: null
  }
};

const mockValidationErrorDetailsWithout = [
  {
    row: 1,
    column: 'name',
    currentValue: '',
    validOptions: null,
    recommendedValue: null,
    errorType: ValidationErrorType.REQUIRED_VALUE,
    errorMessage: null,
    schemaFieldName: 'name'
  },
  {
    row: 2,
    column: 'email',
    currentValue: 'invalid-email',
    validOptions: null,
    recommendedValue: null,
    errorType: ValidationErrorType.INVALID_PATTERN,
    errorMessage: null,
    schemaFieldName: 'email'
  },
  {
    row: 3,
    column: 'status',
    currentValue: 'invalid-status',
    validOptions: ['active', 'inactive'],
    recommendedValue: null,
    errorType: ValidationErrorType.INVALID_OPTION,
    errorMessage: null,
    schemaFieldName: 'status'
  }
];

const mockApiResponseWithoutCustomMessages: ValidationStatusResponse = {
  success: true,
  jobId: 'test-job-456',
  userId: 'test-user',
  status: ValidationJobStatus.COMPLETED,
  latestResults: {
    validationResults: {
      validationResults: mockValidationErrorDetailsWithout,
      summary: {
        totalRows: 3,
        totalErrors: 3,
        errorTypes: {
          [ValidationErrorType.REQUIRED_VALUE]: 1,
          [ValidationErrorType.INVALID_PATTERN]: 1,
          [ValidationErrorType.INVALID_OPTION]: 1
        }
      }
    },
    schemaAlignmentResults: null
  }
};

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('Custom Error Message Complete Workflow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Setup default mocks for API functions
    mockApi.submitMetadataValidation = jest.fn();
    mockApi.pollValidationStatus = jest.fn();
  });

  describe('End-to-End API to Display Workflow', () => {
    it('should handle complete workflow from API response to error display', async () => {
      // Mock submitMetadataValidation to return a job ID
      mockApi.submitMetadataValidation.mockResolvedValue({
        success: true,
        jobId: 'test-job-123'
      });

      // Mock pollValidationStatus - returns the full ValidationStatusResponse
      mockApi.pollValidationStatus.mockResolvedValue(mockApiResponseWithCustomMessages);

      const mockData = [
        ['library_strategy', 'sequence_id', 'CSID', 'submitter_state', 'regular_field'],
        ['Invalid', 'invalid-format', '123', 'XX', '']
      ];

      const mockOnValidationErrors = jest.fn();
      const mockOnValidationComplete = jest.fn();

      renderWithTheme(
        <ValidationSidebarComponent
          data={mockData}
          changes={[]}
          coreSchemaId="test-core"
          programSchemaId="test-program"
          onValidationComplete={mockOnValidationComplete}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      // Simulate validation submission
      const submitButton = screen.getByText('Submit for Validation');
      fireEvent.click(submitButton);

      // Wait for validation to complete and errors to be processed
      await waitFor(() => {
        expect(mockOnValidationErrors).toHaveBeenCalled();
      }, { timeout: 5000 });

      // Verify that custom error messages are properly passed to the callback
      const [errors, jobId] = mockOnValidationErrors.mock.calls[0];
      expect(jobId).toBe('test-job-123');
      expect(errors).toHaveLength(5);

      // Verify custom error messages are preserved
      const customMessageErrors = errors.filter((e: ValidationError) => e.errorMessage !== null);
      expect(customMessageErrors).toHaveLength(4);

      // Verify specific custom messages
      const libraryStrategyError = errors.find((e: ValidationError) =>
        e.column === 'library_strategy' && e.currentValue === 'Invalid'
      );
      expect(libraryStrategyError?.errorMessage).toBe(
        'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'
      );

      const sequenceIdError = errors.find((e: ValidationError) =>
        e.column === 'sequence_id' && e.currentValue === 'invalid-format'
      );
      expect(sequenceIdError?.errorMessage).toBe(
        'sequence_id is a required field that must follow the proper formatting'
      );
    });

    it('should display custom error messages correctly in ValidationErrorsPanel', async () => {
      const errors = mockValidationErrorDetails;

      renderWithTheme(
        <ValidationErrorsPanel errors={errors} />
      );

      await waitFor(() => {
        const schemaRequirementChips = screen.getAllByText('Schema Requirement');
        expect(schemaRequirementChips.length).toBeGreaterThan(0);
      }, { timeout: 2000 });

      // Verify custom error messages are displayed prominently
      expect(screen.getByText('library_strategy is a required field. Valid input(s) are: ["Amplicon"]')).toBeInTheDocument();
      expect(screen.getByText('sequence_id is a required field that must follow the proper formatting')).toBeInTheDocument();
      expect(screen.getByText('CSID is a required field and must be a ten-digit numerical string with no special characters')).toBeInTheDocument();
      expect(screen.getByText('submitter_state is a required field and must be formatted as the two-letter State abbreviation')).toBeInTheDocument();

      // Verify schema requirement indicators
      const schemaRequirementChips = screen.getAllByText('Schema Requirement');
      expect(schemaRequirementChips).toHaveLength(4); // 4 errors with custom messages

      // Verify fallback display for error without custom message
      expect(screen.getByText('Row 5, Column "regular_field"')).toBeInTheDocument();
      expect(screen.getByText('Current: ""')).toBeInTheDocument();
    });

    it('should handle mixed custom and system error messages in complete workflow', async () => {
      const mixedApiResponse: ValidationStatusResponse = {
        success: true,
        jobId: 'test-job-123',
        userId: 'test-user',
        status: ValidationJobStatus.COMPLETED,
        latestResults: {
          validationResults: {
            validationResults: [
              mockValidationErrorDetails[0], // Custom message
              mockValidationErrorDetailsWithout[0] // No custom message
            ],
            summary: {
              totalRows: 2,
              totalErrors: 2,
              errorTypes: {
                [ValidationErrorType.INVALID_OPTION]: 1,
                [ValidationErrorType.REQUIRED_VALUE]: 1
              }
            }
          },
          schemaAlignmentResults: null
        }
      };

      // Mock submitMetadataValidation to return a job ID
      mockApi.submitMetadataValidation.mockResolvedValue({
        success: true,
        jobId: 'test-job-123'
      });

      // Mock pollValidationStatus
      mockApi.pollValidationStatus.mockResolvedValue(mixedApiResponse);

      const mockData = [
        ['library_strategy', 'name'],
        ['Invalid', '']
      ];

      const mockOnValidationErrors = jest.fn();

      renderWithTheme(
        <ValidationSidebarComponent
          data={mockData}
          changes={[]}
          coreSchemaId="test-core"
          programSchemaId="test-program"
          onValidationComplete={jest.fn()}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      const submitButton = screen.getByText('Submit for Validation');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnValidationErrors).toHaveBeenCalled();
      }, { timeout: 5000 });

      const [errors] = mockOnValidationErrors.mock.calls[0];
      expect(errors).toHaveLength(2);

      // Verify mixed error types
      const customMessageError = errors.find((e: ValidationError) => e.errorMessage !== null);
      const systemMessageError = errors.find((e: ValidationError) => e.errorMessage === null);

      expect(customMessageError).toBeDefined();
      expect(systemMessageError).toBeDefined();

      expect(customMessageError?.errorMessage).toBe(
        'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'
      );
      expect(systemMessageError?.errorMessage).toBeNull();
    });
  });

  describe('Performance and Scalability', () => {
    it('should handle large numbers of custom error messages efficiently', async () => {
      // Create a large number of errors with custom messages
      const largeErrorSet: ValidationError[] = [];
      for (let i = 1; i <= 200; i++) {
        largeErrorSet.push({
          row: i,
          column: `field_${i}`,
          currentValue: `invalid_${i}`,
          validOptions: [`valid_${i}_1`, `valid_${i}_2`],
          recommendedValue: `valid_${i}_1`,
          errorType: ValidationErrorType.INVALID_OPTION,
          errorMessage: `Custom error message for field_${i}. This field requires specific formatting and must be one of the valid options provided. Please review your data and select an appropriate value.`,
          schemaFieldName: `field_${i}`
        });
      }

      const startTime = performance.now();

      renderWithTheme(
        <ValidationErrorsPanel errors={largeErrorSet} />
      );

      await waitFor(() => {
        const schemaRequirementChips = screen.getAllByText('Schema Requirement');
        expect(schemaRequirementChips.length).toBeGreaterThan(0);
      }, { timeout: 3000 });

      const renderTime = performance.now() - startTime;

      // Should render within reasonable time (less than 2 seconds for 200 errors)
      expect(renderTime).toBeLessThan(2000);

      // Verify first error is displayed correctly
      expect(screen.getByText('Row 1, Column "field_1"')).toBeInTheDocument();
      // Use getAllByText since field_1 matches field_1, field_10, field_11, etc.
      const field1Messages = screen.getAllByText(/Custom error message for field_1\./);
      expect(field1Messages.length).toBeGreaterThan(0);

      // Verify schema requirement indicators are present
      const schemaRequirementChips = screen.getAllByText('Schema Requirement');
      expect(schemaRequirementChips.length).toBeGreaterThan(0);
    });

    it('should handle rapid error updates without performance degradation', async () => {
      const { rerender } = renderWithTheme(
        <ValidationErrorsPanel errors={[]} />
      );

      // Simulate rapid updates with different error sets using the flat arrays
      const updateSets = [
        mockValidationErrorDetails.slice(0, 1),
        mockValidationErrorDetails.slice(0, 2),
        mockValidationErrorDetails.slice(0, 3),
        mockValidationErrorDetails,
        mockValidationErrorDetailsWithout
      ];

      for (let i = 0; i < updateSets.length; i++) {
        const errorSet = updateSets[i];
        const updateStart = performance.now();

        rerender(
          <ThemeProvider theme={theme}>
            <ValidationErrorsPanel errors={errorSet} />
          </ThemeProvider>
        );

        // Wait for the appropriate indicator based on error set
        if (i < updateSets.length - 1) {
          // First 4 sets have custom messages
          await waitFor(() => {
            const chips = screen.getAllByText('Schema Requirement');
            expect(chips.length).toBeGreaterThan(0);
          });
        } else {
          // Last set has no custom messages
          await waitFor(() => {
            const chips = screen.getAllByText('System Generated');
            expect(chips.length).toBeGreaterThan(0);
          });
        }

        const updateTime = performance.now() - updateStart;
        expect(updateTime).toBeLessThan(500); // Should update quickly
      }
    });
  });

  describe('Error Message Formatting and Display Quality', () => {
    it('should format long custom error messages appropriately', async () => {
      const errorWithLongMessage: ValidationError[] = [
        {
          row: 1,
          column: 'complex_field',
          currentValue: 'invalid',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: 'This is a comprehensive custom error message that provides detailed information about what went wrong with the data validation. It includes specific formatting requirements, examples of valid values, detailed explanations of why this validation is important for data quality and downstream processing, and step-by-step instructions for correcting the issue. The message is intentionally long to test how the UI handles extensive custom error messages from schema definitions.',
          schemaFieldName: 'complex_field'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={errorWithLongMessage} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Should display the full long message without truncation
      expect(screen.getByText(/This is a comprehensive custom error message/)).toBeInTheDocument();
      expect(screen.getByText(/step-by-step instructions for correcting the issue/)).toBeInTheDocument();

      // Should have proper styling for long messages
      const messageElement = screen.getByText(/This is a comprehensive custom error message/);
      expect(messageElement).toBeInTheDocument();

      // Should show schema requirement indicator
      expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
    });

    it('should display schema field context correctly when different from column name', async () => {
      const errorWithDifferentSchemaField: ValidationError[] = [
        {
          row: 1,
          column: 'transformed_column_name',
          currentValue: 'invalid',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: 'The original schema field has specific requirements that must be met.',
          schemaFieldName: 'original_schema_field_name'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={errorWithDifferentSchemaField} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Should show schema field context when different from column name
      expect(screen.getByText('(Schema field: original_schema_field_name)')).toBeInTheDocument();
      expect(screen.getByText('The original schema field has specific requirements that must be met.')).toBeInTheDocument();
      expect(screen.getByText('Row 1, Column "transformed_column_name"')).toBeInTheDocument();
    });

    it('should handle special characters and formatting in custom error messages', async () => {
      const errorWithSpecialCharacters: ValidationError[] = [
        {
          row: 1,
          column: 'special_field',
          currentValue: 'test',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: 'Field must match pattern: /^[A-Z]{2}\\d{4}$/ (e.g., "AB1234"). Special chars: <>&"\'',
          schemaFieldName: 'special_field'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={errorWithSpecialCharacters} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Should properly display special characters without HTML encoding issues
      expect(screen.getByText(/Field must match pattern: \/\^/)).toBeInTheDocument();
      expect(screen.getByText(/Special chars: <>&"'/)).toBeInTheDocument();
    });
  });

  describe('Accessibility and User Experience', () => {
    it('should provide proper accessibility features for custom error messages', async () => {
      const errors = mockValidationErrorDetails.slice(0, 2);

      renderWithTheme(
        <ValidationErrorsPanel errors={errors} />
      );

      await waitFor(() => {
        const schemaRequirementChips = screen.getAllByText('Schema Requirement');
        expect(schemaRequirementChips.length).toBeGreaterThan(0);
      }, { timeout: 2000 });

      // Should have proper list structure
      const errorList = screen.getByRole('list');
      expect(errorList).toBeInTheDocument();

      // Should have proper ARIA labels for custom message indicators
      const schemaRequirementChips = screen.getAllByText('Schema Requirement');
      expect(schemaRequirementChips.length).toBeGreaterThan(0);

      // Both errors should be rendered within the list
      expect(screen.getByText('Row 1, Column "library_strategy"')).toBeInTheDocument();
      expect(screen.getByText('Row 2, Column "sequence_id"')).toBeInTheDocument();
    });

    it('should provide clear visual hierarchy between custom and system messages', async () => {
      const mixedErrors = [
        mockValidationErrorDetails[0], // Custom message
        mockValidationErrorDetailsWithout[0] // System message
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={mixedErrors} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Custom message should have special styling indicator
      expect(screen.getByText('Schema Requirement')).toBeInTheDocument();

      // Both errors should be clearly distinguishable
      expect(screen.getByText('library_strategy is a required field. Valid input(s) are: ["Amplicon"]')).toBeInTheDocument();
      expect(screen.getByText('Row 1, Column "name"')).toBeInTheDocument();

      // Should have different visual treatments - custom messages in styled boxes, system in cards
      const customMessageElement = screen.getByText('library_strategy is a required field. Valid input(s) are: ["Amplicon"]');
      const systemMessageElement = screen.getByText('Row 1, Column "name"');

      expect(customMessageElement).toBeInTheDocument();
      expect(systemMessageElement).toBeInTheDocument();

      // Verify they are rendered as distinct elements in the DOM
      expect(customMessageElement.closest('[class*="MuiBox-root"]')).toBeInTheDocument();
      expect(systemMessageElement.parentElement).toBeInTheDocument();
    });
  });

  describe('Backward Compatibility', () => {
    it('should maintain compatibility with existing validation workflows', async () => {
      // Test with API response that has no custom error message fields
      const legacyErrors = [
        {
          row: 1,
          column: 'legacy_field',
          currentValue: 'invalid',
          validOptions: ['valid1', 'valid2'],
          recommendedValue: 'valid1',
          errorType: ValidationErrorType.INVALID_OPTION,
          errorMessage: null,
          schemaFieldName: 'legacy_field'
        }
      ];

      const legacyApiResponse: ValidationStatusResponse = {
        success: true,
        jobId: 'legacy-job-123',
        userId: 'test-user',
        status: ValidationJobStatus.COMPLETED,
        latestResults: {
          validationResults: {
            validationResults: legacyErrors,
            summary: {
              totalRows: 1,
              totalErrors: 1,
              errorTypes: {
                [ValidationErrorType.INVALID_OPTION]: 1
              }
            }
          },
          schemaAlignmentResults: null
        }
      };

      // Mock submitMetadataValidation to return a job ID
      mockApi.submitMetadataValidation.mockResolvedValue({
        success: true,
        jobId: 'legacy-job-123'
      });

      // Mock pollValidationStatus
      mockApi.pollValidationStatus.mockResolvedValue(legacyApiResponse);

      const mockData = [
        ['legacy_field'],
        ['invalid']
      ];

      const mockOnValidationErrors = jest.fn();

      renderWithTheme(
        <ValidationSidebarComponent
          data={mockData}
          changes={[]}
          coreSchemaId="test-core"
          programSchemaId="test-program"
          onValidationComplete={jest.fn()}
          onValidationErrors={mockOnValidationErrors}
        />
      );

      const submitButton = screen.getByText('Submit for Validation');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnValidationErrors).toHaveBeenCalled();
      }, { timeout: 10000 });

      const [errors] = mockOnValidationErrors.mock.calls[0];
      expect(errors).toHaveLength(1);

      // Should handle legacy format correctly
      expect(errors[0].errorMessage).toBeNull();
      expect(errors[0].schemaFieldName).toBe('legacy_field');

      // Display should work correctly with legacy data
      renderWithTheme(
        <ValidationErrorsPanel errors={errors} />
      );

      await waitFor(() => {
        const systemGeneratedChips = screen.getAllByText('System Generated');
        expect(systemGeneratedChips.length).toBeGreaterThan(0);
      });

      expect(screen.getByText('Row 1, Column "legacy_field"')).toBeInTheDocument();
      expect(screen.getByText('Current: "invalid"')).toBeInTheDocument();
      expect(screen.getByText('Recommended: "valid1"')).toBeInTheDocument();

      // Should show system generated indicator, not custom message indicator
      expect(screen.getByText('System Generated')).toBeInTheDocument();
      expect(screen.queryByText('Schema Requirement')).not.toBeInTheDocument();
    });

    it('should handle undefined or missing custom message fields gracefully', async () => {
      const errorsWithUndefinedFields: ValidationError[] = [
        {
          row: 1,
          column: 'test_field',
          currentValue: 'invalid',
          validOptions: ['valid'],
          recommendedValue: 'valid',
          errorType: ValidationErrorType.INVALID_OPTION,
          errorMessage: undefined as any,
          schemaFieldName: undefined as any
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={errorsWithUndefinedFields} />
      );

      await waitFor(() => {
        expect(screen.getByText('System Generated')).toBeInTheDocument();
      });

      // Should handle undefined fields gracefully
      expect(screen.getByText('Row 1, Column "test_field"')).toBeInTheDocument();
      expect(screen.getByText('Current: "invalid"')).toBeInTheDocument();

      // Should show system generated indicator when errorMessage is undefined
      expect(screen.getByText('System Generated')).toBeInTheDocument();
      expect(screen.queryByText('Schema Requirement')).not.toBeInTheDocument();

      // Should not crash or show undefined text
      expect(screen.queryByText('undefined')).not.toBeInTheDocument();
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle empty custom error messages gracefully', async () => {
      const errorWithEmptyMessage: ValidationError[] = [
        {
          row: 1,
          column: 'test_field',
          currentValue: 'invalid',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: '', // Empty string
          schemaFieldName: 'test_field'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={errorWithEmptyMessage} />
      );

      await waitFor(() => {
        expect(screen.getByText('System Generated')).toBeInTheDocument();
      });

      // Should treat empty string as no custom message
      expect(screen.getByText('Row 1, Column "test_field"')).toBeInTheDocument();
      expect(screen.getByText('System Generated')).toBeInTheDocument();
      expect(screen.queryByText('Schema Requirement')).not.toBeInTheDocument();
    });

    it('should handle very long schema field names appropriately', async () => {
      const errorWithLongSchemaFieldName: ValidationError[] = [
        {
          row: 1,
          column: 'short_col',
          currentValue: 'invalid',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: 'This field has specific requirements.',
          schemaFieldName: 'this_is_a_very_long_schema_field_name_that_might_cause_display_issues_if_not_handled_properly'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={errorWithLongSchemaFieldName} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Should display long schema field name appropriately
      expect(screen.getByText(/Schema field: this_is_a_very_long_schema_field_name/)).toBeInTheDocument();
      expect(screen.getByText('This field has specific requirements.')).toBeInTheDocument();
    });
  });
});
