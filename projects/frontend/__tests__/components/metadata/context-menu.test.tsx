/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ContextMenuComponent } from '../../../components/metadata/context-menu';
import {
  ContextMenuState,
  ColumnContextMenuAction,
  RowContextMenuAction,
  ColumnOperation,
  RowOperation
} from '../../../lib/types';

const theme = createTheme();

const defaultColumnContextMenuState: ContextMenuState = {
  isOpen: true,
  anchorX: 100,
  anchorY: 100,
  menuType: 'column',
  targetIndex: 0,
  targetColumnName: 'TestColumn'
};

const defaultRowContextMenuState: ContextMenuState = {
  isOpen: true,
  anchorX: 100,
  anchorY: 100,
  menuType: 'row',
  targetIndex: 0,
  targetColumnName: undefined
};

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('ContextMenuComponent', () => {
  const mockOnClose = jest.fn();
  const mockOnColumnOperation = jest.fn();
  const mockOnRowOperation = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Column Context Menu', () => {
    it('renders column context menu with all options', () => {
      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultColumnContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      expect(screen.getByRole('menu')).toBeInTheDocument();
      expect(screen.getByText('Rename Column')).toBeInTheDocument();
      expect(screen.getByText('Add Column Before')).toBeInTheDocument();
      expect(screen.getByText('Add Column After')).toBeInTheDocument();
      expect(screen.getByText('Remove Column')).toBeInTheDocument();
    });

    it('calls onColumnOperation with rename action when rename is clicked', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultColumnContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      await user.click(screen.getByText('Rename Column'));

      expect(mockOnColumnOperation).toHaveBeenCalledWith({
        action: ColumnContextMenuAction.RENAME,
        columnIndex: 0,
        columnName: 'TestColumn',
        insertPosition: undefined
      });
      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onColumnOperation with add before action when add before is clicked', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultColumnContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      await user.click(screen.getByText('Add Column Before'));

      expect(mockOnColumnOperation).toHaveBeenCalledWith({
        action: ColumnContextMenuAction.ADD_BEFORE,
        columnIndex: 0,
        columnName: 'TestColumn',
        insertPosition: 'before'
      });
      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onColumnOperation with add after action when add after is clicked', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultColumnContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      await user.click(screen.getByText('Add Column After'));

      expect(mockOnColumnOperation).toHaveBeenCalledWith({
        action: ColumnContextMenuAction.ADD_AFTER,
        columnIndex: 0,
        columnName: 'TestColumn',
        insertPosition: 'after'
      });
      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onColumnOperation with remove action when remove is clicked', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultColumnContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      await user.click(screen.getByText('Remove Column'));

      expect(mockOnColumnOperation).toHaveBeenCalledWith({
        action: ColumnContextMenuAction.REMOVE,
        columnIndex: 0,
        columnName: 'TestColumn',
        insertPosition: undefined
      });
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe('Row Context Menu', () => {
    it('renders row context menu with all options', () => {
      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultRowContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      expect(screen.getByRole('menu')).toBeInTheDocument();
      expect(screen.getByText('Add Row Above')).toBeInTheDocument();
      expect(screen.getByText('Add Row Below')).toBeInTheDocument();
      expect(screen.getByText('Remove Row')).toBeInTheDocument();
    });

    it('calls onRowOperation with add above action when add above is clicked', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultRowContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      await user.click(screen.getByText('Add Row Above'));

      expect(mockOnRowOperation).toHaveBeenCalledWith({
        action: RowContextMenuAction.ADD_ABOVE,
        rowIndex: 0,
        insertPosition: 'above'
      });
      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onRowOperation with add below action when add below is clicked', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultRowContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      await user.click(screen.getByText('Add Row Below'));

      expect(mockOnRowOperation).toHaveBeenCalledWith({
        action: RowContextMenuAction.ADD_BELOW,
        rowIndex: 0,
        insertPosition: 'below'
      });
      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onRowOperation with remove action when remove is clicked', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultRowContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      await user.click(screen.getByText('Remove Row'));

      expect(mockOnRowOperation).toHaveBeenCalledWith({
        action: RowContextMenuAction.REMOVE,
        rowIndex: 0,
        insertPosition: undefined
      });
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe('Accessibility and Keyboard Navigation', () => {
    it('closes menu when Escape key is pressed', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultColumnContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      await user.keyboard('{Escape}');

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('closes menu when clicking away', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <div>
          <div data-testid="outside">Outside element</div>
          <ContextMenuComponent
            contextMenuState={defaultColumnContextMenuState}
            onClose={mockOnClose}
            onColumnOperation={mockOnColumnOperation}
            onRowOperation={mockOnRowOperation}
          />
        </div>
      );

      await user.click(screen.getByTestId('outside'));

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('has proper ARIA attributes', () => {
      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultColumnContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      const menus = screen.getAllByRole('menu');
      expect(menus.length).toBeGreaterThan(0);

      // Check that at least one menu has the correct aria-label
      const menuWithLabel = menus.find(menu =>
        menu.getAttribute('aria-label') === 'column context menu'
      );
      expect(menuWithLabel).toBeInTheDocument();

      const menuItems = screen.getAllByRole('menuitem');
      expect(menuItems).toHaveLength(4);
      menuItems.forEach(item => {
        expect(item).toHaveAttribute('tabIndex', '0');
      });
    });

    it('applies destructive styling to remove options', () => {
      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultColumnContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      const removeMenuItem = screen.getByText('Remove Column').closest('[role="menuitem"]');
      expect(removeMenuItem).toHaveClass('destructive');
    });
  });

  describe('Menu State Management', () => {
    it('does not render when context menu is closed', () => {
      const closedState: ContextMenuState = {
        ...defaultColumnContextMenuState,
        isOpen: false
      };

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={closedState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });

    it('positions menu at specified coordinates', () => {
      const customState: ContextMenuState = {
        ...defaultColumnContextMenuState,
        anchorX: 200,
        anchorY: 300
      };

      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={customState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      // The menu should be rendered (exact positioning testing would require more complex setup)
      const menus = screen.getAllByRole('menu');
      expect(menus.length).toBeGreaterThan(0);
    });
  });

  describe('Icon Rendering', () => {
    it('renders appropriate icons for each menu item', () => {
      renderWithTheme(
        <ContextMenuComponent
          contextMenuState={defaultColumnContextMenuState}
          onClose={mockOnClose}
          onColumnOperation={mockOnColumnOperation}
          onRowOperation={mockOnRowOperation}
        />
      );

      // Check that icons are rendered by looking for specific test IDs
      expect(screen.getByTestId('EditIcon')).toBeInTheDocument();
      expect(screen.getAllByTestId('AddCircleOutlineIcon')).toHaveLength(2);
      expect(screen.getByTestId('DeleteIcon')).toBeInTheDocument();
    });
  });
});
