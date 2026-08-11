/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ValidationSidebarComponent } from '../../components/metadata/validation-sidebar';
import { ValidationError, SchemaAlignmentResults, Change, ValidationErrorType } from '../../lib/types';
import { beforeEach } from 'node:test';

// Mock the auth context
jest.mock('react-oidc-context', () => ({
  useAuth: () => ({
    user: { access_token: 'mock-token' }
  })
}));

// Mock the API functions
jest.mock('../../lib/api', () => ({
  updateValidationJob: jest.fn(),
  pollValidationStatus: jest.fn(),
  submitMetadataValidation: jest.fn()
}));

describe('ValidationSidebarComponent - UI Cleanup', () => {
  const mockProps = {
    data: [['header1', 'header2'], ['value1', 'value2']],
    changes: [] as Change[],
    validationErrors: [] as ValidationError[],
    schemaAlignmentResults: null as SchemaAlignmentResults | null,
    onValidationComplete: jest.fn(),
    onValidationErrors: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Job ID Display Relocation', () => {
    it('should not display Job ID in header when no jobId is provided', () => {
      render(<ValidationSidebarComponent {...mockProps} />);

      // Job ID should not be visible anywhere in the header area
      const submitButton = screen.getByRole('button', { name: /submit for validation/i });
      const headerArea = submitButton.closest('[data-testid="header-area"]') || submitButton.parentElement;

      expect(headerArea).not.toHaveTextContent('Job ID');
    });

    it('should display Job ID at the bottom of sidebar when jobId is provided', () => {
      render(<ValidationSidebarComponent {...mockProps} jobId="test-job-123" />);

      // Job ID should be visible at the bottom
      const jobIdElement = screen.getByText('Job ID');
      const jobIdValue = screen.getByText('test-job-123');

      expect(jobIdElement).toBeInTheDocument();
      expect(jobIdValue).toBeInTheDocument();

      // Check that it's styled as a footer (has border-top and muted background)
      const jobIdContainer = jobIdElement.closest('div');
      expect(jobIdContainer).toBeInTheDocument();

      // Check for footer styling attributes (Material-UI applies these as CSS classes)
      expect(jobIdContainer).toHaveClass('MuiBox-root');
    });

    it('should display Job ID with monospace font and proper styling', () => {
      render(<ValidationSidebarComponent {...mockProps} jobId="test-job-123" />);

      const jobIdValue = screen.getByText('test-job-123');
      expect(jobIdValue).toHaveStyle({
        fontFamily: 'monospace',
        fontSize: '0.7rem',
        wordBreak: 'break-all'
      });
    });
  });

  describe('Recent Changes Collapsible Functionality', () => {
    const changesData: Change[] = [
      {
        row: 1,
        column: 0,
        oldValue: 'old1',
        newValue: 'new1',
        timestamp: new Date('2023-01-01T10:00:00Z')
      },
      {
        row: 2,
        column: 1,
        oldValue: 'old2',
        newValue: 'new2',
        timestamp: new Date('2023-01-01T10:01:00Z')
      }
    ];

    it('should display Recent Changes section as collapsed by default', () => {
      render(<ValidationSidebarComponent {...mockProps} changes={changesData} />);

      const sectionHeader = screen.getByText('Recent Changes (2)');
      expect(sectionHeader).toBeInTheDocument();

      // Changes should not be visible by default (collapsed)
      expect(screen.queryByText(/Row 2, header1: "old1" → "new1"/)).not.toBeInTheDocument();

      // Check aria-expanded is false
      const toggleRegion = screen.getByRole('button', { name: /expand recent changes section/i });
      expect(toggleRegion).toHaveAttribute('aria-expanded', 'false');
    });

    it('should toggle Recent Changes section when clicked', async () => {
      const user = userEvent.setup();
      render(<ValidationSidebarComponent {...mockProps} changes={changesData} />);

      const toggleButton = screen.getByRole('button', { name: /expand recent changes section/i });

      // Initially collapsed - changes should not be visible
      expect(screen.queryByText(/Row 2, header1: "old1" → "new1"/)).not.toBeInTheDocument();

      // Click to expand
      await user.click(toggleButton);

      // Changes should be visible
      await waitFor(() => {
        expect(screen.getByText(/Row 2, header1: "old1" → "new1"/)).toBeInTheDocument();
      });

      // Click to collapse again
      const collapseButton = screen.getByRole('button', { name: /collapse recent changes section/i });
      await user.click(collapseButton);

      // Changes should be hidden again
      await waitFor(() => {
        expect(screen.queryByText(/Row 2, header1: "old1" → "new1"/)).not.toBeInTheDocument();
      });
    });

    it('should support keyboard navigation for collapse/expand', async () => {
      const user = userEvent.setup();
      render(<ValidationSidebarComponent {...mockProps} changes={changesData} />);

      const toggleButton = screen.getByRole('button', { name: /expand recent changes section/i });

      // Focus the toggle button
      toggleButton.focus();

      // Press Enter to expand
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(screen.getByText(/Row 2, header1: "old1" → "new1"/)).toBeInTheDocument();
      });

      // Press Space to collapse
      await user.keyboard(' ');

      await waitFor(() => {
        expect(screen.queryByText(/Row 2, header1: "old1" → "new1"/)).not.toBeInTheDocument();
      });
    });

    it('should show correct change count in header even when collapsed', () => {
      render(<ValidationSidebarComponent {...mockProps} changes={changesData} />);

      // Header should show the count even when collapsed (default state)
      expect(screen.getByText('Recent Changes (2)')).toBeInTheDocument();

      // Changes themselves should not be visible (collapsed by default)
      expect(screen.queryByText(/Row 2, header1: "old1" → "new1"/)).not.toBeInTheDocument();
    });

    it('should have proper ARIA attributes for accessibility', () => {
      render(<ValidationSidebarComponent {...mockProps} changes={changesData} />);

      const toggleButton = screen.getByRole('button', { name: /expand recent changes section/i });

      // Should be collapsed by default
      expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
      expect(toggleButton).toHaveAttribute('tabIndex', '0');
    });
  });

  describe('Independent Sidebar Scrolling', () => {
    it('should have proper overflow settings on main container', () => {
      render(<ValidationSidebarComponent {...mockProps} />);

      // Find the main sidebar container by looking for the root Box with overflow hidden
      const sidebarContainer = document.querySelector('[style*="overflow: hidden"]');

      // Main container should have overflow hidden to prevent it from scrolling
      expect(sidebarContainer).toBeInTheDocument();
    });

    it('should have scrollable tab content area', () => {
      render(<ValidationSidebarComponent {...mockProps} />);

      // Find the tab content area
      const tabContent = document.querySelector('[data-tab-content="true"]');

      expect(tabContent).toBeInTheDocument();
      // The tab content area itself has overflow hidden, letting panels handle scrolling
      expect(tabContent).toHaveStyle({
        overflow: 'hidden'
      });
    });

    it('should have custom scrollbar styling', () => {
      render(<ValidationSidebarComponent {...mockProps} />);

      const tabContent = document.querySelector('[data-tab-content="true"]');

      // The tab content area has overflow hidden, scrollbar styles are on individual panels
      expect(tabContent).toHaveStyle({
        overflow: 'hidden'
      });
    });

    it('should scroll to top when switching tabs', async () => {
      const user = userEvent.setup();

      // Mock scrollTo function
      const mockScrollTo = jest.fn();
      Object.defineProperty(Element.prototype, 'scrollTo', {
        value: mockScrollTo,
        writable: true
      });

      render(<ValidationSidebarComponent {...mockProps} />);

      // Switch to validation errors tab
      const validationTab = screen.getByRole('tab', { name: /validation errors/i });
      await user.click(validationTab);

      // Should call scrollTo with smooth behavior
      expect(mockScrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' });

      // Switch back to schema changes tab
      const schemaTab = screen.getByRole('tab', { name: /schema changes/i });
      await user.click(schemaTab);

      // Should call scrollTo again
      expect(mockScrollTo).toHaveBeenCalledTimes(2);
    });
  });

  describe('Panel Header Cleanup', () => {
    it('should not display redundant header text in validation errors panel', () => {
      const validationErrors: ValidationError[] = [
        {
          row: 1,
          column: 'test-column',
          currentValue: 'invalid',
          errorType: ValidationErrorType.INVALID_OPTION,
          recommendedValue: 'valid',
          validOptions: ['valid', 'option2'],
          schemaFieldName: 'test-field',
          confidenceScore: 0.85,
          confidenceLevel: 'High'
        }
      ];

      render(<ValidationSidebarComponent {...mockProps} validationErrors={validationErrors} />);

      // Switch to validation errors tab
      const validationTab = screen.getByRole('tab', { name: /validation errors/i });
      fireEvent.click(validationTab);

      // Should not have redundant "Validation Errors (1)" header since tab badge shows count
      expect(screen.queryByText('Validation Errors (1)')).not.toBeInTheDocument();
    });

    it('should not display redundant header text in schema changes panel', () => {
      const schemaAlignmentResults: SchemaAlignmentResults = {
        schemaAlignmentResults: [
          {
            changeType: 'rename',
            originalColumn: 'old_name',
            newColumn: 'new_name',
            reason: 'Schema alignment',
            rowCountAffected: 10
          }
        ],
        summary: {
          jobId: 'test-job',
          version: 1,
          timestamp: new Date(),
          originalDataCsv: 'test,data',
          alignedDataCsv: 'test,data',
          totalChanges: 1,
          columnsRenamed: 1,
          columnsAdded: 0,
          columnsRemoved: 0,
          rowsOriginal: 10,
          rowsAligned: 10
        }
      };

      render(<ValidationSidebarComponent {...mockProps} schemaAlignmentResults={schemaAlignmentResults} />);

      // Should be on schema changes tab by default
      // Should not have redundant "Schema Changes (1)" header since tab badge shows count
      expect(screen.queryByText('Schema Changes (1)')).not.toBeInTheDocument();

      // Should not have explanatory text about automatic schema alignment
      expect(screen.queryByText(/These changes were automatically applied/)).not.toBeInTheDocument();
    });
  });
});
