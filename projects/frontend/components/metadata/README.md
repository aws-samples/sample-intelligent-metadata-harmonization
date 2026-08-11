# Metadata Validation Components

This directory contains React components for the metadata validation workflow, built with Material UI and TypeScript.

## Components Overview

### FileUploadComponent ✅ IMPLEMENTED

**Location**: `file-upload.tsx`

A centered file upload interface that handles schema selection, CSV file validation, and parsing.

#### Features

- **Schema Selection**:
  - Dual dropdown interface for Core and Program schema selection
  - Automatic loading of available schemas from API on component mount
  - Initial schema ID validation against loaded schemas to ensure data integrity
  - Loading states with CircularProgress during schema fetching
  - Error handling for schema API failures with user-friendly messages
  - Validation requiring both schemas before file upload is enabled

- **File Validation**:
  - Checks for `.csv` file extension
  - Enforces 10MB file size limit
  - Validates file content is not empty
  - Requires schema selection before file processing

- **CSV Parsing**:
  - Client-side parsing using browser File API
  - Handles quoted fields and embedded commas correctly
  - Validates minimum data requirements (header + at least one data row)

- **User Experience**:
  - Material UI centered layout with Container, Grid, and Box components
  - Schema selection dropdowns with FormControl, InputLabel, and Select
  - Loading states with CircularProgress during schema loading and file processing
  - Error handling via Material UI Snackbar with Alert component
  - File input reset after processing
  - Accessible design with proper ARIA labels and keyboard navigation

- **Error Handling**:
  - Schema loading failures with specific error messages
  - Schema selection validation (both required)
  - Invalid file extension errors
  - File size limit exceeded errors
  - Empty file validation
  - CSV parsing errors
  - Minimum data validation (header + data rows)

#### Props

```typescript
interface FileUploadProps {
  onFileProcessed: (data: string[][], coreSchemaId: string, programSchemaId: string) => void;
  initialCoreSchemaId?: string;
  initialProgramSchemaId?: string;
  disabled?: boolean;
}
```

#### Usage

```typescript
import { FileUploadComponent } from './metadata/file-upload';

<FileUploadComponent
  onFileProcessed={(csvData, coreSchemaId, programSchemaId) => {
    // Handle parsed CSV data with selected schemas
    console.log('Parsed CSV:', csvData);
    console.log('Selected schemas:', { coreSchemaId, programSchemaId });
  }}
  initialCoreSchemaId="cyclospora_core_v1"
  initialProgramSchemaId="cyclospora_program_v1"
  disabled={false}
/>
```

#### Implementation Details

- Uses `useRef` for file input management and `useEffect` for schema loading
- Implements `getAvailableSchemasForUI` API call with comprehensive error handling
- Manages schema selection state with `SchemaSelectionState` interface
- Validates initial schema IDs against loaded schemas to prevent invalid selections
- Implements custom CSV parser with quote handling
- Provides comprehensive file and schema validation before processing
- Emits parsed data as 2D string array with selected schema IDs
- Handles all error scenarios gracefully with user feedback via Snackbar
- Supports initial schema values with validation and disabled state for controlled usage

### SpreadsheetEditorComponent ✅ IMPLEMENTED

**Location**: `spreadsheet-editor.tsx`

An interactive spreadsheet editor built on react-spreadsheet with validation error highlighting and change tracking.

#### Features

- **Interactive Spreadsheet**:
  - Built on react-spreadsheet library for Excel-like editing experience
  - Displays CSV data with proper header row and user-friendly 1-based row numbering for error display
  - Real-time cell editing with change detection and tracking

- **Advanced Scrolling & Layout**:
  - Horizontal and vertical scrolling for large datasets
  - Sticky column headers that remain visible during scrolling
  - Dynamic table sizing that expands beyond container width for many columns
  - Responsive design that prevents cramped layouts with minimum column widths

- **Validation Error Highlighting**:
  - Visual highlighting of cells with validation errors using red borders and background
  - Error mapping based on row and column coordinates
  - Supports multiple error types with consistent visual feedback

- **Performance & Optimization**:
  - Efficient error mapping using Map-based lookups
  - Debug element removal for clean production rendering
  - Optimized change detection and data transformation
  - Clean separation between component logic and DOM rendering
  - Automatic column sizing with content-based width calculation

- **Change Management**:
  - Tracks individual cell changes with timestamps
  - Provides detailed change objects with old/new values and coordinates
  - Supports disabled state for read-only viewing during processing

#### Props

```typescript
interface SpreadsheetEditorProps {
  data: string[][];                           // CSV data with header row
  validationErrors?: ValidationError[] | null; // Validation errors for highlighting
  disabled?: boolean;                         // Disable editing during processing
  onChange?: (newData: string[][], change: Change) => void; // Change callback
}

interface ValidationError {
  row: number;           // 1-based row index (includes header)
  column: string;        // Column name from header
  currentValue: string;  // Current cell value
  validOptions: string[] | null; // Valid options for this field (now includes required fields when applicable)
  recommendedValue: string | null; // Suggested correction
  errorType: string;     // Type of validation error
}

interface Change {
  row: number;      // Row index in full data array
  column: number;   // Column index
  oldValue: string; // Previous cell value
  newValue: string; // New cell value
  timestamp: Date;  // When change occurred
}
```

#### Usage

```typescript
import { SpreadsheetEditorComponent } from './metadata/spreadsheet-editor';

<SpreadsheetEditorComponent
  data={csvData}
  validationErrors={errors}
  disabled={isProcessing}
  onChange={(newData, change) => {
    console.log('Data changed:', change);
    setCsvData(newData);
  }}
/>
```

#### Implementation Details

- **Error Mapping**: Efficient Map-based lookup for validation error highlighting
- **Change Detection**: Compares old vs new data to generate precise change objects
- **Performance Optimized**: Removed debug elements and unused imports for production efficiency
- **Accessibility**: Proper ARIA labels and keyboard navigation support
- **Advanced Scrolling**:
  - Horizontal and vertical scrolling with smooth behavior
  - Sticky headers with proper z-index layering
  - Dynamic table sizing (`max-content` width with `100%` minimum)
  - Content-aware column sizing (120px minimum, 300px maximum)
  - Text overflow handling with ellipsis for long content
- **Responsive Design**:
  - Adapts to container size with proper scrolling
  - Prevents text wrapping in cells for consistent layout
  - Custom scrollbar styling for better visibility

