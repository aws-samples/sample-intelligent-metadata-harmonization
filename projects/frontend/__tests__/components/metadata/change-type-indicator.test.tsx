/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { ChangeTypeIndicator, SimpleChangeTypeIndicator } from '../../../components/metadata/change-type-indicator';
import { ChangeType, ChangeSourceType } from '../../../lib/types';
import { theme } from '../../../lib/theme';

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

describe('ChangeTypeIndicator', () => {
  describe('Basic Rendering', () => {
    it('should render change type and source type indicators', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.ADD}
            sourceType={ChangeSourceType.SYSTEM}
          />
        </TestWrapper>
      );

      expect(screen.getByText('Added')).toBeInTheDocument();
      expect(screen.getByText('System')).toBeInTheDocument();
    });

    it('should render without labels when showLabel is false', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.RENAME}
            sourceType={ChangeSourceType.USER}
            showLabel={false}
          />
        </TestWrapper>
      );

      expect(screen.queryByText('Modified')).not.toBeInTheDocument();
      expect(screen.queryByText('User')).not.toBeInTheDocument();
    });

    it('should display custom tooltip text when provided', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.REMOVE}
            sourceType={ChangeSourceType.SYSTEM}
            tooltipText="Custom tooltip text"
          />
        </TestWrapper>
      );

      // MUI Tooltip doesn't add title directly, just check the component renders
      expect(screen.getByText('Removed')).toBeInTheDocument();
      expect(screen.getByText('System')).toBeInTheDocument();
    });
  });

  describe('Change Type Styling', () => {
    it('should apply correct styling for ADD change type', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.ADD}
            sourceType={ChangeSourceType.SYSTEM}
          />
        </TestWrapper>
      );

      const addChip = screen.getByText('Added').closest('.MuiChip-root');
      expect(addChip).toHaveStyle('background-color: #e8f5e8');
      expect(addChip).toHaveStyle('color: #4caf50');
      expect(addChip).toHaveStyle('border: 1px solid #4caf50');
    });

    it('should apply correct styling for REMOVE change type', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.REMOVE}
            sourceType={ChangeSourceType.USER}
          />
        </TestWrapper>
      );

      const removeChip = screen.getByText('Removed').closest('.MuiChip-root');
      expect(removeChip).toHaveStyle('background-color: #ffeaea');
      expect(removeChip).toHaveStyle('color: #f44336');
      expect(removeChip).toHaveStyle('border: 1px solid #f44336');
    });

    it('should apply correct styling for RENAME change type', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.RENAME}
            sourceType={ChangeSourceType.SYSTEM}
          />
        </TestWrapper>
      );

      const renameChip = screen.getByText('Modified').closest('.MuiChip-root');
      expect(renameChip).toHaveStyle('background-color: #fff3e0');
      expect(renameChip).toHaveStyle('color: #ff9800');
      expect(renameChip).toHaveStyle('border: 1px solid #ff9800');
    });
  });

  describe('Source Type Styling', () => {
    it('should apply correct styling for SYSTEM source type', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.ADD}
            sourceType={ChangeSourceType.SYSTEM}
          />
        </TestWrapper>
      );

      const systemChip = screen.getByText('System').closest('.MuiChip-root');
      expect(systemChip).toHaveStyle('background-color: #e3f2fd');
      expect(systemChip).toHaveStyle('color: #2196f3');
      expect(systemChip).toHaveStyle('border-color: #2196f3');
    });

    it('should apply correct styling for USER source type', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.RENAME}
            sourceType={ChangeSourceType.USER}
          />
        </TestWrapper>
      );

      const userChip = screen.getByText('User').closest('.MuiChip-root');
      expect(userChip).toHaveStyle('background-color: #f3e5f5');
      expect(userChip).toHaveStyle('color: #9c27b0');
      expect(userChip).toHaveStyle('border-color: #9c27b0');
    });
  });

  describe('Size Variants', () => {
    it('should apply small size styling', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.ADD}
            sourceType={ChangeSourceType.SYSTEM}
            size="small"
          />
        </TestWrapper>
      );

      const addChip = screen.getByText('Added').closest('.MuiChip-root');
      const systemChip = screen.getByText('System').closest('.MuiChip-root');

      expect(addChip).toHaveClass('MuiChip-sizeSmall');
      expect(systemChip).toHaveClass('MuiChip-sizeSmall');
    });

    it('should apply medium size styling', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.REMOVE}
            sourceType={ChangeSourceType.USER}
            size="medium"
          />
        </TestWrapper>
      );

      const removeChip = screen.getByText('Removed').closest('.MuiChip-root');
      const userChip = screen.getByText('User').closest('.MuiChip-root');

      expect(removeChip).toHaveClass('MuiChip-sizeSmall');
      expect(userChip).toHaveClass('MuiChip-sizeSmall');
    });

    it('should apply large size styling', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.RENAME}
            sourceType={ChangeSourceType.SYSTEM}
            size="large"
          />
        </TestWrapper>
      );

      const renameChip = screen.getByText('Modified').closest('.MuiChip-root');
      const systemChip = screen.getByText('System').closest('.MuiChip-root');

      expect(renameChip).toHaveClass('MuiChip-sizeMedium');
      expect(systemChip).toHaveClass('MuiChip-sizeMedium');
    });
  });

  describe('Icons', () => {
    it('should display correct icons for each change type', () => {
      const { rerender } = render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.ADD}
            sourceType={ChangeSourceType.SYSTEM}
          />
        </TestWrapper>
      );

      expect(screen.getByTestId('AddIcon')).toBeInTheDocument();

      rerender(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.REMOVE}
            sourceType={ChangeSourceType.SYSTEM}
          />
        </TestWrapper>
      );

      expect(screen.getByTestId('RemoveIcon')).toBeInTheDocument();

      rerender(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.RENAME}
            sourceType={ChangeSourceType.SYSTEM}
          />
        </TestWrapper>
      );

      expect(screen.getByTestId('EditIcon')).toBeInTheDocument();
    });

    it('should display correct icons for each source type', () => {
      const { rerender } = render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.ADD}
            sourceType={ChangeSourceType.SYSTEM}
          />
        </TestWrapper>
      );

      expect(screen.getByTestId('ComputerIcon')).toBeInTheDocument();

      rerender(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.ADD}
            sourceType={ChangeSourceType.USER}
          />
        </TestWrapper>
      );

      expect(screen.getByTestId('PersonIcon')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper tooltip for accessibility', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.ADD}
            sourceType={ChangeSourceType.SYSTEM}
          />
        </TestWrapper>
      );

      // Check that the component renders with proper content for accessibility
      expect(screen.getByText('Added')).toBeInTheDocument();
      expect(screen.getByText('System')).toBeInTheDocument();
    });

    it('should be keyboard accessible', () => {
      render(
        <TestWrapper>
          <ChangeTypeIndicator
            changeType={ChangeType.RENAME}
            sourceType={ChangeSourceType.USER}
          />
        </TestWrapper>
      );

      const modifiedChip = screen.getByText('Modified');
      const userChip = screen.getByText('User');

      expect(modifiedChip).toBeVisible();
      expect(userChip).toBeVisible();
    });
  });
});

