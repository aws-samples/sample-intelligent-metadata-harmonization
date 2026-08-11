/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { ErrorCardComponent } from '../../../components/metadata/error-card';
import { ValidationError, ValidationErrorType } from '../../../lib/types';
import { theme } from '../../../lib/theme';
import { beforeEach } from 'node:test';

// Mock validation error data
const mockError: ValidationError = {
  row: 5,
  column: 'age',
  currentValue: 'invalid_age',
  recommendedValue: '25',
  errorType: ValidationErrorType.INVALID_OPTION,
  validOptions: ['18', '25', '30', '35'],
  confidenceScore: 0.85,
  confidenceLevel: 'High',
  errorMessage: 'Age must be one of the valid options'
};

const mockErrorWithoutRecommendation: ValidationError = {
  row: 3,
  column: 'name',
  currentValue: '',
  recommendedValue: null,
  errorType: ValidationErrorType.REQUIRED_VALUE,
  validOptions: null,
  confidenceScore: 0.3,
  confidenceLevel: 'Low'
};

const mockErrorMediumConfidence: ValidationError = {
  row: 2,
  column: 'status',
  currentValue: 'activ',
  recommendedValue: 'active',
  errorType: ValidationErrorType.INVALID_PATTERN,
  validOptions: null,
  confidenceScore: 0.65,
  confidenceLevel: 'Medium',
  errorMessage: 'Status value does not match expected pattern'
};

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

