/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ValidationErrorsPanel } from '../../../components/metadata/validation-errors-panel';
import { ValidationError, ValidationErrorType } from '../../../lib/types';
import { beforeEach } from 'node:test';

describe('ValidationErrorsPanel', () => {
  const mockValidationErrors: ValidationError[] = [
    {
      row: 1,
      column: 'Email',
      currentValue: 'invalid-email',
      validOptions: null,
      recommendedValue: 'valid@example.com',
      errorType: ValidationErrorType.INVALID_PATTERN
    },
    {
      row: 2,
      column: 'Status',
      currentValue: 'invalid-status',
      validOptions: ['Active', 'Inactive', 'Pending'],
      recommendedValue: 'Active',
      errorType: ValidationErrorType.INVALID_OPTION
    },
    {
      row: 3,
      column: 'Name',
      currentValue: '',
      validOptions: null,
      recommendedValue: null,
      errorType: ValidationErrorType.REQUIRED_VALUE
    }
  ];

  const defaultProps = {
    errors: mockValidationErrors,
    onAcceptError: jest.fn(),
    onAcceptAllErrors: jest.fn(),
    onDismissError: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Error Display', () => {
    it('should display all validation errors with correct information', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      // Header with error count removed - count now shown in tab badge

      // Check individual errors
      expect(screen.getByText('Row 1, Column "Email"')).toBeInTheDocument();
      expect(screen.getByText('Current: "invalid-email"')).toBeInTheDocument();
      expect(screen.getByText('Recommended: "valid@example.com"')).toBeInTheDocument();

      expect(screen.getByText('Row 2, Column "Status"')).toBeInTheDocument();
      expect(screen.getByText('Current: "invalid-status"')).toBeInTheDocument();
      expect(screen.getByText('Recommended: "Active"')).toBeInTheDocument();
      // Valid options are not shown when there's a recommendation

      expect(screen.getByText('Row 3, Column "Name"')).toBeInTheDocument();
      expect(screen.getByText('Current: ""')).toBeInTheDocument();
    });

    it('should show bulk actions button when errors have recommendations', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      // Should show bulk accept button for errors with recommendations (2 out of 3)
      expect(screen.getByText('Accept All Recommendations (2)')).toBeInTheDocument();
    });

    it('should not display footer with summary information (footer removed)', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      // Footer was commented out in source code (lines 241-247)
      expect(screen.queryByText('2 of 3 errors have recommended corrections')).not.toBeInTheDocument();
    });
  });

  describe('Empty States', () => {
    it('should display empty state when no errors exist', () => {
      render(<ValidationErrorsPanel {...defaultProps} errors={[]} />);

      expect(screen.getByText('No Validation Issues')).toBeInTheDocument();
      expect(screen.getByText('Your data passes all validation checks for the selected schema.')).toBeInTheDocument();
    });

    it('should display loading state when isLoading is true', () => {
      render(<ValidationErrorsPanel {...defaultProps} errors={[]} isLoading={true} />);

      expect(screen.getByText('Checking for validation issues...')).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should call onAcceptError when Accept Recommendation button is clicked', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      const acceptButtons = screen.getAllByText('Accept Recommendation');
      fireEvent.click(acceptButtons[0]);

      expect(defaultProps.onAcceptError).toHaveBeenCalledWith(mockValidationErrors[0]);
    });

    it('should call onDismissError when Dismiss button is clicked', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      const dismissButtons = screen.getAllByText('Dismiss');
      fireEvent.click(dismissButtons[0]);

      expect(defaultProps.onDismissError).toHaveBeenCalledWith(mockValidationErrors[0]);
    });

    it('should call onAcceptAllErrors when bulk accept button is clicked', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      const bulkAcceptButton = screen.getByText('Accept All Recommendations (2)');
      fireEvent.click(bulkAcceptButton);

      // Should be called with only errors that have recommendations
      const errorsWithRecommendations = mockValidationErrors.filter(error => error.recommendedValue !== null);
      expect(defaultProps.onAcceptAllErrors).toHaveBeenCalledWith(errorsWithRecommendations);
    });

    it('should not show Accept Recommendation/Dismiss buttons when callbacks are not provided', () => {
      const propsWithoutCallbacks = {
        errors: mockValidationErrors
      };

      render(<ValidationErrorsPanel {...propsWithoutCallbacks} />);

      expect(screen.queryByText('Accept Recommendation')).not.toBeInTheDocument();
      expect(screen.queryByText('Dismiss')).not.toBeInTheDocument();
    });

    it('should not show bulk actions when onAcceptAllErrors callback is not provided', () => {
      const propsWithoutBulkCallback = {
        ...defaultProps,
        onAcceptAllErrors: undefined
      };

      render(<ValidationErrorsPanel {...propsWithoutBulkCallback} />);

      expect(screen.queryByText(/Accept All Recommendations/)).not.toBeInTheDocument();
    });
  });

  describe('Custom Error Cards', () => {
    it('should render custom error cards when children are provided', () => {
      const customErrorCard = (
        <div key="custom" data-testid="custom-error-card">
          Custom Error Display
        </div>
      );

      render(
        <ValidationErrorsPanel {...defaultProps}>
          {customErrorCard}
        </ValidationErrorsPanel>
      );

      expect(screen.getByTestId('custom-error-card')).toBeInTheDocument();
      expect(screen.getByText('Custom Error Display')).toBeInTheDocument();

      // Default error display should not be shown when children are provided
      expect(screen.queryByText('Row 1, Column "Email"')).not.toBeInTheDocument();
    });
  });

  describe('Manual Editing Guidance', () => {
    it('should show manual editing guidance when no recommendation is available but valid options exist', () => {
      const errorsWithValidOptionsOnly: ValidationError[] = [
        {
          row: 1,
          column: 'Status',
          currentValue: 'invalid-status',
          validOptions: ['Active', 'Inactive', 'Pending'],
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_OPTION
        }
      ];

      render(<ValidationErrorsPanel {...defaultProps} errors={errorsWithValidOptionsOnly} />);

      // Should show manual editing guidance
      expect(screen.getByText('No automatic recommendation found')).toBeInTheDocument();
      expect(screen.getByText('Valid options: Active, Inactive, Pending')).toBeInTheDocument();
      expect(screen.getByText('You can manually edit this cell in the spreadsheet to use one of the valid options above.')).toBeInTheDocument();

      // Should not show Accept Recommendation button
      expect(screen.queryByText('Accept Recommendation')).not.toBeInTheDocument();
    });

    it('should show recommendation UI when recommendedValue is available', () => {
      const errorsWithRecommendations: ValidationError[] = [
        {
          row: 1,
          column: 'Email',
          currentValue: 'invalid-email',
          validOptions: null,
          recommendedValue: 'valid@example.com',
          errorType: ValidationErrorType.INVALID_PATTERN
        }
      ];

      render(<ValidationErrorsPanel {...defaultProps} errors={errorsWithRecommendations} />);

      // Should show recommendation UI
      expect(screen.getByText('Recommended: "valid@example.com"')).toBeInTheDocument();
      expect(screen.getByText('Accept Recommendation')).toBeInTheDocument();

      // Should not show manual editing guidance
      expect(screen.queryByText('No automatic recommendation found')).not.toBeInTheDocument();
    });
  });

  describe('Error Filtering', () => {
    it('should correctly identify errors with recommendations for bulk operations', () => {
      const errorsWithoutRecommendations = [
        {
          row: 1,
          column: 'Name',
          currentValue: '',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.REQUIRED_VALUE
        }
      ];

      render(<ValidationErrorsPanel {...defaultProps} errors={errorsWithoutRecommendations} />);

      // Should not show bulk actions when no errors have recommendations
      expect(screen.queryByText(/Accept All Recommendations/)).not.toBeInTheDocument();

      // Footer was commented out in source code, so it shouldn't appear
      expect(screen.queryByText('0 of 1 errors have recommended corrections')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible error display without redundant header', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      // Header with error count removed - count now shown in tab badge
      expect(screen.queryByRole('heading', { level: 6 })).not.toBeInTheDocument();
    });

    it('should have accessible button labels', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      const acceptButtons = screen.getAllByRole('button', { name: 'Accept Recommendation' });
      expect(acceptButtons).toHaveLength(2); // Only errors with recommendations

      const dismissButtons = screen.getAllByRole('button', { name: 'Dismiss' });
      expect(dismissButtons).toHaveLength(2); // Only errors with recommendations

      const bulkButton = screen.getByRole('button', { name: 'Accept All Recommendations (2)' });
      expect(bulkButton).toBeInTheDocument();
    });
  });

  describe('Current View Context', () => {
    it('should not display view context information (removed functionality)', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      // Should not contain any view-related context text
      expect(screen.queryByText(/original/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/aligned/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/view/i)).not.toBeInTheDocument();
    });
  });

  describe('Backward Compatibility', () => {
    it('should maintain existing error handling functionality', () => {
      render(<ValidationErrorsPanel {...defaultProps} />);

      // All existing functionality should work (header removed for cleaner UI)

      // Error details should be displayed
      expect(screen.getByText('Row 1, Column "Email"')).toBeInTheDocument();
      expect(screen.getByText('Current: "invalid-email"')).toBeInTheDocument();
      expect(screen.getByText('Recommended: "valid@example.com"')).toBeInTheDocument();

      // Interactions should work
      const acceptButton = screen.getAllByText('Accept Recommendation')[0];
      fireEvent.click(acceptButton);
      expect(defaultProps.onAcceptError).toHaveBeenCalled();
    });
  });

  describe('Custom Error Messages', () => {
    const errorsWithCustomMessages: ValidationError[] = [
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
        column: 'regular_field',
        currentValue: '',
        validOptions: null,
        recommendedValue: null,
        errorType: ValidationErrorType.REQUIRED_VALUE
        // No custom error message - should fall back to system generated
      }
    ];

    it('should display custom error messages prominently when available', () => {
      render(<ValidationErrorsPanel errors={errorsWithCustomMessages} />);

      // Should display custom error messages
      expect(screen.getByText('library_strategy is a required field. Valid input(s) are: ["Amplicon"]')).toBeInTheDocument();
      expect(screen.getByText('sequence_id is a required field that must follow the proper formatting')).toBeInTheDocument();

      // Should show schema requirement indicators
      expect(screen.getAllByText('Schema Requirement')).toHaveLength(2);
    });

    it('should display schema field name context when different from column name', () => {
      const errorWithDifferentSchemaField: ValidationError[] = [
        {
          row: 1,
          column: 'col_name',
          currentValue: 'invalid',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: 'Custom error message',
          schemaFieldName: 'different_schema_field'
        }
      ];

      render(<ValidationErrorsPanel errors={errorWithDifferentSchemaField} />);

      // Should show schema field context
      expect(screen.getByText('(Schema field: different_schema_field)')).toBeInTheDocument();
    });

    it('should not display schema field context when same as column name', () => {
      const errorWithSameSchemaField: ValidationError[] = [
        {
          row: 1,
          column: 'field_name',
          currentValue: 'invalid',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: 'Custom error message',
          schemaFieldName: 'field_name'
        }
      ];

      render(<ValidationErrorsPanel errors={errorWithSameSchemaField} />);

      // Should not show redundant schema field context
      expect(screen.queryByText('(Schema field: field_name)')).not.toBeInTheDocument();
    });

    it('should fall back to system-generated error messages when custom messages are not available', () => {
      render(<ValidationErrorsPanel errors={errorsWithCustomMessages} />);

      // Should show system-generated message for the error without custom message
      expect(screen.getByText('This field is required and cannot be empty.')).toBeInTheDocument();
      expect(screen.getByText('System Generated')).toBeInTheDocument();
    });

    it('should visually distinguish between schema-defined and system-generated error messages', () => {
      render(<ValidationErrorsPanel errors={errorsWithCustomMessages} />);

      // Should have visual indicators for both types
      expect(screen.getAllByText('Schema Requirement')).toHaveLength(2);
      expect(screen.getByText('System Generated')).toBeInTheDocument();
    });

    it('should display all error types with appropriate fallback messages', () => {
      const errorTypesWithoutCustomMessages: ValidationError[] = [
        {
          row: 1,
          column: 'required_field',
          currentValue: '',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.REQUIRED_VALUE
        },
        {
          row: 2,
          column: 'option_field',
          currentValue: 'invalid',
          validOptions: ['valid1', 'valid2'],
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_OPTION
        },
        {
          row: 3,
          column: 'pattern_field',
          currentValue: 'invalid-format',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN
        }
      ];

      render(<ValidationErrorsPanel errors={errorTypesWithoutCustomMessages} />);

      // Should show appropriate fallback messages for each error type
      expect(screen.getByText('This field is required and cannot be empty.')).toBeInTheDocument();
      expect(screen.getByText('The value is not one of the allowed options.')).toBeInTheDocument();
      expect(screen.getByText('The value does not match the required format.')).toBeInTheDocument();

      // All should be marked as system generated
      expect(screen.getAllByText('System Generated')).toHaveLength(3);
    });

    it('should maintain all existing functionality with custom error messages', () => {
      const onAcceptError = jest.fn();
      const onDismissError = jest.fn();

      render(
        <ValidationErrorsPanel
          errors={errorsWithCustomMessages}
          onAcceptError={onAcceptError}
          onDismissError={onDismissError}
        />
      );

      // Should still show recommendations and allow interactions
      expect(screen.getByText('Recommended: "Amplicon"')).toBeInTheDocument();

      const acceptButton = screen.getByText('Accept Recommendation');
      fireEvent.click(acceptButton);
      expect(onAcceptError).toHaveBeenCalledWith(errorsWithCustomMessages[0]);
    });
  });
});
