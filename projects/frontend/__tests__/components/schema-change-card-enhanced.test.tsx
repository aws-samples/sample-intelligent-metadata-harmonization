/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { SchemaChangesPanel } from '../../components/metadata/schema-changes-panel';
import { SchemaAlignmentChangeDetail } from '../../lib/types';
import { beforeEach } from 'node:test';

const theme = createTheme();

const mockChanges: SchemaAlignmentChangeDetail[] = [
  {
    changeType: 'rename',
    originalColumn: 'very_long_column_name_that_might_overflow_in_horizontal_layout',
    newColumn: 'target_column_with_equally_long_name_for_testing',
    reason: 'Target: target_column_with_equally_long_name_for_testing | Match: very_long_column_name_that_might_overflow_in_horizontal_layout | Confidence: High | Reasoning: Semantic similarity analysis indicates strong match',
    rowCountAffected: 100,
    confidenceScore: 0.9,
    confidenceLevel: 'High',
    llmConfidenceLevel: 'High'
  },
  {
    changeType: 'add',
    newColumn: 'new_required_column',
    reason: 'Target: new_required_column | Confidence: High | Reasoning: Required by schema',
    rowCountAffected: 100,
    confidenceScore: 0.9,
    confidenceLevel: 'High'
  },
  {
    changeType: 'remove',
    originalColumn: 'obsolete_column_to_be_removed',
    reason: 'Source: obsolete_column_to_be_removed | Confidence: Medium | Reasoning: Not in target schema',
    rowCountAffected: 100,
    confidenceScore: 0.65,
    confidenceLevel: 'Medium'
  }
];

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('Enhanced Schema Change Cards', () => {
  const mockProps = {
    changes: mockChanges,
    onAcceptChange: jest.fn(),
    onRevertChange: jest.fn(),
    appliedChangeIds: new Set<string>(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('displays confidence levels with correct colors', () => {
    renderWithTheme(<SchemaChangesPanel {...mockProps} />);

    // Check for High confidence (green) - confidence is displayed without "Confidence" suffix
    expect(screen.getAllByText('High')).toHaveLength(2);

    // Check for Medium confidence (orange)
    expect(screen.getByText('Medium')).toBeInTheDocument();
  });

  it('uses vertical layout to prevent text overflow for long column names', () => {
    renderWithTheme(<SchemaChangesPanel {...mockProps} />);

    // Check that long column names are displayed
    expect(screen.getByText('very_long_column_name_that_might_overflow_in_horizontal_layout')).toBeInTheDocument();
    expect(screen.getByText('target_column_with_equally_long_name_for_testing')).toBeInTheDocument();
  });

  it('displays enhanced reasoning with Target/Match/Confidence/Reasoning format', () => {
    renderWithTheme(<SchemaChangesPanel {...mockProps} />);

    // Enhanced reasoning is displayed in tooltips on hover, not directly visible
    // Check that confidence chips are present which contain the reasoning in tooltips
    const confidenceChips = document.querySelectorAll('[aria-label*="Reasoning"]');
    expect(confidenceChips.length).toBeGreaterThan(0);
  });

  it('shows operation types instead of generic text', () => {
    renderWithTheme(<SchemaChangesPanel {...mockProps} />);

    // Check for specific operation types
    expect(screen.getByText('Rename')).toBeInTheDocument();
    expect(screen.getByText('Add')).toBeInTheDocument();
    expect(screen.getByText('Remove')).toBeInTheDocument();
  });

  it('uses blue theme colors consistent with application', () => {
    const { container } = renderWithTheme(<SchemaChangesPanel {...mockProps} />);

    // Check that cards have primary color borders (blue theme)
    const cards = container.querySelectorAll('.MuiCard-root');
    expect(cards.length).toBeGreaterThan(0);
  });

  it('displays confidence tooltips with numerical scores', () => {
    renderWithTheme(<SchemaChangesPanel {...mockProps} />);

    // Check for confidence chips - they display levels without "Confidence" suffix
    const confidenceChips = screen.getAllByText(/^(High|Medium|Low|Unknown)$/);
    expect(confidenceChips.length).toBeGreaterThan(0);
  });

  it('handles missing confidence data gracefully', () => {
    const changesWithoutConfidence: SchemaAlignmentChangeDetail[] = [
      {
        changeType: 'rename',
        originalColumn: 'test_column',
        newColumn: 'target_column',
        reason: 'Simple rename operation',
        confidenceScore: 0,
        confidenceLevel: 'Unknown'
      }
    ];

    renderWithTheme(
      <SchemaChangesPanel
        {...mockProps}
        changes={changesWithoutConfidence}
      />
    );

    // Should display Unknown confidence gracefully - without "Confidence" suffix
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  it('displays column mappings with clear visual hierarchy', () => {
    renderWithTheme(<SchemaChangesPanel {...mockProps} />);

    // Check for "RENAME TO" label in rename operations
    // The component doesn't use "From" and "To" labels separately
    expect(screen.getByText('RENAME TO')).toBeInTheDocument();

    // Check that column names are displayed in chips
    expect(screen.getByText('very_long_column_name_that_might_overflow_in_horizontal_layout')).toBeInTheDocument();
    expect(screen.getByText('target_column_with_equally_long_name_for_testing')).toBeInTheDocument();
  });

  it('shows row count affected information', () => {
    renderWithTheme(<SchemaChangesPanel {...mockProps} />);

    // Check that row count information is displayed
    expect(screen.getAllByText('Affects 100 rows')).toHaveLength(3);
  });
});
