/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { ChangesSummaryCard } from '../../../components/metadata/changes-summary-card';
import { ChangesSummary } from '../../../lib/types';
import { theme } from '../../../lib/theme';

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

// Mock data
const mockSummaryWithChanges: ChangesSummary = {
  totalChanges: 15,
  adds: 5,
  removes: 3,
  renames: 7,
  systemChanges: 10,
  userChanges: 5
};

const mockSummaryNoChanges: ChangesSummary = {
  totalChanges: 0,
  adds: 0,
  removes: 0,
  renames: 0,
  systemChanges: 0,
  userChanges: 0
};

const mockSummaryLowChanges: ChangesSummary = {
  totalChanges: 3,
  adds: 1,
  removes: 1,
  renames: 1,
  systemChanges: 2,
  userChanges: 1
};

const mockSummaryMediumChanges: ChangesSummary = {
  totalChanges: 12,
  adds: 4,
  removes: 3,
  renames: 5,
  systemChanges: 8,
  userChanges: 4
};

const mockSummaryHighChanges: ChangesSummary = {
  totalChanges: 25,
  adds: 10,
  removes: 8,
  renames: 7,
  systemChanges: 15,
  userChanges: 10
};

describe('ChangesSummaryCard', () => {
  describe('Loading State', () => {
    it('should render loading skeletons when loading is true', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} loading={true} />
        </TestWrapper>
      );

      // Should show skeleton loaders - check for MUI skeleton classes
      const skeletons = document.querySelectorAll('.MuiSkeleton-root');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('should not render actual content when loading', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} loading={true} />
        </TestWrapper>
      );

      expect(screen.queryByText('Changes Summary')).not.toBeInTheDocument();
      expect(screen.queryByText('15 Total')).not.toBeInTheDocument();
    });
  });

  describe('No Changes State', () => {
    it('should render no changes message when totalChanges is 0', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryNoChanges} />
        </TestWrapper>
      );

      expect(screen.getByText('No Changes Detected')).toBeInTheDocument();
      expect(screen.getByText('Your data remained unchanged during processing.')).toBeInTheDocument();
    });

    it('should apply success styling for no changes', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryNoChanges} />
        </TestWrapper>
      );

      const card = screen.getByText('No Changes Detected').closest('.MuiCard-root');
      expect(card).toHaveStyle('border-color: #2e7d32'); // success.main
    });

    it('should show expand icon when onClick is provided for no changes', () => {
      const mockOnClick = jest.fn();
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryNoChanges} onClick={mockOnClick} />
        </TestWrapper>
      );

      expect(screen.getByTestId('ExpandMoreIcon')).toBeInTheDocument();
    });
  });

  describe('Changes Present State', () => {
    it('should render changes summary with correct totals', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      expect(screen.getByText('Changes Summary')).toBeInTheDocument();
      expect(screen.getByText('15 Total')).toBeInTheDocument();
    });

    it('should display change type breakdown', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      expect(screen.getByText('Change Types')).toBeInTheDocument();
      expect(screen.getByText('Added')).toBeInTheDocument();
      expect(screen.getByText('Removed')).toBeInTheDocument();
      expect(screen.getByText('Modified')).toBeInTheDocument();

      // Check counts - use getAllByText for duplicates
      const fives = screen.getAllByText('5');
      expect(fives.length).toBe(2); // adds and user changes
      expect(screen.getByText('3')).toBeInTheDocument(); // removes
      expect(screen.getByText('7')).toBeInTheDocument(); // renames
    });

    it('should display change source breakdown', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      expect(screen.getByText('Change Sources')).toBeInTheDocument();
      expect(screen.getByText('System')).toBeInTheDocument();
      expect(screen.getByText('User')).toBeInTheDocument();

      // Check counts - use more specific selectors to avoid duplicates
      const systemChip = screen.getByLabelText('Changes recommended by the system');
      const userChip = screen.getByLabelText('Changes made by user input');
      expect(systemChip).toHaveTextContent('10');
      expect(userChip).toHaveTextContent('5');
    });

    it('should display percentage breakdown', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      // 10/15 = 67% system, 5/15 = 33% user
      expect(screen.getByText('67% system, 33% user')).toBeInTheDocument();
    });

    it('should show custom title when provided', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard
            summary={mockSummaryWithChanges}
            title="Custom Changes Title"
          />
        </TestWrapper>
      );

      expect(screen.getByText('Custom Changes Title')).toBeInTheDocument();
      expect(screen.queryByText('Changes Summary')).not.toBeInTheDocument();
    });
  });

  describe('Card Color Coding', () => {
    it('should apply info color for low changes (1-5)', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryLowChanges} />
        </TestWrapper>
      );

      const card = screen.getByText('Changes Summary').closest('.MuiCard-root');
      expect(card).toHaveStyle('border-color: #0288d1'); // info.main
    });

    it('should apply warning color for medium changes (6-20)', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryMediumChanges} />
        </TestWrapper>
      );

      const card = screen.getByText('Changes Summary').closest('.MuiCard-root');
      expect(card).toHaveStyle('border-color: #ed6c02'); // warning.main
    });

    it('should apply error color for high changes (>20)', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryHighChanges} />
        </TestWrapper>
      );

      const card = screen.getByText('Changes Summary').closest('.MuiCard-root');
      expect(card).toHaveStyle('border-color: #d32f2f'); // error.main
    });
  });

  describe('Interactive Features', () => {
    it('should call onClick when card is clicked', () => {
      const mockOnClick = jest.fn();
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} onClick={mockOnClick} />
        </TestWrapper>
      );

      const card = screen.getByText('Changes Summary').closest('.MuiCard-root');
      fireEvent.click(card!);

      expect(mockOnClick).toHaveBeenCalledTimes(1);
    });

    it('should show expand icon when onClick is provided', () => {
      const mockOnClick = jest.fn();
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} onClick={mockOnClick} />
        </TestWrapper>
      );

      expect(screen.getByTestId('ExpandMoreIcon')).toBeInTheDocument();
    });

    it('should not show expand icon when onClick is not provided', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      expect(screen.queryByTestId('ExpandMoreIcon')).not.toBeInTheDocument();
    });

    it('should apply hover effects when clickable', () => {
      const mockOnClick = jest.fn();
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} onClick={mockOnClick} />
        </TestWrapper>
      );

      const card = screen.getByText('Changes Summary').closest('.MuiCard-root');
      expect(card).toHaveStyle('cursor: pointer');
    });

    it('should not apply hover effects when not clickable', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      const card = screen.getByText('Changes Summary').closest('.MuiCard-root');
      expect(card).toHaveStyle('cursor: default');
    });
  });

  describe('Icons and Visual Elements', () => {
    it('should display correct icons for change types', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      expect(screen.getByTestId('AddIcon')).toBeInTheDocument();
      expect(screen.getByTestId('RemoveIcon')).toBeInTheDocument();
      expect(screen.getByTestId('EditIcon')).toBeInTheDocument();
    });

    it('should display correct icons for source types', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      expect(screen.getByTestId('ComputerIcon')).toBeInTheDocument();
      expect(screen.getByTestId('PersonIcon')).toBeInTheDocument();
    });

    it('should display trending up icon in header', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      expect(screen.getByTestId('TrendingUpIcon')).toBeInTheDocument();
    });
  });

  describe('Tooltips', () => {
    it('should show tooltips for system changes', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      const systemChip = screen.getByLabelText('Changes recommended by the system');
      expect(systemChip).toBeInTheDocument();
    });

    it('should show tooltips for user changes', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      const userChip = screen.getByLabelText('Changes made by user input');
      expect(userChip).toBeInTheDocument();
    });
  });

  describe('Footer Messages', () => {
    it('should show clickable footer message when onClick is provided', () => {
      const mockOnClick = jest.fn();
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} onClick={mockOnClick} />
        </TestWrapper>
      );

      expect(screen.getByText('Click to view detailed changes')).toBeInTheDocument();
    });

    it('should show default footer message when onClick is not provided', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      expect(screen.getByText('Changes detected during processing')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes for clickable card', () => {
      const mockOnClick = jest.fn();
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} onClick={mockOnClick} />
        </TestWrapper>
      );

      const card = screen.getByText('Changes Summary').closest('.MuiCard-root');
      expect(card).toBeVisible();
    });

    it('should support keyboard navigation when clickable', () => {
      const mockOnClick = jest.fn();
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} onClick={mockOnClick} />
        </TestWrapper>
      );

      const card = screen.getByText('Changes Summary').closest('.MuiCard-root');
      expect(card).toBeVisible();
    });

    it('should have readable text contrast', () => {
      render(
        <TestWrapper>
          <ChangesSummaryCard summary={mockSummaryWithChanges} />
        </TestWrapper>
      );

      const title = screen.getByText('Changes Summary');
      const changeTypes = screen.getByText('Change Types');
      const changeSources = screen.getByText('Change Sources');

      expect(title).toBeVisible();
      expect(changeTypes).toBeVisible();
      expect(changeSources).toBeVisible();
    });
  });

  describe('Edge Cases', () => {
    it('should handle zero values gracefully', () => {
      const summaryWithZeros: ChangesSummary = {
        totalChanges: 5,
        adds: 0,
        removes: 0,
        renames: 5,
        systemChanges: 5,
        userChanges: 0
      };

      render(
        <TestWrapper>
          <ChangesSummaryCard summary={summaryWithZeros} />
        </TestWrapper>
      );

      // Check that zeros are displayed - use getAllByText since there are multiple zeros
      const zeros = screen.getAllByText('0');
      expect(zeros.length).toBeGreaterThan(0);
      expect(screen.getByText('100% system, 0% user')).toBeInTheDocument();
    });

    it('should handle single change correctly', () => {
      const singleChange: ChangesSummary = {
        totalChanges: 1,
        adds: 1,
        removes: 0,
        renames: 0,
        systemChanges: 1,
        userChanges: 0
      };

      render(
        <TestWrapper>
          <ChangesSummaryCard summary={singleChange} />
        </TestWrapper>
      );

      expect(screen.getByText('1 Total')).toBeInTheDocument();
      expect(screen.getByText('100% system, 0% user')).toBeInTheDocument();
    });

    it('should handle large numbers correctly', () => {
      const largeNumbers: ChangesSummary = {
        totalChanges: 1000,
        adds: 400,
        removes: 300,
        renames: 300,
        systemChanges: 600,
        userChanges: 400
      };

      render(
        <TestWrapper>
          <ChangesSummaryCard summary={largeNumbers} />
        </TestWrapper>
      );

      expect(screen.getByText('1000 Total')).toBeInTheDocument();
      // Check that large numbers are displayed - use getAllByText since there are duplicates
      const fourHundreds = screen.getAllByText('400');
      expect(fourHundreds.length).toBe(2); // adds and user changes
      const threeHundreds = screen.getAllByText('300');
      expect(threeHundreds.length).toBe(2); // removes and renames
      expect(screen.getByText('600')).toBeInTheDocument(); // system
      expect(screen.getByText('60% system, 40% user')).toBeInTheDocument();
    });
  });
});
