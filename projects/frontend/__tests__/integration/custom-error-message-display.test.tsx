/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Integration tests for custom error message display workflow.
 *
 * This module tests the complete workflow from API response parsing
 * through to frontend display of custom error messages from schema definitions.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '../../lib/theme';
import { ValidationErrorsPanel } from '../../components/metadata/validation-errors-panel';
import { ValidationError, ValidationErrorType } from '../../lib/types';

// Mock data that simulates API responses with custom error messages
const mockErrorsWithCustomMessages: ValidationError[] = [
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
    // No custom error message - should fall back to system generated
    errorMessage: null,
    schemaFieldName: 'regular_field'
  }
];

const mockErrorsWithoutCustomMessages: ValidationError[] = [
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

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('Custom Error Message Display Integration', () => {
  describe('Custom Error Message Display', () => {
    it('should display custom error messages prominently when available', async () => {
      renderWithTheme(
        <ValidationErrorsPanel errors={mockErrorsWithCustomMessages} />
      );

      // Wait for component to render - check for actual error content instead of heading
      await waitFor(() => {
        expect(screen.getByText('library_strategy is a required field. Valid input(s) are: ["Amplicon"]')).toBeInTheDocument();
      });

      // Should display custom error messages prominently
      expect(screen.getByText('library_strategy is a required field. Valid input(s) are: ["Amplicon"]')).toBeInTheDocument();
      expect(screen.getByText('sequence_id is a required field that must follow the proper formatting')).toBeInTheDocument();
      expect(screen.getByText('CSID is a required field and must be a ten-digit numerical string with no special characters')).toBeInTheDocument();
      expect(screen.getByText('submitter_state is a required field and must be formatted as the two-letter State abbreviation')).toBeInTheDocument();

      // Should show schema requirement indicators for custom messages
      const schemaRequirementChips = screen.getAllByText('Schema Requirement');
      expect(schemaRequirementChips).toHaveLength(4); // 4 errors with custom messages
    });

    it('should display schema field name context when different from column name', async () => {
      const errorWithDifferentSchemaField: ValidationError[] = [
        {
          row: 1,
          column: 'col_name',
          currentValue: 'invalid',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: 'Custom error message for different schema field',
          schemaFieldName: 'different_schema_field'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={errorWithDifferentSchemaField} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Should show schema field context when different from column name
      expect(screen.getByText('(Schema field: different_schema_field)')).toBeInTheDocument();
      expect(screen.getByText('Custom error message for different schema field')).toBeInTheDocument();
    });

    it('should not display schema field context when same as column name', async () => {
      const errorWithSameSchemaField: ValidationError[] = [
        {
          row: 1,
          column: 'field_name',
          currentValue: 'invalid',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: 'Custom error message for same field',
          schemaFieldName: 'field_name'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={errorWithSameSchemaField} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Should not show redundant schema field context
      expect(screen.queryByText('(Schema field: field_name)')).not.toBeInTheDocument();
      expect(screen.getByText('Custom error message for same field')).toBeInTheDocument();
    });

    it('should fall back to system-generated error display when custom messages are not available', async () => {
      renderWithTheme(
        <ValidationErrorsPanel errors={mockErrorsWithoutCustomMessages} />
      );

      await waitFor(() => {
        const systemGeneratedChips = screen.getAllByText('System Generated');
        expect(systemGeneratedChips.length).toBeGreaterThan(0);
      });

      // Should not show custom error message boxes for system-generated errors
      expect(screen.queryByText('Schema Requirement')).not.toBeInTheDocument();

      // Should show system generated indicators
      const systemGeneratedChips = screen.getAllByText('System Generated');
      expect(systemGeneratedChips).toHaveLength(3); // 3 errors without custom messages

      // Should still display error information
      expect(screen.getByText('Row 1, Column "name"')).toBeInTheDocument();
      expect(screen.getByText('Row 2, Column "email"')).toBeInTheDocument();
      expect(screen.getByText('Row 3, Column "status"')).toBeInTheDocument();

      // Should show current values
      expect(screen.getByText('Current: ""')).toBeInTheDocument(); // Empty name
      expect(screen.getByText('Current: "invalid-email"')).toBeInTheDocument();
      expect(screen.getByText('Current: "invalid-status"')).toBeInTheDocument();
    });

    it('should handle mixed custom and system error messages correctly', async () => {
      const mixedErrors: ValidationError[] = [
        {
          row: 1,
          column: 'field_with_custom',
          currentValue: 'invalid1',
          validOptions: ['option1', 'option2'],
          recommendedValue: 'option1',
          errorType: ValidationErrorType.INVALID_OPTION,
          errorMessage: 'This field has a custom error message from the schema',
          schemaFieldName: 'field_with_custom'
        },
        {
          row: 2,
          column: 'field_without_custom',
          currentValue: 'invalid2',
          validOptions: ['optionA', 'optionB'],
          recommendedValue: 'optionA',
          errorType: ValidationErrorType.INVALID_OPTION,
          errorMessage: null,
          schemaFieldName: 'field_without_custom'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={mixedErrors} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Should show custom error message for first error
      expect(screen.getByText('This field has a custom error message from the schema')).toBeInTheDocument();
      expect(screen.getByText('Schema Requirement')).toBeInTheDocument();

      // Should show system-generated display for second error
      expect(screen.getByText('Row 2, Column "field_without_custom"')).toBeInTheDocument();
      expect(screen.getByText('Current: "invalid2"')).toBeInTheDocument();

      // Should show valid options for both (note: only shown when no recommendation available)
      // Since both errors have recommendedValue, valid options won't be displayed
      expect(screen.getByText('Recommended: "option1"')).toBeInTheDocument();
      expect(screen.getByText('Recommended: "optionA"')).toBeInTheDocument();
    });
  });

  describe('Error Message Formatting and Display', () => {
    it('should format custom error messages with proper styling', async () => {
      renderWithTheme(
        <ValidationErrorsPanel errors={mockErrorsWithCustomMessages.slice(0, 1)} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Check that custom error message is displayed in a styled box
      const customMessageElement = screen.getByText('library_strategy is a required field. Valid input(s) are: ["Amplicon"]');
      expect(customMessageElement).toBeInTheDocument();

      // The message should be in a styled container (info box)
      const messageContainer = customMessageElement.closest('[class*="MuiBox-root"]');
      expect(messageContainer).toBeInTheDocument();
    });

    it('should display error type information correctly', async () => {
      renderWithTheme(
        <ValidationErrorsPanel errors={mockErrorsWithCustomMessages} />
      );

      await waitFor(() => {
        const schemaRequirementChips = screen.getAllByText('Schema Requirement');
        expect(schemaRequirementChips.length).toBeGreaterThan(0);
      });

      // Should show different error types
      expect(screen.getByText('Row 1, Column "library_strategy"')).toBeInTheDocument();
      expect(screen.getByText('Row 2, Column "sequence_id"')).toBeInTheDocument();
      expect(screen.getByText('Row 3, Column "CSID"')).toBeInTheDocument();
      expect(screen.getByText('Row 4, Column "submitter_state"')).toBeInTheDocument();
      expect(screen.getByText('Row 5, Column "regular_field"')).toBeInTheDocument();
    });

    it('should handle long custom error messages gracefully', async () => {
      const errorWithLongMessage: ValidationError[] = [
        {
          row: 1,
          column: 'complex_field',
          currentValue: 'invalid',
          validOptions: null,
          recommendedValue: null,
          errorType: ValidationErrorType.INVALID_PATTERN,
          errorMessage: 'This is a very long custom error message that provides detailed information about what went wrong and what the user should do to fix it. It includes specific formatting requirements, examples of valid values, and additional context about why this validation is important for data quality and downstream processing.',
          schemaFieldName: 'complex_field'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={errorWithLongMessage} />
      );

      await waitFor(() => {
        expect(screen.getByText('Schema Requirement')).toBeInTheDocument();
      });

      // Should display the full long message
      expect(screen.getByText(/This is a very long custom error message/)).toBeInTheDocument();
      expect(screen.getByText(/important for data quality and downstream processing/)).toBeInTheDocument();
    });
  });

  describe('Performance and Rendering', () => {
    it('should render large numbers of errors with custom messages efficiently', async () => {
      // Create a large number of errors with custom messages
      const largeErrorSet: ValidationError[] = [];
      for (let i = 1; i <= 100; i++) {
        largeErrorSet.push({
          row: i,
          column: `field_${i}`,
          currentValue: `invalid_${i}`,
          validOptions: [`valid_${i}_1`, `valid_${i}_2`],
          recommendedValue: `valid_${i}_1`,
          errorType: ValidationErrorType.INVALID_OPTION,
          errorMessage: `Custom error message for field_${i}. Valid options are valid_${i}_1 or valid_${i}_2`,
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
      });

      const renderTime = performance.now() - startTime;

      // Should render within reasonable time (less than 1 second)
      expect(renderTime).toBeLessThan(1000);

      // Should display first few errors
      expect(screen.getByText('Row 1, Column "field_1"')).toBeInTheDocument();
      expect(screen.getByText('Custom error message for field_1. Valid options are valid_1_1 or valid_1_2')).toBeInTheDocument();
    });

    it('should handle rapid error updates without performance issues', async () => {
      const { rerender } = renderWithTheme(
        <ValidationErrorsPanel errors={[]} />
      );

      // Simulate rapid updates with different error sets
      const updateSets = [
        mockErrorsWithCustomMessages.slice(0, 1),
        mockErrorsWithCustomMessages.slice(0, 2),
        mockErrorsWithCustomMessages.slice(0, 3),
        mockErrorsWithCustomMessages,
        mockErrorsWithoutCustomMessages
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
            const schemaRequirementChips = screen.getAllByText('Schema Requirement');
            expect(schemaRequirementChips.length).toBeGreaterThan(0);
          });
        } else {
          // Last set has no custom messages
          await waitFor(() => {
            const systemGeneratedChips = screen.getAllByText('System Generated');
            expect(systemGeneratedChips.length).toBeGreaterThan(0);
          });
        }

        const updateTime = performance.now() - updateStart;
        expect(updateTime).toBeLessThan(100); // Should update quickly
      }
    });
  });

  describe('Backward Compatibility', () => {
    it('should maintain compatibility with existing validation workflows', async () => {
      // Test that the component works with both old and new error formats
      const legacyErrors: ValidationError[] = [
        {
          row: 1,
          column: 'legacy_field',
          currentValue: 'invalid',
          validOptions: ['valid1', 'valid2'],
          recommendedValue: 'valid1',
          errorType: ValidationErrorType.INVALID_OPTION,
          // Legacy format - no custom error message fields
          errorMessage: null,
          schemaFieldName: 'legacy_field'
        }
      ];

      renderWithTheme(
        <ValidationErrorsPanel errors={legacyErrors} />
      );

      await waitFor(() => {
        expect(screen.getByText('System Generated')).toBeInTheDocument();
      });

      // Should display legacy error correctly
      expect(screen.getByText('Row 1, Column "legacy_field"')).toBeInTheDocument();
      expect(screen.getByText('Current: "invalid"')).toBeInTheDocument();
      expect(screen.getByText('Recommended: "valid1"')).toBeInTheDocument();

      // Should show system generated indicator, not custom message indicator
      expect(screen.getByText('System Generated')).toBeInTheDocument();
      expect(screen.queryByText('Schema Requirement')).not.toBeInTheDocument();
    });

    it('should handle missing or undefined custom message fields gracefully', async () => {
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

  describe('Accessibility and User Experience', () => {
    it('should provide proper ARIA labels and accessibility features', async () => {
      renderWithTheme(
        <ValidationErrorsPanel errors={mockErrorsWithCustomMessages.slice(0, 2)} />
      );

      await waitFor(() => {
        const schemaRequirementChips = screen.getAllByText('Schema Requirement');
        expect(schemaRequirementChips.length).toBeGreaterThan(0);
      });

      // Should have proper list structure for errors
      const errorList = screen.getByRole('list');
      expect(errorList).toBeInTheDocument();

      // Should have proper button accessibility for actions (only when callbacks are provided)
      // Since we didn't provide onAcceptError callback, no buttons should be present
      const buttons = screen.queryAllByRole('button');
      expect(buttons.length).toBe(0); // No buttons without callbacks
    });

    it('should provide clear visual hierarchy for custom vs system messages', async () => {
      const mixedErrors = [
        mockErrorsWithCustomMessages[0], // Has custom message
        mockErrorsWithoutCustomMessages[0] // No custom message
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
    });
  });
});