### ColumnRenameDialog ✅ IMPLEMENTED

**Location**: `column-rename-dialog.tsx`

A comprehensive dialog component for renaming columns with validation, user feedback, and accessibility features.

#### Features

- **Input Validation**:
  - Real-time validation for empty names, duplicates, and invalid characters
  - Prevents column names with commas, line breaks, or other invalid characters
  - Excludes current column from duplicate validation to allow case changes
  - Comprehensive error messages with specific guidance

- **User Experience**:
  - Auto-focus and text selection on dialog open for easy replacement
  - Loading states during rename operations with disabled interactions
  - Visual feedback through alerts for valid changes
  - Keyboard shortcuts (Enter to confirm, Escape to cancel)
  - Close button with proper disabled state during loading

- **Accessibility**:
  - Full keyboard navigation support
  - ARIA labels and descriptions for screen readers
  - Proper focus management and tab order
  - Semantic HTML structure with dialog roles

- **Error Prevention**:
  - Validates against existing column names to prevent duplicates
  - Checks for empty or whitespace-only names
  - Character restrictions for CSV compatibility
  - Only proceeds with rename if name actually changed

#### Props

```typescript
interface ColumnRenameDialogProps {
  open: boolean;                        // Whether the dialog is open
  currentColumnName: string;            // Current column name to rename
  columnIndex: number;                  // Index of the column being renamed
  existingColumnNames: string[];        // List of all existing column names for validation
  loading?: boolean;                    // Whether the rename operation is in progress
  onConfirm: (newColumnName: string) => void;  // Callback when rename is confirmed
  onCancel: () => void;                 // Callback when dialog is cancelled
}
```

#### Usage

```typescript
import { ColumnRenameDialog } from './metadata/column-rename-dialog';

<ColumnRenameDialog
  open={isRenameDialogOpen}
  currentColumnName="old_column_name"
  columnIndex={2}
  existingColumnNames={['col1', 'col2', 'old_column_name', 'col4']}
  loading={isRenaming}
  onConfirm={(newName) => {
    console.log('Renaming column to:', newName);
    performColumnRename(newName);
  }}
  onCancel={() => {
    console.log('Rename cancelled');
    setIsRenameDialogOpen(false);
  }}
/>
```

#### Implementation Details

- **State Management**: Uses local state for input value and validation errors
- **Validation Logic**: Comprehensive validation with real-time feedback
- **Focus Management**: Auto-focuses input field with text selection on open
- **Error Handling**: Graceful handling of validation errors with user-friendly messages
- **Performance**: Efficient validation with minimal re-renders
- **Material UI Integration**: Consistent styling with application theme
- **Test Environment Compatibility**: Handles test environments where select() may not be available

### RemoveColumnDialog ✅ IMPLEMENTED

**Location**: `remove-column-dialog.tsx`

A comprehensive confirmation dialog for safely removing columns with data loss warnings and impact preview.

#### Features

- **Safety and Validation**:
  - Clear warning about permanent data loss with error-styled alerts
  - Requires explicit user confirmation before removal
  - Column index validation to prevent invalid operations
  - Comprehensive error handling with user-friendly messages

- **Data Preview and Analysis**:
  - Shows column information (name, position, total rows)
  - Displays first 5 non-empty values from the column in table format
  - Row statistics showing data vs empty row counts
  - Impact analysis detailing consequences of removal

- **User Experience**:
  - Material UI chips showing column statistics
  - Responsive design that works across screen sizes
  - Loading states with spinner during removal processing
  - Clear visual hierarchy with warning colors for destructive actions

- **Accessibility**:
  - Full ARIA compliance with proper labels and descriptions
  - Semantic HTML structure with dialog roles
  - Screen reader compatible with descriptive content
  - Keyboard navigation support

#### Props

```typescript
interface RemoveColumnDialogProps {
  open: boolean;                        // Whether the dialog is open
  columnIndex: number;                  // Column index to remove
  columnName: string;                   // Current column name
  columnData?: string[];                // Sample data from the column
  totalRows?: number;                   // Total number of rows affected
  loading?: boolean;                    // Whether operation is processing
  onConfirm: () => void;                // Callback when user confirms removal
  onCancel: () => void;                 // Callback when user cancels removal
}
```

#### Usage

```typescript
import { RemoveColumnDialog } from './metadata/remove-column-dialog';

<RemoveColumnDialog
  open={isRemoveDialogOpen}
  columnIndex={2}
  columnName="column_to_remove"
  columnData={['value1', 'value2', '', 'value4']}
  totalRows={100}
  loading={isRemoving}
  onConfirm={() => {
    console.log('Removing column');
    performColumnRemoval();
  }}
  onCancel={() => {
    console.log('Removal cancelled');
    setIsRemoveDialogOpen(false);
  }}
/>
```

#### Implementation Details

- **Data Processing**: Filters and displays non-empty values for preview
- **Statistics Calculation**: Computes affected vs empty row counts
- **Visual Design**: Uses Material UI Table for data preview with proper styling
- **Warning System**: Multiple levels of warnings with clear impact descriptions
- **Performance**: Efficient data processing with preview limitations (first 5 values)
- **Material UI Integration**: Consistent styling with error theme colors
- **Responsive Layout**: Adapts to different screen sizes with proper spacing

### DataStructureToolbar ✅ IMPLEMENTED

**Location**: `data-structure-toolbar.tsx`

A comprehensive toolbar component providing quick access to all data structure management operations with intelligent state-aware controls and keyboard shortcuts.

#### Features

- **Column Operations**:
  - Add Column button with keyboard shortcut (Ctrl+Shift+C)
  - Rename Column button (F2) - enabled only when single column selected
  - Remove Column button (Delete) - enabled when columns selected, error color when active
  - Context-aware tooltips showing keyboard shortcuts and selection requirements

- **Row Operations**:
  - Add Row Above button (Ctrl+Shift+R) with visual icon overlay
  - Add Row Below button (Ctrl+Alt+R) with positioned icon indicator
  - Remove Row button (Shift+Delete) - enabled when rows selected with error styling

- **Bulk Operations**:
  - Dynamic bulk operation buttons that appear when multiple items selected
  - Bulk Add Columns/Rows with selection count display
  - Bulk Rename functionality for multiple columns
  - Bulk Remove operations with error color styling for destructive actions
  - Smart button grouping with contained variant for prominence

- **Undo/Redo System**:
  - Undo button (Ctrl+Z) with disabled state management
  - Redo button (Ctrl+Y) with proper state tracking
  - Visual feedback for available operations