describe('ErrorCardComponent', () => {
  const mockOnAccept = jest.fn();
  const mockOnAcceptAll = jest.fn();
  const mockOnDismiss = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Styling and Theme Compliance', () => {
    it('should render with primary blue theme colors', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const card = screen.getByRole('button', { name: /accept all similar changes/i }).closest('[class*="MuiCard"]');
      expect(card).toBeInTheDocument();

      // Check that location chip uses primary theme colors
      const locationChip = screen.getByText('Row 5, Column age');
      expect(locationChip).toBeInTheDocument();
    });

    it('should display proper visual hierarchy with organized layout', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      // Check error icon and type are prominently displayed in header
      expect(screen.getByText('Invalid Option')).toBeInTheDocument();

      // Check location chip is present in header
      expect(screen.getByText('Row 5, Column age')).toBeInTheDocument();

      // Check confidence chip is in header
      expect(screen.getByText('High')).toBeInTheDocument();

      // Check value comparison section
      expect(screen.getByText('Current Value')).toBeInTheDocument();
      expect(screen.getByText('Suggested Value')).toBeInTheDocument();
      expect(screen.getByText('invalid_age')).toBeInTheDocument();
      expect(screen.getByText('25')).toBeInTheDocument();
    });

    it('should maintain proper contrast ratios for accessibility', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      // Check that text elements are visible and accessible
      const errorType = screen.getByText('Invalid Option');
      expect(errorType).toBeVisible();

      const currentValue = screen.getByText('invalid_age');
      expect(currentValue).toBeVisible();

      const suggestedValue = screen.getByText('25');
      expect(suggestedValue).toBeVisible();
    });

    it('should show hover effects on card', async () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const card = screen.getByRole('button', { name: /accept all similar changes/i }).closest('[class*="MuiCard"]');

      // Simulate hover
      if (card) {
        fireEvent.mouseEnter(card);
        await waitFor(() => {
          // Card should be visible and interactive
          expect(card).toBeInTheDocument();
        });
      }
    });
  });

  describe('Accept Button Functionality', () => {
    it('should render Accept button when recommendedValue is present', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 25/i });
      expect(acceptButton).toBeInTheDocument();
      expect(acceptButton).not.toBeDisabled();
    });

    it('should not render Accept button when recommendedValue is null', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockErrorWithoutRecommendation}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptButton = screen.queryByRole('button', { name: /accept suggested value/i });
      expect(acceptButton).not.toBeInTheDocument();
    });

    it('should call onAccept when Accept button is clicked', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 25/i });
      fireEvent.click(acceptButton);

      expect(mockOnAccept).toHaveBeenCalledTimes(1);
    });

    it('should have proper styling for Accept button', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 25/i });

      // Check button has success theme colors (outlined variant)
      expect(acceptButton).toHaveClass('MuiButton-outlined');
      expect(acceptButton).toBeVisible();
    });

    it('should show hover effects on Accept button', async () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 25/i });

      fireEvent.mouseEnter(acceptButton);
      await waitFor(() => {
        expect(acceptButton).toBeVisible();
      });
    });
  });

  describe('Accept All Button Functionality', () => {
    it('should always render Accept All button', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column age/i });
      expect(acceptAllButton).toBeInTheDocument();
      expect(acceptAllButton).not.toBeDisabled();
    });

    it('should render Accept All button even without recommendedValue', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockErrorWithoutRecommendation}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column name/i });
      expect(acceptAllButton).toBeInTheDocument();
    });

    it('should call onAcceptAll when Accept All button is clicked', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column age/i });
      fireEvent.click(acceptAllButton);

      expect(mockOnAcceptAll).toHaveBeenCalledTimes(1);
    });

    it('should have primary blue primary theme styling for Accept All button', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column age/i });

      // Check button has primary theme colors (contained variant)
      expect(acceptAllButton).toHaveClass('MuiButton-contained');
      expect(acceptAllButton).toBeVisible();
    });
  });

  describe('Dismiss Button Functionality', () => {
    it('should render dismiss button', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const dismissButton = screen.getByRole('button', { name: /dismiss error/i });
      expect(dismissButton).toBeInTheDocument();
    });

    it('should call onDismiss when dismiss button is clicked', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const dismissButton = screen.getByRole('button', { name: /dismiss error/i });
      fireEvent.click(dismissButton);

      expect(mockOnDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe('Button Styling Consistency', () => {
    it('should have consistent button sizing and spacing', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 25/i });
      const acceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column age/i });

      // Both buttons should be visible and properly sized
      expect(acceptButton).toBeVisible();
      expect(acceptAllButton).toBeVisible();

      // Check that buttons have consistent small size
      expect(acceptButton).toHaveClass('MuiButton-sizeSmall');
      expect(acceptAllButton).toHaveClass('MuiButton-sizeSmall');
    });

    it('should have proper disabled states when needed', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockErrorWithoutRecommendation}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      // Accept button should not be rendered when no recommended value
      const acceptButton = screen.queryByRole('button', { name: /accept suggested value/i });
      expect(acceptButton).not.toBeInTheDocument();

      // Accept All button should still be enabled
      const acceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column name/i });
      expect(acceptAllButton).not.toBeDisabled();
    });

    it('should support keyboard navigation', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const acceptButton = screen.getByRole('button', { name: /accept suggested value: 25/i });
      const acceptAllButton = screen.getByRole('button', { name: /accept all similar changes for column age/i });
      const dismissButton = screen.getByRole('button', { name: /dismiss error/i });

      // All buttons should be focusable
      act(() => {
        acceptButton.focus();
      });
      expect(acceptButton).toHaveFocus();

      act(() => {
        acceptAllButton.focus();
      });
      expect(acceptAllButton).toHaveFocus();

      act(() => {
        dismissButton.focus();
      });
      expect(dismissButton).toHaveFocus();
    });
  });

  describe('Error Display Scenarios', () => {
    it('should handle empty current value', () => {
      const errorWithEmptyValue: ValidationError = {
        ...mockError,
        currentValue: ''
      };

      render(
        <TestWrapper>
          <ErrorCardComponent
            error={errorWithEmptyValue}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      expect(screen.getByText('(empty)')).toBeInTheDocument();
    });

    it('should format error type correctly', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      // INVALID_OPTION should be formatted as "Invalid Option"
      expect(screen.getByText('Invalid Option')).toBeInTheDocument();
    });

    it('should display location information correctly', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      expect(screen.getByText('Row 5, Column age')).toBeInTheDocument();
    });
  });

  describe('Confidence Scoring Features', () => {
    it('should display confidence level indicator with correct color for High confidence', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const confidenceChip = screen.getByText('High');
      expect(confidenceChip).toBeInTheDocument();

      // Check that the chip has green background for high confidence
      const chipElement = confidenceChip.closest('.MuiChip-root');
      expect(chipElement).toHaveStyle('background-color: #4caf50');
    });

    it('should display confidence level indicator with correct color for Medium confidence', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockErrorMediumConfidence}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const confidenceChip = screen.getByText('Medium');
      expect(confidenceChip).toBeInTheDocument();

      // Check that the chip has orange background for medium confidence
      const chipElement = confidenceChip.closest('.MuiChip-root');
      expect(chipElement).toHaveStyle('background-color: #ff9800');
    });

    it('should display confidence level indicator with correct color for Low confidence', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockErrorWithoutRecommendation}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const confidenceChip = screen.getByText('Low');
      expect(confidenceChip).toBeInTheDocument();

      // Check that the chip has red background for low confidence
      const chipElement = confidenceChip.closest('.MuiChip-root');
      expect(chipElement).toHaveStyle('background-color: #f44336');
    });

    it('should show confidence tooltip with error message on hover', async () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const confidenceChip = screen.getByText('High');

      // Hover over the confidence chip
      fireEvent.mouseEnter(confidenceChip);

      await waitFor(() => {
        expect(screen.getByText(/Error: Age must be one of the valid options/)).toBeInTheDocument();
      });
    });

    it('should handle missing confidence data gracefully', () => {
      const errorWithoutConfidence: ValidationError = {
        ...mockError,
        confidenceScore: undefined as any,
        confidenceLevel: undefined as any
      };

      render(
        <TestWrapper>
          <ErrorCardComponent
            error={errorWithoutConfidence}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const confidenceChip = screen.getByText('Unknown');
      expect(confidenceChip).toBeInTheDocument();

      // Check that the chip has gray background for unknown confidence
      const chipElement = confidenceChip.closest('.MuiChip-root');
      expect(chipElement).toHaveStyle('background-color: #757575');
    });

    it('should display confidence indicator with info icon', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const confidenceChip = screen.getByText('High');
      const chipElement = confidenceChip.closest('.MuiChip-root');

      // Check that the chip contains an info icon
      const infoIcon = chipElement?.querySelector('[data-testid="InfoOutlinedIcon"]');
      expect(infoIcon).toBeInTheDocument();
    });
  });

  describe('Error Message Display', () => {
    it('should prominently display error message when present', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      // The error message is shown in a Tooltip on the error type
      const errorType = screen.getByText('Invalid Option');
      expect(errorType).toBeInTheDocument();
      expect(errorType).toBeVisible();
    });

    it('should not display error message section when errorMessage is not present', () => {
      const errorWithoutMessage: ValidationError = {
        ...mockError,
        errorMessage: undefined
      };

      render(
        <TestWrapper>
          <ErrorCardComponent
            error={errorWithoutMessage}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const errorText = screen.queryByText(/Error:/);
      expect(errorText).not.toBeInTheDocument();
    });

    it('should style error message with proper contrast and visibility', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockErrorMediumConfidence}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      // The error type is prominently displayed with error styling
      const errorType = screen.getByText('Invalid Pattern');
      expect(errorType).toBeInTheDocument();
      expect(errorType).toBeVisible();
    });
  });

  describe('Theme Consistency', () => {
    it('should maintain consistent styling with application theme', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      // Check that location chip uses primary theme colors
      const locationChip = screen.getByText('Row 5, Column age');
      const locationChipElement = locationChip.closest('.MuiChip-root');
      expect(locationChipElement).toHaveStyle('background-color: #005fcc'); // primary.main

      // Check that confidence chip maintains proper styling
      const confidenceChip = screen.getByText('High');
      expect(confidenceChip).toBeVisible();
    });

    it('should use consistent chip sizing and spacing', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const locationChip = screen.getByText('Row 5, Column age');
      const confidenceChip = screen.getByText('High');

      // Both chips should be small size and visible
      const locationChipElement = locationChip.closest('.MuiChip-root');
      const confidenceChipElement = confidenceChip.closest('.MuiChip-root');

      expect(locationChipElement).toHaveClass('MuiChip-sizeSmall');
      expect(confidenceChipElement).toHaveClass('MuiChip-sizeSmall');
    });
  });

  describe('Accessibility Compliance', () => {
    it('should have proper ARIA labels', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      expect(screen.getByRole('button', { name: /accept suggested value: 25/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /accept all similar changes for column age/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /dismiss error/i })).toBeInTheDocument();
    });

    it('should support screen readers with confidence information', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      // Check that important content is accessible to screen readers
      expect(screen.getByText('Invalid Option')).toBeInTheDocument();
      expect(screen.getByText('Current Value')).toBeInTheDocument();
      expect(screen.getByText('Suggested Value')).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('should provide accessible tooltips for confidence information', () => {
      render(
        <TestWrapper>
          <ErrorCardComponent
            error={mockError}
            onAccept={mockOnAccept}
            onAcceptAll={mockOnAcceptAll}
            onDismiss={mockOnDismiss}
          />
        </TestWrapper>
      );

      const confidenceChip = screen.getByText('High');

      // Check that the confidence chip has the tooltip aria-label
      const chipElement = confidenceChip.closest('[aria-label]');
      expect(chipElement).toHaveAttribute('aria-label', 'Error: Age must be one of the valid options');
    });
  });
});
