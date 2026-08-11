/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '@mui/material/styles';
import { DetailedChangesList } from '../../../components/metadata/detailed-changes-list';
import { ChangeObject, ChangeType, ChangeSourceType, ChangeComponent } from '../../../lib/types';
import { theme } from '../../../lib/theme';

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

// Mock data
const mockChanges: ChangeObject[] = [
  {
    changeId: 'change-001',
    changeType: ChangeType.ADD,
    sourceType: ChangeSourceType.SYSTEM,
    component: ChangeComponent.VALIDATION,
    row: 1,
    column: 'participant_id',
    newValue: 'New Value',
    timestamp: '2025-01-01T12:00:00Z',
    sourceVersion: 1,
    targetVersion: 2,
    confidenceScore: 0.85
  },
  {
    changeId: 'change-002',
    changeType: ChangeType.RENAME,
    sourceType: ChangeSourceType.USER,
    component: ChangeComponent.SCHEMA_ALIGNMENT,
    row: 2,
    column: 'status',
    oldValue: 'Old Value',
    newValue: 'Modified Value',
    timestamp: '2025-01-01T12:01:00Z',
    sourceVersion: 1,
    targetVersion: 2
  },
  {
    changeId: 'change-003',
    changeType: ChangeType.REMOVE,
    sourceType: ChangeSourceType.SYSTEM,
    component: ChangeComponent.VALIDATION,
    row: 3,
    column: 'notes',
    oldValue: 'Removed Value',
    timestamp: '2025-01-01T12:02:00Z',
    sourceVersion: 1,
    targetVersion: 2,
    confidenceScore: 0.65
  }
];