- **Selection and Interaction Modes**:
  - Toggle Selection Mode (Ctrl+A) with active state coloring
  - Toggle Drag & Drop Mode with visual feedback
  - Mode indicators using primary color for active states

- **Import/Export Operations**:
  - Import Structure button for loading external configurations
  - Export Structure button for saving current layout
  - Consistent icon usage for file operations

- **Status Information Display**:
  - Real-time modification count chips with warning colors
  - Dataset dimensions display (columns × rows)
  - Visual indicators for modified columns and rows
  - Responsive status layout with proper spacing

- **Settings and Tools**:
  - Data Statistics button for opening analytics panel
  - Templates button for structure template management
  - Settings button for configuration options
  - Organized button groups with consistent styling

#### Props

```typescript
interface DataStructureToolbarProps {
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
```

#### Usage

```typescript
import { DataStructureToolbar } from './metadata/data-structure-toolbar';

<DataStructureToolbar
  // Column operations
  onAddColumn={() => console.log('Add column')}
  onRemoveColumn={() => console.log('Remove selected columns')}
  onRenameColumn={() => console.log('Rename selected column')}

  // Row operations
  onAddRowAbove={() => console.log('Add row above')}
  onAddRowBelow={() => console.log('Add row below')}
  onRemoveRow={() => console.log('Remove selected rows')}

  // Bulk operations
  onBulkAddColumns={() => console.log('Bulk add columns')}
  onBulkRemoveColumns={() => console.log('Bulk remove columns')}
  onBulkRenameColumns={() => console.log('Bulk rename columns')}
  onBulkAddRows={() => console.log('Bulk add rows')}
  onBulkRemoveRows={() => console.log('Bulk remove rows')}

  // Undo/Redo
  onUndo={() => console.log('Undo last action')}
  onRedo={() => console.log('Redo last action')}
  canUndo={undoStack.length > 0}
  canRedo={redoStack.length > 0}

  // Selection modes
  onToggleSelectionMode={() => setSelectionMode(!selectionMode)}
  onToggleDragMode={() => setDragMode(!dragMode)}
  isSelectionMode={selectionMode}
  isDragMode={dragMode}

  // Import/Export
  onImportStructure={() => console.log('Import structure')}
  onExportStructure={() => console.log('Export structure')}

  // Tools
  onOpenTemplates={() => setTemplateDialogOpen(true)}
  onOpenSettings={() => setSettingsDialogOpen(true)}
  onOpenStatistics={() => setStatsDialogOpen(true)}

  // Current state
  selectedColumns={[1, 3, 5]}
  selectedRows={[2, 4]}
  totalColumns={10}
  totalRows={100}
  modifiedColumns={[1, 5]}
  modifiedRows={[2]}
/>
```

#### Implementation Details

- **Sticky Positioning**: Uses `position: sticky` with `top: 0` and high z-index for always-visible toolbar
- **Smart State Management**: Buttons automatically enable/disable based on selection state
- **Visual Feedback**: Color-coded buttons (error for destructive operations, primary for active modes)
- **Responsive Layout**: Uses Material UI Toolbar with proper spacing and button groups
- **Keyboard Accessibility**: Full keyboard navigation with comprehensive tooltip shortcuts
- **Performance**: Efficient state calculations with minimal re-renders
- **Material UI Integration**: Consistent styling with application theme and proper component composition
- **Icon Overlays**: Creative icon positioning for row operation visual indicators
- **Bulk Operation Logic**: Dynamic bulk controls that appear only when multiple items selected

### ValidationSidebarComponent ✅ IMPLEMENTED

**Location**: `validation-sidebar.tsx`

A tabbed sidebar component for validation controls, job tracking, error management, and schema alignment change management. The component takes full width of its container and is designed to be placed within a layout container that controls its overall dimensions.

#### Features

- **Job ID Display**:
  - Shows current job ID in a monospace font with grey background
  - Conditionally displayed only when a job ID is available
  - Styled with Material UI Typography and Box components
  - Word-break handling for long job IDs to prevent layout issues

- **Submit Controls**:
  - Submit button for initial validation or resubmission
  - Dynamic button text: "Submit for Validation" vs "Resubmit for Validation"
  - Loading states with CircularProgress during processing
  - Icon changes based on context (Send for new, Refresh for resubmit)

- **Job Polling**:
  - Real-time status updates with enhanced progress tracking
  - Automatic polling for job completion
  - Comprehensive error handling and timeout management
  - Status-specific progress indicators and messages
  - Improved server failure handling with user-friendly error messages
  - Enhanced error detection for processor graph execution failures and validation result issues

- **Change Management**:
  - Displays list of recent modifications
  - Tracks individual cell changes with timestamps
  - Visual feedback for user interactions

- **Tabbed Interface**:
  - Material UI Tabs with badge counts for errors and schema changes
  - "Validation Errors" tab with error icon and count badge
  - "Schema Changes" tab with transform icon and count badge
  - Full-width tab layout with proper styling and accessibility

- **Validation Errors Tab**:
  - Integration with ValidationErrorsPanel component
  - Scrollable list of validation issues with accept/dismiss actions
  - Bulk operation support for applying multiple similar changes
  - Loading states during validation processing
  - Current view context for error positioning

- **Schema Changes Tab**:
  - Integration with SchemaChangesPanel component with optimized flex layout
  - Review and manually apply schema alignment changes with scrollable content
  - Accept/revert functionality for individual changes with proper state management
  - Bulk operations for accepting or reverting multiple changes with confirmation dialogs
  - Transformation summary display with change counts and visual indicators

#### Props

```typescript
interface ValidationSidebarProps {
  data: string[][];                    // CSV data for validation
  changes: Change[];                   // Recent modifications
  validationErrors?: ValidationError[] | null; // Current validation errors
  schemaAlignmentResults?: SchemaAlignmentResults | null; // Schema alignment results with detailed changes
  currentView?: DataViewType;          // Current data view context (original or aligned)
  isSubmitting?: boolean;              // Loading state
  jobId?: string;                      // Current job ID for display and tracking
  coreSchemaId?: string;              // Core schema identifier
  programSchemaId?: string;           // Program schema identifier
  onValidationComplete: (jobId?: string) => void;
  onValidationErrors: (errors: ValidationError[], jobId?: string) => void;
  onApplyChange?: (change: ValidationError) => void;        // Apply single validation error correction
  onApplyAllChanges?: (columnChanges: ValidationError[]) => void; // Apply multiple validation error corrections
  onDisableSpreadsheet?: (disabled: boolean) => void;
  onAcceptSchemaChange?: (changeId: string) => void;       // Accept a schema alignment change
  onRevertSchemaChange?: (changeId: string) => void;       // Revert a schema alignment change
  children?: React.ReactNode;
}
```

