/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useEffect, useRef } from 'react';
import {
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Paper,
  ClickAwayListener,
  Popper,
  MenuList
} from '@mui/material';
import {
  Edit,
  Add,
  Delete,
  AddCircleOutline,
  RemoveCircleOutline
} from '@mui/icons-material';
import {
  ContextMenuProps,
  ColumnContextMenuAction,
  RowContextMenuAction,
  ContextMenuItem
} from '../../lib/types';

/**
 * Context menu component for column and row operations
 * Provides right-click functionality for manual data structure management
 */
export const ContextMenuComponent: React.FC<ContextMenuProps> = ({
  contextMenuState,
  onClose,
  onColumnOperation,
  onRowOperation
}) => {
  const menuRef = useRef<HTMLDivElement>(null);

  // Handle keyboard accessibility (Escape key to close)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && contextMenuState.isOpen) {
        onClose();
      }
    };

    if (contextMenuState.isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Focus the menu for keyboard navigation
      if (menuRef.current) {
        menuRef.current.focus();
      }
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [contextMenuState.isOpen, onClose]);

  // Generate menu items based on menu type
  const getMenuItems = (): ContextMenuItem[] => {
    if (contextMenuState.menuType === 'column') {
      return [
        {
          id: 'rename-column',
          label: 'Rename Column',
          icon: 'Edit',
          action: ColumnContextMenuAction.RENAME,
          disabled: false
        },
        {
          id: 'add-column-before',
          label: 'Add Column Before',
          icon: 'AddCircleOutline',
          action: ColumnContextMenuAction.ADD_BEFORE,
          disabled: false
        },
        {
          id: 'add-column-after',
          label: 'Add Column After',
          icon: 'AddCircleOutline',
          action: ColumnContextMenuAction.ADD_AFTER,
          disabled: false
        },
        {
          id: 'remove-column',
          label: 'Remove Column',
          icon: 'Delete',
          action: ColumnContextMenuAction.REMOVE,
          disabled: false,
          destructive: true
        }
      ];
    } else {
      return [
        {
          id: 'add-row-above',
          label: 'Add Row Above',
          icon: 'AddCircleOutline',
          action: RowContextMenuAction.ADD_ABOVE,
          disabled: false
        },
        {
          id: 'add-row-below',
          label: 'Add Row Below',
          icon: 'AddCircleOutline',
          action: RowContextMenuAction.ADD_BELOW,
          disabled: false
        },
        {
          id: 'remove-row',
          label: 'Remove Row',
          icon: 'Delete',
          action: RowContextMenuAction.REMOVE,
          disabled: false,
          destructive: true
        }
      ];
    }
  };

  // Get icon component by name
  const getIconComponent = (iconName?: string) => {
    switch (iconName) {
      case 'Edit':
        return <Edit fontSize="small" />;
      case 'Add':
        return <Add fontSize="small" />;
      case 'Delete':
        return <Delete fontSize="small" />;
      case 'AddCircleOutline':
        return <AddCircleOutline fontSize="small" />;
      case 'RemoveCircleOutline':
        return <RemoveCircleOutline fontSize="small" />;
      default:
        return null;
    }
  };

  // Handle menu item click
  const handleMenuItemClick = (menuItem: ContextMenuItem) => {
    if (contextMenuState.menuType === 'column' && onColumnOperation) {
      const columnOperation = {
        action: menuItem.action as ColumnContextMenuAction,
        columnIndex: contextMenuState.targetIndex,
        columnName: contextMenuState.targetColumnName || '',
        insertPosition: menuItem.action === ColumnContextMenuAction.ADD_BEFORE ? 'before' as const :
                      menuItem.action === ColumnContextMenuAction.ADD_AFTER ? 'after' as const : undefined
      };
      onColumnOperation(columnOperation);
    } else if (contextMenuState.menuType === 'row' && onRowOperation) {
      const rowOperation = {
        action: menuItem.action as RowContextMenuAction,
        rowIndex: contextMenuState.targetIndex,
        insertPosition: menuItem.action === RowContextMenuAction.ADD_ABOVE ? 'above' as const :
                       menuItem.action === RowContextMenuAction.ADD_BELOW ? 'below' as const : undefined
      };
      onRowOperation(rowOperation);
    }
    onClose();
  };

  if (!contextMenuState.isOpen) {
    return null;
  }

  const menuItems = getMenuItems();

  return (
    <Popper
      open={contextMenuState.isOpen}
      anchorEl={{
        getBoundingClientRect: () => ({
          top: contextMenuState.anchorY,
          left: contextMenuState.anchorX,
          right: contextMenuState.anchorX,
          bottom: contextMenuState.anchorY,
          width: 0,
          height: 0,
          x: contextMenuState.anchorX,
          y: contextMenuState.anchorY,
          toJSON: () => ({})
        })
      } as any}
      placement="bottom-start"
      style={{ zIndex: 1300 }}
    >
      <ClickAwayListener onClickAway={onClose}>
        <Paper
          ref={menuRef}
          elevation={8}
          sx={{
            minWidth: 200,
            maxWidth: 300,
            '& .MuiMenuItem-root': {
              fontSize: '0.875rem',
              minHeight: 40,
              '&:hover': {
                backgroundColor: 'action.hover'
              },
              '&.destructive': {
                color: 'error.main',
                '& .MuiListItemIcon-root': {
                  color: 'error.main'
                },
                '&:hover': {
                  backgroundColor: 'error.light',
                  color: 'error.contrastText'
                }
              }
            }
          }}
          tabIndex={-1}
          aria-label={`${contextMenuState.menuType} context menu`}
        >
          <MenuList
            dense
            role="menu"
            aria-label={`${contextMenuState.menuType} context menu`}
          >
            {menuItems.map((menuItem, index) => (
              <MenuItem
                key={menuItem.id}
                onClick={() => handleMenuItemClick(menuItem)}
                disabled={menuItem.disabled}
                className={menuItem.destructive ? 'destructive' : ''}
                role="menuitem"
                tabIndex={0}
              >
                {menuItem.icon && (
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {getIconComponent(menuItem.icon)}
                  </ListItemIcon>
                )}
                <ListItemText primary={menuItem.label} />
              </MenuItem>
            ))}
          </MenuList>
        </Paper>
      </ClickAwayListener>
    </Popper>
  );
};
