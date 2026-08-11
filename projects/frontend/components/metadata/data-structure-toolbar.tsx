/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import {
  Box,
  Toolbar,
  IconButton,
  Button,
  ButtonGroup,
  Tooltip,
  Divider,
  Typography,
  Chip
} from '@mui/material';
import {
  Add as AddIcon,
  Remove as RemoveIcon,
  Edit as EditIcon,
  ViewColumn as ViewColumnIcon,
  TableRows as TableRowsIcon,
  DragIndicator as DragIcon,
  Undo as UndoIcon,
  Redo as RedoIcon,
  Save as SaveIcon,
  FileUpload as ImportIcon,
  FileDownload as ExportIcon,
  Settings as SettingsIcon,
  SelectAll as SelectAllIcon,
  Analytics as StatsIcon
} from '@mui/icons-material';

export interface DataStructureToolbarProps {
  // Column operations
  onAddColumn: () => void;
  onRemoveColumn: () => void;
  onRenameColumn: () => void;

  // Row operations
  onAddRowAbove: () => void;
  onAddRowBelow: () => void;
  onRemoveRow: () => void;

  // Bulk operations
  onBulkAddColumns: () => void;
  onBulkRemoveColumns: () => void;
  onBulkRenameColumns: () => void;
  onBulkAddRows: () => void;
  onBulkRemoveRows: () => void;

  // Undo/Redo
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;

  // Selection and drag-drop
  onToggleSelectionMode: () => void;
  onToggleDragMode: () => void;
  isSelectionMode: boolean;
  isDragMode: boolean;

  // Import/Export
  onImportStructure: () => void;
  onExportStructure: () => void;

  // Templates and settings
  onOpenTemplates: () => void;
  onOpenSettings: () => void;
  onOpenStatistics: () => void;

  // Current state
  selectedColumns: number[];
  selectedRows: number[];
  totalColumns: number;
  totalRows: number;
  modifiedColumns: number[];
  modifiedRows: number[];
}