#### Usage

```typescript
import { ValidationSidebarComponent } from './metadata/validation-sidebar';

<ValidationSidebarComponent
  data={csvData}
  changes={recentChanges}
  validationErrors={errors}
  schemaAlignmentResults={schemaAlignmentResults}
  currentView={DataViewType.ORIGINAL}
  isSubmitting={isProcessing}
  jobId={currentJobId}
  coreSchemaId="cyclospora_core_v1"
  programSchemaId="cyclospora_program_v1"
  onValidationComplete={(jobId) => {
    console.log('Validation completed for job:', jobId);
  }}
  onValidationErrors={(errors, jobId) => {
    console.log('Validation errors for job:', jobId, errors);
  }}
  onApplyChange={(error) => {
    console.log('Applying single validation error correction:', error);
    // Apply the recommended value to the spreadsheet
  }}
  onApplyAllChanges={(errors) => {
    console.log('Applying multiple validation error corrections:', errors);
    // Apply all recommended values to the spreadsheet
  }}
  onAcceptSchemaChange={(changeId) => {
    console.log('Accepting schema alignment change:', changeId);
    // Mark the schema change as accepted
  }}
  onRevertSchemaChange={(changeId) => {
    console.log('Reverting schema alignment change:', changeId);
    // Revert the schema alignment change
  }}
/>
```

#### Implementation Details

- **Job ID Management**: Uses `useState` to track current job ID with `useEffect` for prop updates
- **Dynamic UI**: Adjusts padding and button text based on job ID presence
- **Monospace Display**: Job ID shown in monospace font for better readability
- **Responsive Layout**: Adapts spacing when job ID is displayed vs hidden
- **Error Handling**: Comprehensive error management with Snackbar notifications and improved server failure messaging
- **State Management**: Tracks polling status, validation progress, error states, and active tab selection
- **Debug Support**: Console logging for server failures to aid in troubleshooting
- **Tabbed Interface**: Uses Material UI Tabs with proper state management and badge integration
- **Component Integration**: Orchestrates ValidationErrorsPanel and SchemaChangesPanel components
- **Callback Management**: Passes appropriate callbacks to child components for error correction and schema change management

### ValidationErrorsPanel ✅ IMPLEMENTED

**Location**: `validation-errors-panel.tsx`

A dedicated panel component for displaying validation errors in a structured format with options for accepting corrections and bulk operations. This component extracts the existing validation error display functionality from the ValidationSidebarComponent to support the new tabbed interface.

#### Features

- **Enhanced Error Display**:
  - Individual error cards with clear location information (row and column)
  - Current value and recommended value display with color-coded styling
  - Smart conditional display logic for recommendations vs manual editing guidance
  - Error count display in header with current view context

- **Improved User Guidance**:
  - Clear "Accept Recommendation" button text for better action clarity
  - Contextual messaging when no automatic recommendation is available
  - Manual editing guidance with valid options display and instructions
  - Visual hierarchy using success colors for recommendations and warning colors for manual cases

- **Error Correction Actions**:
  - "Accept Recommendation" button for applying individual error corrections (improved from "Accept")
  - Dismiss button for hiding individual error cards
  - Bulk "Accept All Recommendations" button for applying multiple corrections
  - Smart filtering to show only errors with recommended values for bulk operations

- **State Management**:
  - Loading state display during validation processing
  - Empty state with success message when no errors exist
  - View context awareness for error positioning (original vs aligned data)
  - Flexible content rendering through children prop for custom error cards

- **Layout & UX**:
  - Full height flex container with proper content distribution
  - Fixed header section with error count and bulk actions
  - Scrollable content area for error list with overflow handling
  - Footer summary showing correction statistics

#### Props

```typescript
interface ValidationErrorsPanelProps {
  errors: ValidationError[];                    // Array of validation errors to display
  currentView: DataViewType;                    // Current data view context for error positioning
  isLoading?: boolean;                          // Whether the panel is in a loading/processing state
  onAcceptError?: (error: ValidationError) => void;        // Callback when user accepts/applies a single error correction
  onAcceptAllErrors?: (errors: ValidationError[]) => void; // Callback when user accepts/applies all error corrections
  onDismissError?: (error: ValidationError) => void;       // Callback when user dismisses a single error
  children?: React.ReactNode;                   // Custom error card components to render
}
```

#### Usage

```typescript
import { ValidationErrorsPanel } from './metadata/validation-errors-panel';

<ValidationErrorsPanel
  errors={validationErrors}
  currentView={DataViewType.ORIGINAL}
  isLoading={false}
  onAcceptError={(error) => {
    console.log('Applying single error correction:', error);
    // Apply the recommended value to the spreadsheet
  }}
  onAcceptAllErrors={(errors) => {
    console.log('Applying multiple error corrections:', errors);
    // Apply all recommended values to the spreadsheet
  }}
  onDismissError={(error) => {
    console.log('Dismissing error:', error);
    // Hide the error card from display
  }}
>
  {/* Optional: Custom error card components */}
  {validationErrors.map(error => (
    <ErrorCardComponent
      key={`${error.row}-${error.column}`}
      error={error}
      onAccept={handleAcceptError}
      onDismiss={handleDismissError}
    />
  ))}
</ValidationErrorsPanel>
```

#### Implementation Details

- **Enhanced Conditional Logic**: Uses ternary operators for better handling of recommendation vs manual editing scenarios
- **Improved User Experience**: Clear action labels and contextual messaging based on error state
- **Smart Display Logic**: Shows appropriate content based on whether automatic recommendations are available
- **Manual Editing Support**: Provides clear instructions for spreadsheet editing when no recommendations exist
- **Flexible Rendering**: Supports both default error display and custom error cards through children prop
- **Bulk Operations**: Filters errors with recommendations for bulk accept functionality
- **State Handling**: Comprehensive loading, empty, and error states with appropriate messaging
- **View Context**: Displays current view context (original vs post-schema alignment) for error positioning
- **Accessibility**: Full keyboard navigation support and screen reader compatibility
- **Material UI Integration**: Consistent styling with application theme and proper component composition
- **Backward Compatibility**: Maintains compatibility with existing ValidationSidebarComponent interface