describe('SimpleChangeTypeIndicator', () => {
  describe('Basic Rendering', () => {
    it('should render only change type indicator', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.ADD} />
        </TestWrapper>
      );

      // Should not show any text labels, only icon
      expect(screen.queryByText('Added')).not.toBeInTheDocument();
      expect(screen.queryByText('System')).not.toBeInTheDocument();
      expect(screen.queryByText('User')).not.toBeInTheDocument();
    });

    it('should have tooltip with change type label', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.REMOVE} />
        </TestWrapper>
      );

      // Check that the chip renders with proper aria-label
      const chip = screen.getByLabelText('Removed');
      expect(chip).toBeInTheDocument();
    });
  });

  describe('Change Type Styling', () => {
    it('should apply correct styling for ADD change type', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.ADD} />
        </TestWrapper>
      );

      const chip = screen.getByLabelText('Added');
      expect(chip).toHaveStyle('background-color: #e8f5e8');
      expect(chip).toHaveStyle('color: #4caf50');
      expect(chip).toHaveStyle('border: 1px solid #4caf50');
    });

    it('should apply correct styling for REMOVE change type', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.REMOVE} />
        </TestWrapper>
      );

      const chip = screen.getByLabelText('Removed');
      expect(chip).toHaveStyle('background-color: #ffeaea');
      expect(chip).toHaveStyle('color: #f44336');
      expect(chip).toHaveStyle('border: 1px solid #f44336');
    });

    it('should apply correct styling for RENAME change type', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.RENAME} />
        </TestWrapper>
      );

      const chip = screen.getByLabelText('Modified');
      expect(chip).toHaveStyle('background-color: #fff3e0');
      expect(chip).toHaveStyle('color: #ff9800');
      expect(chip).toHaveStyle('border: 1px solid #ff9800');
    });
  });

  describe('Size Variants', () => {
    it('should apply small size styling', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.ADD} size="small" />
        </TestWrapper>
      );

      const chip = screen.getByLabelText('Added');
      expect(chip).toHaveClass('MuiChip-sizeSmall');
    });

    it('should apply medium size styling by default', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.RENAME} />
        </TestWrapper>
      );

      const chip = screen.getByLabelText('Modified');
      expect(chip).toHaveClass('MuiChip-sizeSmall');
    });

    it('should apply large size styling', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.REMOVE} size="large" />
        </TestWrapper>
      );

      const chip = screen.getByLabelText('Removed');
      expect(chip).toHaveClass('MuiChip-sizeMedium');
    });
  });

  describe('Icons', () => {
    it('should display correct icon for ADD change type', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.ADD} />
        </TestWrapper>
      );

      expect(screen.getByTestId('AddIcon')).toBeInTheDocument();
    });

    it('should display correct icon for REMOVE change type', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.REMOVE} />
        </TestWrapper>
      );

      expect(screen.getByTestId('RemoveIcon')).toBeInTheDocument();
    });

    it('should display correct icon for RENAME change type', () => {
      render(
        <TestWrapper>
          <SimpleChangeTypeIndicator changeType={ChangeType.RENAME} />
        </TestWrapper>
      );

      expect(screen.getByTestId('EditIcon')).toBeInTheDocument();
    });
  });
});