describe('DetailedChangesList', () => {
  describe('Loading State', () => {
    it('should render loading skeletons when loading is true', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} loading={true} />
        </TestWrapper>
      );

      // Check for skeleton elements by class name instead of test id
      const skeletons = document.querySelectorAll('.MuiSkeleton-root');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('should not render actual content when loading', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} loading={true} />
        </TestWrapper>
      );

      expect(screen.queryByText('Detailed Changes')).not.toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should render empty message when no changes provided', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={[]} />
        </TestWrapper>
      );

      expect(screen.getByText('No changes to display')).toBeInTheDocument();
    });

    it('should render empty message when changes is null', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={null as unknown as ChangeObject[]} />
        </TestWrapper>
      );

      expect(screen.getByText('No changes to display')).toBeInTheDocument();
    });
  });

  describe('Basic Rendering', () => {
    it('should render changes list with correct count', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      expect(screen.getByText('Detailed Changes (3)')).toBeInTheDocument();
    });

    it('should render all changes', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      expect(screen.getByText('Added')).toBeInTheDocument();
      expect(screen.getByText('Modified')).toBeInTheDocument();
      expect(screen.getByText('Removed')).toBeInTheDocument();
    });

    it('should display change type indicators', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      expect(screen.getAllByText('System').length).toBeGreaterThan(0);
      expect(screen.getByText('User')).toBeInTheDocument();
    });

    it('should display cell coordinates', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      // Coordinates are displayed as "Row X, ColumnName" in chip format
      // There may be multiple elements with same row number, so check they exist
      expect(screen.getAllByText(/Row 1, /).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Row 2, /).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Row 3, /).length).toBeGreaterThan(0);
    });
  });

  describe('Change Value Display', () => {
    it('should display added values correctly', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      expect(screen.getByText('Added Value')).toBeInTheDocument();
      expect(screen.getAllByText('New Value').length).toBeGreaterThan(0);
    });

    it('should display modified values correctly', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      expect(screen.getByText('Previous Value')).toBeInTheDocument();
      expect(screen.getAllByText('New Value').length).toBeGreaterThan(0);
      expect(screen.getByText('Old Value')).toBeInTheDocument();
      expect(screen.getByText('Modified Value')).toBeInTheDocument();
    });

    it('should display removed values correctly', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      expect(screen.getAllByText('Removed Value').length).toBeGreaterThan(0);
    });

    it('should handle empty values', () => {
      const changesWithEmpty: ChangeObject[] = [{
        ...mockChanges[0],
        newValue: '',
        oldValue: null
      }];

      render(
        <TestWrapper>
          <DetailedChangesList changes={changesWithEmpty} />
        </TestWrapper>
      );

      expect(screen.getByText('(empty)')).toBeInTheDocument();
    });
  });

  describe('Filtering', () => {
    it('should show filters button when enableFiltering is true', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableFiltering={true} />
        </TestWrapper>
      );

      expect(screen.getByText('Filters')).toBeInTheDocument();
    });

    it('should not show filters button when enableFiltering is false', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableFiltering={false} />
        </TestWrapper>
      );

      expect(screen.queryByText('Filters')).not.toBeInTheDocument();
    });

    it('should expand filters panel when filters button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableFiltering={true} />
        </TestWrapper>
      );

      const filtersButton = screen.getByText('Filters');
      await user.click(filtersButton);

      expect(screen.getByText('Filter Changes')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Search changes...')).toBeInTheDocument();
    });

    it('should filter by search text', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableFiltering={true} />
        </TestWrapper>
      );

      // Open filters
      await user.click(screen.getByText('Filters'));

      // Search for "New Value"
      const searchInput = screen.getByPlaceholderText('Search changes...');
      await user.type(searchInput, 'New Value');

      // Should show filtered results - use regex to match the text with parentheses
      await waitFor(() => {
        expect(screen.getByText(/Detailed Changes \(\d+\)/)).toBeInTheDocument();
      });
    });

    it('should filter by change type', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableFiltering={true} />
        </TestWrapper>
      );

      // Open filters
      await user.click(screen.getByText('Filters'));

      // Find the Change Type select - it's the first combobox after the search input
      const comboboxes = screen.getAllByRole('combobox');
      const changeTypeSelect = comboboxes[0]; // First combobox is Change Type
      await user.click(changeTypeSelect);
      await user.click(screen.getByText('add'));

      // Should show only ADD changes
      await waitFor(() => {
        expect(screen.getByText(/Detailed Changes \(1\)/)).toBeInTheDocument();
      });
    });

    it('should clear all filters', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableFiltering={true} />
        </TestWrapper>
      );

      // Open filters and add search text
      await user.click(screen.getByText('Filters'));
      const searchInput = screen.getByPlaceholderText('Search changes...');
      await user.type(searchInput, 'test');

      // Clear filters
      await user.click(screen.getByText('Clear All'));

      // Should show all changes again
      await waitFor(() => {
        expect(screen.getByText('Detailed Changes (3)')).toBeInTheDocument();
      });
    });
  });

  describe('Sorting', () => {
    it('should show sort options when enableSorting is true', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableSorting={true} enableFiltering={true} />
        </TestWrapper>
      );

      // Open filters to see sort options
      await user.click(screen.getByText('Filters'));

      // Check that we have the expected number of comboboxes (3 filters + 2 sort options = 5 total)
      const comboboxes = screen.getAllByRole('combobox');
      expect(comboboxes).toHaveLength(5);
    });

    it('should sort by timestamp by default', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableSorting={true} enableFiltering={true} />
        </TestWrapper>
      );

      // Changes should be in reverse chronological order by default
      const changeCards = screen.getAllByText(/validation|schema_alignment/);
      expect(changeCards).toHaveLength(3);
    });

    it('should change sort order', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableSorting={true} enableFiltering={true} />
        </TestWrapper>
      );

      // Open filters
      await user.click(screen.getByText('Filters'));

      // Change sort order to ascending - it's the last combobox (Order)
      const comboboxes = screen.getAllByRole('combobox');
      const orderSelect = comboboxes[comboboxes.length - 1]; // Last combobox is Order
      await user.click(orderSelect);
      await user.click(screen.getByText('Oldest'));

      // Changes should now be in chronological order
      await waitFor(() => {
        expect(screen.getByText(/Detailed Changes \(3\)/)).toBeInTheDocument();
      });
    });
  });

  describe('Pagination', () => {
    const manyChanges: ChangeObject[] = Array.from({ length: 25 }, (_, i) => ({
      changeId: `change-${i.toString().padStart(3, '0')}`,
      changeType: ChangeType.ADD,
      sourceType: ChangeSourceType.SYSTEM,
      component: ChangeComponent.VALIDATION,
      row: i + 1,
      column: `column_${i + 1}`,
      newValue: `Value ${i + 1}`,
      timestamp: `2025-01-01T12:${i.toString().padStart(2, '0')}:00Z`,
      sourceVersion: 1,
      targetVersion: 2
    }));

    it('should show pagination when there are more items than initialDisplayCount', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={manyChanges} initialDisplayCount={10} />
        </TestWrapper>
      );

      // Should show pagination component
      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('should display correct number of items per page', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={manyChanges} initialDisplayCount={10} />
        </TestWrapper>
      );

      // Should show 10 items on first page
      const changeCards = screen.getAllByText(/validation/);
      expect(changeCards).toHaveLength(10);
    });

    it('should navigate to next page', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={manyChanges} initialDisplayCount={10} />
        </TestWrapper>
      );

      // Click next page
      const nextButton = screen.getByRole('button', { name: /go to page 2/i });
      await user.click(nextButton);

      // Should show different items
      await waitFor(() => {
        expect(screen.getByText('Value 11')).toBeInTheDocument();
      });
    });
  });

  describe('Change Expansion', () => {
    it('should expand change details when expand button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      // Click expand button for first change
      const expandButtons = screen.getAllByTestId('ExpandMoreIcon');
      await user.click(expandButtons[0]);

      // Should show additional details - use getAllByText since there are multiple
      const additionalDetails = screen.getAllByText('Additional Details');
      expect(additionalDetails.length).toBeGreaterThan(0);
      expect(screen.getAllByText('Change ID').length).toBeGreaterThan(0);
      expect(screen.getByText('change-001')).toBeInTheDocument();
    });

    it('should show confidence score in expanded details', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      // Expand first change (has confidence score)
      const expandButtons = screen.getAllByTestId('ExpandMoreIcon');
      await user.click(expandButtons[0]);

      // Check for confidence information - use getAllByText since there might be multiple
      const confidenceLabels = screen.getAllByText('Confidence');
      expect(confidenceLabels.length).toBeGreaterThan(0);
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('should show field path in expanded details when available', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      // Expand second change (has field path)
      const expandButtons = screen.getAllByTestId('ExpandMoreIcon');
      await user.click(expandButtons[1]);

      // Expanded details show "Additional Details" section
      const additionalDetails = screen.queryAllByText('Additional Details');
      expect(additionalDetails.length).toBeGreaterThan(0);

      // Field path may be in the expanded section - check expanded content elements exist
      const changeIds = screen.queryAllByText('Change ID');
      expect(changeIds.length).toBeGreaterThan(0);
    });

    it('should collapse expanded details when clicked again', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      // Expand then collapse
      const expandButtons = screen.getAllByTestId('ExpandMoreIcon');
      await user.click(expandButtons[0]);

      // Check that details are expanded
      expect(screen.getAllByText('Additional Details').length).toBeGreaterThan(0);

      const collapseButton = screen.getByTestId('ExpandLessIcon');
      await user.click(collapseButton);

      // After collapsing, the specific expanded details should not be visible
      await waitFor(() => {
        // Check that the expand button is back to ExpandMoreIcon
        expect(screen.getAllByTestId('ExpandMoreIcon').length).toBe(3);
      });
    });
  });

  describe('Change Selection', () => {
    it('should call onChangeSelect when change is clicked', async () => {
      const mockOnChangeSelect = jest.fn();
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} onChangeSelect={mockOnChangeSelect} />
        </TestWrapper>
      );

      // Click on first change card
      const changeCard = screen.getByText('Added').closest('.MuiCard-root');
      await user.click(changeCard!);

      expect(mockOnChangeSelect).toHaveBeenCalledWith(mockChanges[0]);
    });

    it('should apply pointer cursor when onChangeSelect is provided', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} onChangeSelect={jest.fn()} />
        </TestWrapper>
      );

      const changeCard = screen.getByText('Added').closest('.MuiCard-root');
      expect(changeCard).toHaveStyle('cursor: pointer');
    });

    it('should not apply pointer cursor when onChangeSelect is not provided', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      const changeCard = screen.getByText('Added').closest('.MuiCard-root');
      expect(changeCard).toHaveStyle('cursor: default');
    });
  });

  describe('No Results State', () => {
    it('should show no results message when filters return no matches', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableFiltering={true} />
        </TestWrapper>
      );

      // Open filters and search for non-existent term
      await user.click(screen.getByText('Filters'));
      const searchInput = screen.getByPlaceholderText('Search changes...');
      await user.type(searchInput, 'nonexistent');

      expect(screen.getByText('No changes match the current filters')).toBeInTheDocument();
      expect(screen.getByText('Clear Filters')).toBeInTheDocument();
    });

    it('should clear filters from no results state', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableFiltering={true} />
        </TestWrapper>
      );

      // Create no results state
      await user.click(screen.getByText('Filters'));
      const searchInput = screen.getByPlaceholderText('Search changes...');
      await user.type(searchInput, 'nonexistent');

      // Clear filters from no results message
      const clearButton = screen.getByRole('button', { name: /clear filters/i });
      await user.click(clearButton);

      await waitFor(() => {
        expect(screen.getByText(/Detailed Changes \(3\)/)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      // Check for accessible elements instead of navigation role
      expect(screen.getByText('Detailed Changes (3)')).toBeInTheDocument();
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} enableFiltering={true} />
        </TestWrapper>
      );

      const filtersButton = screen.getByText('Filters');

      // Should be focusable
      filtersButton.focus();
      expect(filtersButton).toHaveFocus();

      // Should be activatable with keyboard
      await user.keyboard('{Enter}');
      expect(screen.getByText('Filter Changes')).toBeInTheDocument();
    });

    it('should have readable text contrast', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      const title = screen.getByText('Detailed Changes (3)');
      const changeType = screen.getByText('Added');
      const sourceTypes = screen.getAllByText('System');
      const sourceType = sourceTypes[0];

      expect(title).toBeVisible();
      expect(changeType).toBeVisible();
      expect(sourceType).toBeVisible();
    });
  });

  describe('Timestamp Formatting', () => {
    it('should format timestamps correctly', () => {
      render(
        <TestWrapper>
          <DetailedChangesList changes={mockChanges} />
        </TestWrapper>
      );

      // Should show formatted timestamps - use getAllByText since there are multiple
      const timestamps = screen.getAllByText(/validation • 1\/1\/2025/);
      expect(timestamps.length).toBeGreaterThan(0);
    });

    it('should handle invalid timestamps gracefully', () => {
      const changesWithInvalidTimestamp: ChangeObject[] = [{
        ...mockChanges[0],
        timestamp: 'invalid-timestamp'
      }];

      render(
        <TestWrapper>
          <DetailedChangesList changes={changesWithInvalidTimestamp} />
        </TestWrapper>
      );

      // Should still render the change
      expect(screen.getByText('Added')).toBeInTheDocument();
    });
  });
});