### SchemaChangesPanel ✅ IMPLEMENTED

**Location**: `schema-changes-panel.tsx`

A comprehensive panel component for displaying and managing schema alignment changes with proper flex layout and scrollable content.

#### Features

- **Flex Layout Design**:
  - Full height flex container (`height: '100%'`) with column direction
  - Fixed header section (`flexShrink: 0`) that doesn't compress during layout
  - Scrollable content area (`flexGrow: 1, overflow: 'auto'`) for change list
  - Proper space distribution for optimal user experience

- **Change Display & Management**:
  - Individual change cards with Material UI Card components and proper spacing
  - Color-coded change type badges (info for renames, success for additions, warning for removals)
  - Before/after column name display for rename operations with arrow indicators
  - Status indicators showing "Accepted", "Required by Schema", or action buttons
  - Accept/Revert buttons for individual changes with proper disabled states

- **Enhanced Bulk Operations with Shared Utilities**:
  - **Parent-Managed Callbacks**: `onApplyAllChanges` and `onRevertAllChanges` for coordinated bulk operations
  - **State Synchronization**: `appliedChangeIds` prop for parent-managed applied changes tracking
  - **Flexible Change Identification**: `getChangeId` callback for consistent change ID generation across components
  - **Shared Execution Functions**: Uses `executeBulkTransformations()` and `revertBulkTransformations()` for consistent behavior
  - **Fallback Implementation**: Local bulk operations when parent callbacks not provided for backward compatibility
  - **Smart Operation Sequencing**: Optimal change ordering (renames → additions → removals) with column state tracking using `updateColumnsAfterChange()`
  - **Comprehensive Error Handling**: Individual change failures don't stop bulk operations, with detailed `TransformationError` tracking and progress reporting
  - **Progress Tracking**: Real-time progress updates with error details using enhanced `ProgressTracker` interface
  - **Confirmation Dialogs**: Automatic detection of destructive changes with user confirmation for bulk operations

- **User Experience**:
  - Empty state display when no changes exist with helpful messaging
  - Comprehensive change descriptions with clear language
  - Tooltips for additional context and help information
  - Summary statistics showing accepted vs total changes and revertable counts

#### Props

```typescript
interface SchemaChangesPanelProps {
  changes: SchemaAlignmentChangeDetail[];     // Array of schema alignment changes to display
  // currentView removed - no longer using toggle functionality
  onApplyColumnRename?: (originalColumn: string, newColumn: string) => void;  // Apply column rename
  onApplyColumnAddition?: (newColumn: string) => void;                        // Apply column addition
  onApplyColumnRemoval?: (columnName: string) => void;                        // Apply column removal
  onAcceptChange: (changeId: string) => void;                                 // Legacy callback for accepting changes
  onRevertChange: (changeId: string) => void;                                 // Legacy callback for reverting changes
  onApplyAllChanges?: () => void;                                             // Bulk apply all changes operation
  onRevertAllChanges?: () => void;                                            // Bulk revert all changes operation
  appliedChangeIds?: Set<string>;                                             // Set of applied change IDs from parent
  getChangeId?: (change: SchemaAlignmentChangeDetail, index: number) => string; // Generate change ID for tracking
}

interface SchemaAlignmentChangeDetail {
  changeType: string;                         // Type of change: 'add', 'remove', 'rename'
  originalColumn?: string;                    // Original column name (for rename/remove operations)
  newColumn?: string;                         // New column name (for rename/add operations)
  reason?: string;                            // Reason for the change
  rowCountAffected?: number;                  // Number of rows affected by this change
}
```

#### Usage

```typescript
import { SchemaChangesPanel } from './metadata/schema-changes-panel';

<SchemaChangesPanel
  changes={schemaAlignmentResults?.schemaAlignmentResults || []}
  // Individual transformation callbacks
  onApplyColumnRename={(originalColumn, newColumn) => {
    console.log('Applying column rename:', originalColumn, '->', newColumn);
    applyColumnRename(originalColumn, newColumn);
  }}
  onApplyColumnAddition={(newColumn) => {
    console.log('Applying column addition:', newColumn);
    applyColumnAddition(newColumn);
  }}
  onApplyColumnRemoval={(columnName) => {
    console.log('Applying column removal:', columnName);
    applyColumnRemoval(columnName);
  }}
  // Bulk operation callbacks (preferred)
  onApplyAllChanges={() => {
    console.log('Applying all schema changes');
    applyAllSchemaChanges();
  }}
  onRevertAllChanges={() => {
    console.log('Reverting all schema changes');
    revertAllSchemaChanges();
  }}
  // State synchronization
  appliedChangeIds={appliedSchemaChangeIds}
  getChangeId={(change, index) => `${change.changeType}-${change.originalColumn || change.newColumn}-${index}`}
  // Legacy callbacks for backward compatibility
  onAcceptChange={(changeId) => {
    console.log('Accepting change:', changeId);
    // Mark the change as accepted
  }}
  onRevertChange={(changeId) => {
    console.log('Reverting change:', changeId);
    // Revert the schema alignment change
  }}
/>
```

#### Implementation Details

- **Layout Architecture**: Uses CSS Flexbox with full height container and proper content distribution
- **Scrolling Behavior**: Implements `overflow: 'auto'` on content area for smooth scrolling with large change sets
- **State Management**: Manages confirmation dialog state for bulk operations with proper cleanup
- **Performance**: Efficient filtering and rendering of changes with minimal re-renders
- **Accessibility**: Full ARIA support, keyboard navigation, and screen reader compatibility
- **Material UI Integration**: Consistent styling with application theme and proper component composition

### ErrorCardComponent ✅ IMPLEMENTED

**Location**: `error-card.tsx`

Individual error cards that display validation issues with action buttons for correction.

#### Features

- **Theme Compliance**:
  - Uses primary blue color scheme (`primary.main`, `primary.light`, `primary.dark`) throughout
  - Consistent with overall application theme and application branding
  - Suggested value text uses primary theme colors instead of success colors
  - Proper contrast ratios for accessibility compliance
  - Enhanced hover effects with `primary.dark` for visual feedback

- **Error Display**:
  - Shows current value, recommended value, and location information
  - **Custom Error Messages**: Displays schema-defined custom error messages when available for more specific, user-friendly validation feedback
  - **Schema Field Context**: Shows schema field name when different from column name after transformations
  - Clear error type indication with appropriate styling
  - Location chip with primary theme colors for consistency
  - **Fallback Behavior**: Gracefully handles cases where custom error messages are not available