export const DataStructureToolbar: React.FC<DataStructureToolbarProps> = ({
  onAddColumn,
  onRemoveColumn,
  onRenameColumn,
  onAddRowAbove,
  onAddRowBelow,
  onRemoveRow,
  onBulkAddColumns,
  onBulkRemoveColumns,
  onBulkRenameColumns,
  onBulkAddRows,
  onBulkRemoveRows,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  onToggleSelectionMode,
  onToggleDragMode,
  isSelectionMode,
  isDragMode,
  onImportStructure,
  onExportStructure,
  onOpenTemplates,
  onOpenSettings,
  onOpenStatistics,
  selectedColumns,
  selectedRows,
  totalColumns,
  totalRows,
  modifiedColumns,
  modifiedRows
}) => {
  const hasColumnSelection = selectedColumns.length > 0;
  const hasRowSelection = selectedRows.length > 0;
  const hasMultipleColumnSelection = selectedColumns.length > 1;
  const hasMultipleRowSelection = selectedRows.length > 1;

  return (
    <Box sx={{
      borderBottom: 1,
      borderColor: 'divider',
      backgroundColor: 'background.paper',
      position: 'sticky',
      top: 0,
      zIndex: 1000,
      width: '100%'
    }}>
      <Toolbar variant="dense" sx={{ minHeight: 48, gap: 1 }}>
        {/* Column Operations */}
        <ButtonGroup size="small" variant="outlined">
          <Tooltip title="Add Column (Ctrl+Shift+C)">
            <IconButton onClick={onAddColumn} size="small">
              <ViewColumnIcon />
              <AddIcon sx={{ fontSize: 12, ml: -0.5, mt: -0.5 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title={hasColumnSelection ? "Rename Selected Column (F2)" : "Select a column to rename"}>
            <span>
              <IconButton
                onClick={onRenameColumn}
                size="small"
                disabled={!hasColumnSelection || hasMultipleColumnSelection}
              >
                <EditIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title={hasColumnSelection ? "Remove Selected Columns (Delete)" : "Select columns to remove"}>
            <span>
              <IconButton
                onClick={onRemoveColumn}
                size="small"
                disabled={!hasColumnSelection}
                color={hasColumnSelection ? "error" : "default"}
              >
                <RemoveIcon />
              </IconButton>
            </span>
          </Tooltip>
        </ButtonGroup>

        <Divider orientation="vertical" flexItem />

        {/* Row Operations */}
        <ButtonGroup size="small" variant="outlined">
          <Tooltip title="Add Row Above (Ctrl+Shift+R)">
            <IconButton onClick={onAddRowAbove} size="small">
              <TableRowsIcon />
              <AddIcon sx={{ fontSize: 12, ml: -0.5, mt: -0.5 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title="Add Row Below (Ctrl+Alt+R)">
            <IconButton onClick={onAddRowBelow} size="small">
              <TableRowsIcon />
              <AddIcon sx={{ fontSize: 12, ml: -0.5, mb: -0.5 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title={hasRowSelection ? "Remove Selected Rows (Shift+Delete)" : "Select rows to remove"}>
            <span>
              <IconButton
                onClick={onRemoveRow}
                size="small"
                disabled={!hasRowSelection}
                color={hasRowSelection ? "error" : "default"}
              >
                <RemoveIcon />
              </IconButton>
            </span>
          </Tooltip>
        </ButtonGroup>

        <Divider orientation="vertical" flexItem />

        {/* Bulk Operations */}
        {(hasMultipleColumnSelection || hasMultipleRowSelection) && (
          <>
            <ButtonGroup size="small" variant="contained" color="primary">
              {hasMultipleColumnSelection && (
                <>
                  <Tooltip title="Bulk Add Columns">
                    <Button onClick={onBulkAddColumns} startIcon={<AddIcon />}>
                      Add {selectedColumns.length} Cols
                    </Button>
                  </Tooltip>
                  <Tooltip title="Bulk Rename Columns">
                    <Button onClick={onBulkRenameColumns} startIcon={<EditIcon />}>
                      Rename
                    </Button>
                  </Tooltip>
                  <Tooltip title="Bulk Remove Columns">
                    <Button onClick={onBulkRemoveColumns} startIcon={<RemoveIcon />} color="error">
                      Remove
                    </Button>
                  </Tooltip>
                </>
              )}
              {hasMultipleRowSelection && (
                <>
                  <Tooltip title="Bulk Add Rows">
                    <Button onClick={onBulkAddRows} startIcon={<AddIcon />}>
                      Add {selectedRows.length} Rows
                    </Button>
                  </Tooltip>
                  <Tooltip title="Bulk Remove Rows">
                    <Button onClick={onBulkRemoveRows} startIcon={<RemoveIcon />} color="error">
                      Remove
                    </Button>
                  </Tooltip>
                </>
              )}
            </ButtonGroup>
            <Divider orientation="vertical" flexItem />
          </>
        )}

        {/* Undo/Redo */}
        <ButtonGroup size="small" variant="outlined">
          <Tooltip title="Undo (Ctrl+Z)">
            <span>
              <IconButton onClick={onUndo} size="small" disabled={!canUndo}>
                <UndoIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Redo (Ctrl+Y)">
            <span>
              <IconButton onClick={onRedo} size="small" disabled={!canRedo}>
                <RedoIcon />
              </IconButton>
            </span>
          </Tooltip>
        </ButtonGroup>

        <Divider orientation="vertical" flexItem />

        {/* Selection and Drag Mode */}
        <ButtonGroup size="small" variant="outlined">
          <Tooltip title="Toggle Selection Mode (Ctrl+A)">
            <IconButton
              onClick={onToggleSelectionMode}
              size="small"
              color={isSelectionMode ? "primary" : "default"}
            >
              <SelectAllIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Toggle Drag & Drop Mode">
            <IconButton
              onClick={onToggleDragMode}
              size="small"
              color={isDragMode ? "primary" : "default"}
            >
              <DragIcon />
            </IconButton>
          </Tooltip>
        </ButtonGroup>

        <Divider orientation="vertical" flexItem />

        {/* Import/Export */}
        <ButtonGroup size="small" variant="outlined">
          <Tooltip title="Import Structure">
            <IconButton onClick={onImportStructure} size="small">
              <ImportIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Export Structure">
            <IconButton onClick={onExportStructure} size="small">
              <ExportIcon />
            </IconButton>
          </Tooltip>
        </ButtonGroup>

        {/* Spacer */}
        <Box sx={{ flexGrow: 1 }} />

        {/* Status Information */}
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          {modifiedColumns.length > 0 && (
            <Chip
              label={`${modifiedColumns.length} cols modified`}
              size="small"
              color="warning"
              variant="outlined"
            />
          )}
          {modifiedRows.length > 0 && (
            <Chip
              label={`${modifiedRows.length} rows modified`}
              size="small"
              color="warning"
              variant="outlined"
            />
          )}
          <Typography variant="caption" color="text.secondary">
            {totalColumns} cols × {totalRows} rows
          </Typography>
        </Box>

        {/* Settings and Tools */}
        <ButtonGroup size="small" variant="outlined">
          <Tooltip title="Data Statistics">
            <IconButton onClick={onOpenStatistics} size="small">
              <StatsIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Templates">
            <IconButton onClick={onOpenTemplates} size="small">
              <SaveIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Settings">
            <IconButton onClick={onOpenSettings} size="small">
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </ButtonGroup>
      </Toolbar>
    </Box>
  );
};