- **Action Buttons**:
  - Accept button for applying individual changes
  - Accept All button for bulk operations on similar errors
  - Dismiss button with X icon for hiding error cards
  - Proper disabled states and accessibility support

#### Props

```typescript
interface ErrorCardProps {
  error: ValidationError;
  onAccept: (error: ValidationError) => void;
  onAcceptAll: (errors: ValidationError[]) => void;
  onDismiss: (error: ValidationError) => void;
}
```

#### Usage

```typescript
import { ErrorCardComponent } from './metadata/error-card';

<ErrorCardComponent
  error={validationError}
  onAccept={(error) => handleSingleChange(error)}
  onAcceptAll={(errors) => handleBulkChanges(errors)}
  onDismiss={(error) => hideErrorCard(error)}
/>
```

#### Implementation Details

- **Theme Integration**: Uses Material UI primary theme colors consistently for application branding
- **Color Consistency**: All text elements use primary color scheme (main/dark) for unified appearance
- **Accessibility**: Proper ARIA labels, keyboard navigation, and contrast ratios
- **Visual Hierarchy**: Clear distinction between error information and action buttons
- **Responsive Design**: Adapts to different screen sizes with proper spacing

### SchemaChangesListComponent ✅ IMPLEMENTED

**Location**: `schema-changes-list.tsx`

A comprehensive component for displaying and managing schema alignment changes with advanced filtering, search capabilities, bulk operations, and confirmation dialogs.

#### Features

- **Advanced Filtering & Search**:
  - Real-time search across column names, change types, and reasons
  - Status filtering (all, pending, applied, reverted) with visual indicators
  - Change type filtering (all, rename, add, remove) with color-coded chips
  - Collapsible filter panel with organized filter categories
  - Statistics display showing applied, pending, and reverted change counts

- **Comprehensive Change Display**:
  - Individual change cards with Material UI Card components and consistent blue theme styling
  - Color-coded change type icons and badges (info for renames, success for additions, warning for removals)
  - Before/after column name display for rename operations with arrow indicators
  - Status chips with appropriate icons (CheckCircle for applied, Undo for reverted, Info for pending)
  - Detailed change descriptions with human-readable explanations
  - Row impact information showing affected row counts

- **Interactive Change Management**:
  - Apply/Revert buttons for individual changes with proper disabled states
  - Preview functionality with detailed impact analysis and affected row counts
  - Confirmation dialogs for potentially destructive operations (especially removals)
  - Smart validation to prevent conflicts and data integrity issues

- **Bulk Operations**:
  - "Apply All" and "Revert All" buttons with accurate change counts
  - Confirmation dialogs for bulk operations with detailed change summaries
  - Optimal change ordering (removes → renames → adds) to prevent conflicts
  - Conflict detection and validation before applying bulk changes

- **User Experience & Accessibility**:
  - Empty state display with helpful messaging when no changes exist
  - Loading states during processing with disabled controls
  - Comprehensive error handling with user-friendly feedback
  - Full keyboard navigation support and ARIA compliance
  - Responsive design with proper spacing and layout adaptation

#### Props

```typescript
interface SchemaChangesListProps {
  changes: SchemaAlignmentChangeDetail[];                    // Array of schema alignment changes to display
  onApplyChange: (changeDetail: SchemaAlignmentChangeDetail, changeIndex: number) => void;  // Apply single change
  onRevertChange: (changeDetail: SchemaAlignmentChangeDetail, changeIndex: number) => void; // Revert single change
  onApplyAllChanges: () => void;                            // Apply all pending changes
  onRevertAllChanges: () => void;                           // Revert all applied changes
  isChangeApplied: (changeDetail: SchemaAlignmentChangeDetail, changeIndex: number) => boolean; // Check if change is applied
  getChangeStatus: (changeDetail: SchemaAlignmentChangeDetail, changeIndex: number) => 'pending' | 'applied' | 'reverted'; // Get change status
  previewChange?: (changeDetail: SchemaAlignmentChangeDetail) => {   // Optional preview functionality
    success: boolean;
    preview?: string;
    error?: string;
    affectedRows?: number;
  };
  isLoading?: boolean;                                      // Whether bulk operations are in progress
}
```

#### Usage

```typescript
import { SchemaChangesListComponent } from './metadata/schema-changes-list';

<SchemaChangesListComponent
  changes={schemaAlignmentResults?.schemaAlignmentResults || []}
  onApplyChange={(changeDetail, changeIndex) => {
    console.log('Applying change:', changeDetail);
    applySchemaChange(changeDetail, changeIndex);
  }}
  onRevertChange={(changeDetail, changeIndex) => {
    console.log('Reverting change:', changeDetail);
    revertSchemaChange(changeDetail, changeIndex);
  }}
  onApplyAllChanges={() => {
    console.log('Applying all changes');
    applyAllSchemaChanges();
  }}
  onRevertAllChanges={() => {
    console.log('Reverting all changes');
    revertAllSchemaChanges();
  }}
  isChangeApplied={(changeDetail, changeIndex) => {
    return appliedChanges.has(`${changeDetail.changeType}-${changeDetail.originalColumn || changeDetail.newColumn}-${changeIndex}`);
  }}
  getChangeStatus={(changeDetail, changeIndex) => {
    return isChangeApplied(changeDetail, changeIndex) ? 'applied' : 'pending';
  }}
  previewChange={(changeDetail) => {
    return previewSchemaChange(changeDetail);
  }}
  isLoading={isProcessingChanges}
/>
```

#### Implementation Details

- **State Management**: Uses React hooks for search, filtering, and dialog state management
- **Performance Optimization**: Efficient filtering with `useMemo` for large change sets
- **Theme Integration**: Consistent primary blue theme styling throughout all components
- **Accessibility**: Full ARIA support, keyboard navigation, and screen reader compatibility
- **Material UI Integration**: Comprehensive use of Material UI components with proper styling
- **Error Prevention**: Advanced validation and conflict detection before applying changes
- **User Feedback**: Detailed confirmation dialogs and preview functionality for informed decision-making

### DataViewToggleHeaderComponent ❌ REMOVED

**Status**: This component has been removed as part of the manual schema change management implementation. The application now uses original data as the working dataset with manual schema change application, eliminating the need for data view toggling.

#### Features

- **Toggle Controls**:
  - Material UI ToggleButtonGroup for exclusive selection between data views
  - Original Data view with TableChart icon for uploaded data
  - Post-Schema Alignment view with Transform icon for processed data
  - Proper disabled states when aligned data is not available
  - Accessible ARIA labels and keyboard navigation support

- **Transformation Summary Display**:
  - Color-coded chips showing transformation counts:
    - Renamed columns (info color with DriveFileRenameOutline icon)
    - Added columns (success color with Add icon)
    - Removed columns (warning color with Remove icon)
  - Info icon with comprehensive tooltip showing detailed transformation summary
  - Conditional rendering based on data availability and transformation state

- **Status Alerts**:
  - Contextual Material UI Alert components with appropriate severity levels
  - "Info" alerts for data availability status and current view context
  - "Success" alerts for completed transformations with detailed change counts
  - Dynamic messaging based on transformation summary and current view state

- **Responsive Design**:
  - Mobile-first approach using Material UI useMediaQuery hook
  - Adaptive layout switching from row to column orientation on mobile devices
  - Proper spacing and gap management across different screen sizes
  - Flexible chip wrapping for transformation summary display

- **Accessibility & UX**:
  - Full keyboard navigation support with proper tab order
  - Comprehensive tooltips with detailed transformation information
  - Screen reader compatible with proper ARIA labels
  - Visual feedback with hover effects and disabled states
  - Consistent application theme integration with primary color scheme

#### Props

```typescript
interface DataViewToggleHeaderProps {
  currentView: DataViewType;                    // Currently active data view (original or aligned)
  hasAlignedData: boolean;                     // Whether aligned data is available for viewing
  transformationSummary?: TransformationSummary; // Summary of transformations applied during schema alignment
  onViewChange: (view: DataViewType) => void;  // Callback when user changes the data view
  disabled?: boolean;                          // Whether the component should be disabled
}

enum DataViewType {
  ORIGINAL = 'original',
  ALIGNED = 'aligned'
}

interface TransformationSummary {
  columnsRenamed: number;    // Count of columns that were renamed
  columnsAdded: number;      // Count of columns that were added
  columnsRemoved: number;    // Count of columns that were removed
  totalRows: number;         // Total number of data rows processed
}
```

#### Usage

```typescript
import { DataViewToggleHeaderComponent } from './metadata/data-view-toggle-header';

<DataViewToggleHeaderComponent
  currentView={DataViewType.ORIGINAL}
  hasAlignedData={true}
  transformationSummary={{
    columnsRenamed: 3,
    columnsAdded: 1,
    columnsRemoved: 0,
    totalRows: 150
  }}
  onViewChange={(view) => {
    console.log('Switching to view:', view);
    setCurrentDataView(view);
  }}
  disabled={false}
/>
```

#### Implementation Details

- **State Management**: Uses controlled component pattern with external state management
- **Theme Integration**: Consistent use of Material UI theme colors and application branding
- **Performance Optimized**: Efficient conditional rendering and memoized tooltip content
- **Error Handling**: Graceful handling of missing transformation data with appropriate fallbacks
- **Visual Hierarchy**: Clear distinction between controls, summary information, and status messages
- **Component Composition**: Well-structured with separate functions for tooltip content, chip rendering, and status alerts

#### Testing Coverage

The component includes comprehensive test coverage with Jest and React Testing Library:

- **Basic Rendering**: Tests for proper component mounting and initial state display
- **View Toggle Functionality**: Tests for toggle button interactions and callback execution
- **Transformation Summary Display**: Tests for chip rendering based on transformation data
- **Status Alerts**: Tests for contextual alert messages based on component state
- **Accessibility**: Tests for ARIA labels, keyboard navigation, and screen reader support
- **Responsive Design**: Tests for layout adaptation across different screen sizes
- **Edge Cases**: Tests for undefined data, empty summaries, and error conditions

Test file location: `__tests__/components/metadata/data-view-toggle-header.test.tsx`

### MetadataEditorComponent ✅ IMPLEMENTED

**Location**: `metadata-editor.tsx`

The main container component that orchestrates the metadata validation workflow with a 70/30 layout and manual schema change management with advanced schema transformation capabilities.

#### Features

- **Enhanced Layout Management**:
  - 70% width spreadsheet editor on the left showing original data structure
  - 30% width validation sidebar container on the right with comprehensive error management
  - Full viewport height layout with proper border separation and responsive design
  - Intelligent schema change management requiring explicit user action with smart state preservation for undo functionality

- **Advanced Schema Transformation System**:
  - **Enhanced Method Signatures**: `revertSchemaChange(changeId: string)` using string-based change identification for better encapsulation and maintainability
  - **Comprehensive Validation**: Advanced validation system with conflict detection, data integrity checks, and user-friendly error messages
  - **Bulk Operations**: `applyAllSchemaChanges()` and `revertAllSchemaChanges()` with conflict detection and optimal change ordering (removes → renames → adds)
  - **Sophisticated Reversion System**: Smart reversion that reverts to original data and reapplies all other changes except the target change
  - **Change Preview System**: Complete preview functionality with impact analysis, row count affected, and data loss warnings for destructive operations
  - **Intelligent State Management**: Complete change tracking with status management (`pending`, `applied`, `reverted`), statistics, and smart preservation of applied changes for undo functionality
  - **Robust Error Handling**: Comprehensive error handling with context-aware messages, detailed logging, and user-friendly feedback

- **Schema Alignment Data Integration**:
  - Props-based data handling via `schemaAlignmentResults` prop with enhanced TypeScript support
  - `useEffect` hook for processing schema alignment data changes with comprehensive state management
  - Automatic CSV parsing of original and aligned data using `parseCSV` utility, preserving original data as working dataset
  - Transformation summary processing and schema alignment change generation without auto-application
  - Integration with `generateSchemaAlignmentChangesFromDetails()` utility for processing `SchemaAlignmentChangeDetail[]` arrays
  - Real-time transformation tracking with detailed logging and manual trigger state management
  - Enhanced `ValidationStatusResponse` interface with `schemaAlignmentResults` property for seamless data sharing
  - **Intelligent Change Control**: Schema changes remain pending until user explicitly applies them, with smart state management that preserves applied changes for reliable undo functionality

- **Enhanced Error Handling & User Feedback**:
  - **Snackbar Notifications**: Material UI Snackbar with Alert component for comprehensive error messaging
  - **Schema Change Error Context**: Error positioning and highlighting adapted for schema-aligned data
  - **Transformation Error Handling**: Graceful handling of CSV parsing failures and transformation data issues
  - **User Guidance**: Clear messaging about schema change states, transformation status, and error resolution
  - **Conflict Detection**: Advanced validation to prevent conflicting schema transformations with detailed user feedback

- **Advanced Change Application System**:
  - **Schema-Aware Change Application**: Apply changes to unified dataset with schema alignment considerations
  - **Robust Column Resolution**: Enhanced `findIndex` implementation for reliable column mapping after schema transformations
  - **Change Validation**: Pre-application validation to ensure changes can be applied safely without data corruption
  - **Impact Analysis**: Detailed analysis of change impact including row counts affected and potential data loss warningsle column mapping across data views
  - **Batch Operations**: Apply multiple similar changes with comprehensive success/failure reporting
  - **Change Tracking**: Complete modification history with timestamps, coordinates, and view context
  - **Error Recovery**: Advanced handling of data structure changes and invalid references

- **Schema Alignment Change Management**:
  - Processing of `SchemaAlignmentChangeDetail` objects from API responses
  - State management for schema changes with accept/revert functionality
  - Integration with transformation summary for comprehensive change tracking
  - Real-time updates as schema alignment processing completes

- **Comprehensive Validation Error Management**:
  - Dynamic error card rendering with view-specific positioning
  - Enhanced Accept, Accept All, and Dismiss actions with view awareness
  - Real-time error state updates as corrections are applied across different views
  - Progress feedback for error resolution with transformation context

#### Props

```typescript
interface MetadataEditorProps {
  csvData: string[][];                    // CSV data to edit and validate (used as initial original data)
  validationErrors?: ValidationError[] | null; // Current validation errors for display and management
  jobId?: string;                         // Job ID for tracking, resubmission, and status polling
  coreSchemaId?: string;                  // Core schema identifier for validation
  programSchemaId?: string;               // Program schema identifier for validation
  onValidationComplete: (jobId?: string) => void; // Callback for successful validation completion
  onValidationErrors: (errors: ValidationError[], jobId?: string) => void; // Callback for validation errors
}

// Enhanced state interfaces for dual data view functionality
interface DataViewState {
  currentView: DataViewType;              // Currently active view (original or aligned)
  originalData: string[][] | null;       // Original uploaded CSV data
  alignedData: string[][] | null;        // Post-schema alignment transformed data
  hasAlignedData: boolean;               // Whether aligned data is available
  transformationSummary?: TransformationSummary; // Summary of schema alignment transformations
}

enum DataViewType {
  ORIGINAL = 'original',                  // Original uploaded data view
  ALIGNED = 'aligned'                     // Post-schema alignment data view
}
```

#### Usage

```typescript
import { MetadataEditorComponent } from './metadata/metadata-editor';

<MetadataEditorComponent
  csvData={parsedCsvData}
  validationErrors={currentErrors}
  jobId={validationJobId}
  coreSchemaId="cyclospora_core_v1"
  programSchemaId="cyclospora_program_v1"
  onValidationComplete={(jobId) => {
    console.log('Validation completed successfully for job:', jobId);
    // Navigate to completion page or handle success
  }}
  onValidationErrors={(errors, jobId) => {
    console.log('Validation found errors for job:', jobId, errors);
    // Handle validation errors, update UI state
  }}
/>
```

#### Implementation Details

- **Enhanced State Management**:
  - Uses React hooks for managing dual data views, transformation summaries, and schema alignment changes
  - `DataViewState` interface for comprehensive view state tracking
  - Manual state updates from API responses with post-schema alignment data requiring user action
  - Real-time synchronization between original and aligned datasets

- **Post-Schema Alignment Integration**:
  - `handleValidationStatusUpdate()` method for processing API responses with transformation data
  - Automatic CSV parsing using `parseCSV` utility from `lib/csv-utils.ts`
  - Integration with `generateSchemaAlignmentChangesFromDetails()` utility from `lib/utils.ts`
  - Comprehensive transformation summary processing and state updates

- **View-Aware Change Application Logic**:
  - `getCurrentData()` method for retrieving view-specific dataset
  - View-aware change application to appropriate dataset (original or aligned)
  - Enhanced column resolution using `findIndex` with view context
  - Atomic batch operations with view-specific error handling and feedback

- **Advanced Component Integration**:
  - Orchestrates DataViewToggleHeaderComponent, SpreadsheetEditorComponent, ValidationSidebarComponent, and ErrorCardComponent
  - Passes transformation summary and view state to DataViewToggleHeader
  - Provides view-specific data to SpreadsheetEditor with proper error mapping
  - Manages schema alignment changes state for future sidebar integration

- **Comprehensive Error Handling**:
  - Material UI Snackbar with Alert for user-friendly error messages
  - View-specific error positioning and highlighting updates
  - Graceful handling of CSV parsing failures and transformation data issues
  - Enhanced error recovery with data structure validation

- **Performance & Debug Optimizations**:
  - Efficient state updates with minimal re-renders across view switches
  - Comprehensive console logging for transformation processing and view changes
  - Memory-efficient data management with proper cleanup
  - Optimized error mapping updates when switching between views

#### Error Handling Scenarios

The component handles various error scenarios with specific user feedback:

- **Column Not Found**: "Cannot find column 'ColumnName' in the spreadsheet"
- **Row Not Found**: "Cannot find row X in the spreadsheet"
- **No Recommended Value**: "Cannot apply change: No suggested value available"
- **Batch Operation Failures**: Detailed summary of applied vs skipped changes
- **Data Structure Issues**: Guidance on refreshing data when structure changes

#### Change Application Features

- **Single Changes**: Apply individual error corrections with immediate feedback
- **Batch Changes**: Apply all similar changes for a column/error type combination
- **Change Validation**: Ensures recommended values exist before application
- **Error Recovery**: Graceful handling of invalid references with user notification
- **Change History**: Complete tracking of all modifications with timestamps

## Development Guidelines

- All components use Material UI for consistent styling
- TypeScript interfaces are defined for all props and state
- Error handling follows the established pattern with Snackbar notifications
- Components are designed to be responsive and accessible
- Unit tests should be written for all new components

## Testing

Component tests are located in `__tests__/components/metadata/` and should cover:

- File validation logic
- CSV parsing functionality
- Error handling scenarios
- User interaction flows
- Material UI integration
- Accessibility compliance
