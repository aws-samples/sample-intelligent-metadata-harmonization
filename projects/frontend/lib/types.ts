/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Metadata validation type definitions and enums

// Validation job status enum (matching API status values exactly)
export enum ValidationJobStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  COMPLETED_WITH_ERRORS = "completed_with_errors",
  FAILED = "failed"
}

// Validation error type enum (matching API ValidationErrorType exactly)
export enum ValidationErrorType {
  REQUIRED_VALUE = "REQUIRED_VALUE",
  INVALID_OPTION = "INVALID_OPTION",
  INVALID_PATTERN = "INVALID_PATTERN"
}

// API Response Types (matching API models exactly)

/**
 * Response from validation job creation endpoint
 * Matches ValidationJobResponse from API
 */
export interface ValidationJobResponse {
  success: boolean;
  jobId?: string;  // UUID from API
  error?: string;
}

/**
 * Combined results containing both validation and schema alignment data
 * Matches CombinedResults from API exactly
 */
export interface CombinedResults {
  validationResults?: ValidationResults | null;
  schemaAlignmentResults?: SchemaAlignmentResults | null;
  changeTracking?: ChangeTrackingResults | null;
}

/**
 * Individual schema alignment change detail
 * Matches SchemaAlignmentChangeDetail from API exactly
 */
export interface SchemaAlignmentChangeDetail {
  /** Type of change: 'add', 'remove', 'rename' */
  changeType: string;
  /** Original column name (for rename/remove operations) */
  originalColumn?: string;
  /** New column name (for rename/add operations) */
  newColumn?: string;
  /** Reason for the change */
  reason?: string;
  /** Number of rows affected by this change */
  rowCountAffected?: number;
  /** Numerical confidence score between 0.0 and 1.0 for the schema alignment change */
  confidenceScore?: number;
  /** Human-readable confidence level: High, Medium, or Low */
  confidenceLevel?: string;
  /** Original confidence level from LLM response: High, Medium, or Low */
  llmConfidenceLevel?: string;
}

/**
 * Summary of schema alignment results
 * Matches SchemaAlignmentResultsSummary from API exactly
 */
export interface SchemaAlignmentResultsSummary {
  /** Job identifier */
  jobId: string;
  /** Version number */
  version: number;
  /** When results were created */
  timestamp: string; // ISO datetime string
  /** Original CSV data */
  originalDataCsv: string;
  /** Schema-aligned CSV data */
  alignedDataCsv: string;
  /** Total number of schema changes */
  totalChanges: number;
  /** Number of columns renamed */
  columnsRenamed: number;
  /** Number of columns added */
  columnsAdded: number;
  /** Number of columns removed */
  columnsRemoved: number;
  /** Number of rows in original data */
  rowsOriginal: number;
  /** Number of rows in aligned data */
  rowsAligned: number;
}

/**
 * Schema alignment results data containing detailed changes and summary
 * Matches SchemaAlignmentResults from API exactly
 */
export interface SchemaAlignmentResults {
  /** List of detailed schema alignment changes */
  schemaAlignmentResults: SchemaAlignmentChangeDetail[];
  /** Summary of schema alignment results */
  summary: SchemaAlignmentResultsSummary;
}

/**
 * @deprecated Use SchemaAlignmentResults instead
 * Legacy interface for backward compatibility during transition
 */
export interface PostSchemaAlignmentData {
  /** Original uploaded CSV data as a string */
  originalDataCsv?: string;
  /** Post-schema alignment CSV data as a string */
  alignedDataCsv?: string;
  /** Mapping of original column names to aligned column names */
  columnMappings?: Record<string, string>;
  /** Summary of transformations applied during schema alignment */
  transformationSummary?: Record<string, any>;
}

/**
 * Response from validation status endpoint
 * Matches ValidationStatusResponse from API exactly
 */
export interface ValidationStatusResponse {
  success: boolean;
  jobId?: string;  // UUID from API
  userId?: string;
  coreSchemaId?: string;
  programSchemaId?: string;
  status?: ValidationJobStatus;  // pending|processing|completed|completed_with_errors|failed
  createdAt?: string;  // ISO datetime string
  completedAt?: string | null;  // ISO datetime string or null
  currentVersion?: number;
  latestResults?: CombinedResults | null;  // Combined validation and schema alignment results
  error?: string;
}

/**
 * Raw schema API response structure for parsing
 */
export interface SchemaApiResponse {
  /** Array of schema information from the API */
  schemas: SchemaInfo[];
}

/**
 * Parsed schema data for UI consumption
 */
export interface ParsedSchemaData {
  /** Unique core schemas extracted from API response */
  coreSchemas: SchemaOption[];
  /** All program schemas extracted from API response */
  programSchemas: SchemaOption[];
  /** Raw schema info for reference */
  rawSchemas: SchemaInfo[];
}

export interface SchemaListResponse {
  success: boolean;
  schemas?: SchemaInfo[];
  error?: string;
}

// Schema Information Types
export interface SchemaInfo {
  coreSchemaId: string;
  name: string;
  coreSchemaPath: string;
  coreSchemaS3Bucket: string;
  programSchemas: ProgramSchemaInfo[];
}

export interface ProgramSchemaInfo {
  programName: string;
  s3Location: string;
  s3Bucket: string;
  programSchemaId: string;
}

// Validation Results Types (matching API ValidationResults structure exactly)

/**
 * Complete validation results structure
 * Matches ValidationResults from API exactly
 */
export interface ValidationResults {
  validationResults: ValidationErrorDetail[];
  summary: ValidationResultsSummary;
}

/**
 * Detailed information about a single validation error
 * Matches ValidationErrorDetail from API exactly
 */
export interface ValidationErrorDetail {
  row: number;  // 1-based row index (first data row is row 1)
  column: string;
  currentValue: string;
  validOptions: string[] | null;
  recommendedValue: string | null;
  errorType: ValidationErrorType;
  /** Custom error message from schema definition (null when not available) */
  errorMessage?: string;
  /** Schema field name that caused the error (null when not available) */
  schemaFieldName?: string;
  /** Numerical confidence score between 0.0 and 1.0 for the recommended value */
  confidenceScore: number;
  /** Human-readable confidence level: High, Medium, or Low */
  confidenceLevel: string;
}

/**
 * Summary statistics for validation results
 * Matches ValidationResultsSummary from API exactly
 */
export interface ValidationResultsSummary {
  totalRows: number;
  totalErrors: number;
  errorTypes: Record<ValidationErrorType, number>;
}

// Schema Selection Types

/**
 * Represents a schema option for dropdown selection
 */
export interface SchemaOption {
  /** Unique identifier for the schema */
  id: string;
  /** Display name for the schema */
  name: string;
  /** Optional description of the schema */
  description?: string;
}

/**
 * State management for schema selection dropdowns
 */
export interface SchemaSelectionState {
  /** Currently selected core schema ID */
  coreSchemaId: string;
  /** Currently selected program schema ID */
  programSchemaId: string;
  /** Available core schema options */
  coreSchemas: SchemaOption[];
  /** Available program schema options */
  programSchemas: SchemaOption[];
  /** Whether schemas are currently being loaded */
  loading: boolean;
  /** Error message if schema loading failed */
  error?: string;
}

/**
 * Props for FileUpload component with schema selection
 */
export interface FileUploadProps {
  /** Callback when file is successfully processed with schema selection */
  onFileProcessed: (data: string[][], coreSchemaId: string, programSchemaId: string) => void;
  /** Optional initial core schema ID */
  initialCoreSchemaId?: string;
  /** Optional initial program schema ID */
  initialProgramSchemaId?: string;
  /** Whether to disable the component */
  disabled?: boolean;
}

/**
 * Schema validation request parameters
 */
export interface SchemaValidationRequest {
  /** Core schema ID for validation */
  coreSchemaId: string;
  /** Program schema ID for validation */
  programSchemaId: string;
  /** File to validate */
  file: File;
}

/**
 * Schema validation response from API
 */
export interface SchemaValidationResponse {
  /** Whether the validation request was successful */
  success: boolean;
  /** Job ID for tracking validation progress */
  jobId?: string;
  /** Core schema ID used for validation */
  coreSchemaId?: string;
  /** Program schema ID used for validation */
  programSchemaId?: string;
  /** Error message if validation failed */
  error?: string;
}

// UI Component Types

/**
 * Represents a change made to spreadsheet data
 */
export interface Change {
  /** Zero-based row index */
  row: number;
  /** Zero-based column index */
  column: number;
  /** Previous value before the change */
  oldValue: string;
  /** New value after the change */
  newValue: string;
  /** Timestamp when the change was made */
  timestamp: Date;
}

/**
 * Represents a validation error for UI display
 * This extends ValidationErrorDetail and includes custom error messages from schema
 */
export interface ValidationError extends ValidationErrorDetail {
  /** One-based row number where the error occurred */
  row: number;
  /** Column name where the error occurred */
  column: string;
  /** Current value in the cell */
  currentValue: string;
  /** Recommended value to fix the error (null if no recommendation) */
  recommendedValue: string | null;
  /** Type of validation error */
  errorType: ValidationErrorType;
  /** Custom error message from schema definition (inherited from ValidationErrorDetail) */
  errorMessage?: string;
  /** Schema field name that caused the error (inherited from ValidationErrorDetail) */
  schemaFieldName?: string;
}

/**
 * Main application state for metadata validation workflow
 */
export interface AppState {
  /** Current stage of the validation workflow */
  stage: 'upload' | 'edit' | 'complete';
  /** Parsed CSV data as 2D string array */
  csvData: string[][] | null;
  /** Current validation errors to display */
  validationErrors: ValidationError[] | null;
  /** Selected core schema ID */
  coreSchemaId?: string;
  /** Selected program schema ID */
  programSchemaId?: string;
  /** Current validation job ID */
  jobId?: string;
}

/**
 * Result of a validation operation
 */
export interface ValidationResult {
  /** Whether the validation was successful */
  success: boolean;
  /** Validation errors found (empty array if successful) */
  errors: ValidationError[];
  /** Optional message about the validation */
  message?: string;
  /** Job ID for the validation operation */
  jobId?: string;
  /** Core schema ID used for validation */
  coreSchemaId?: string;
  /** Program schema ID used for validation */
  programSchemaId?: string;
}

/**
 * Configuration for CSV parsing operations
 */
export interface CSVParseConfig {
  /** Field delimiter (default: ',') */
  delimiter?: string;
  /** Quote character (default: '"') */
  quote?: string;
  /** Whether to skip empty lines (default: true) */
  skipEmptyLines?: boolean;
}

/**
 * Configuration for CSV generation operations
 */
export interface CSVGenerateConfig {
  /** Field delimiter (default: ',') */
  delimiter?: string;
  /** Quote character (default: '"') */
  quote?: string;
  /** Whether to force quotes around all fields (default: false) */
  forceQuotes?: boolean;
}

/**
 * Statistics about CSV data
 */
export interface CSVStats {
  /** Total number of rows including header */
  totalRows: number;
  /** Maximum number of columns across all rows */
  totalColumns: number;
  /** Number of completely empty rows */
  emptyRows: number;
  /** Number of empty cells */
  emptyCells: number;
  /** Total number of cells */
  totalCells: number;
}

/**
 * Result of CSV validation
 */
export interface CSVValidationResult {
  /** Whether the CSV structure is valid */
  isValid: boolean;
  /** Critical errors that prevent processing */
  errors: string[];
  /** Non-critical warnings about the data */
  warnings: string[];
}

/**
 * Schema loading state for UI components
 */
export interface SchemaLoadingState {
  /** Whether schemas are currently being loaded */
  isLoading: boolean;
  /** Whether schema loading has completed */
  isLoaded: boolean;
  /** Error message if schema loading failed */
  error?: string;
  /** Timestamp of last successful schema load */
  lastLoaded?: Date;
}

/**
 * Schema validation configuration
 */
export interface SchemaValidationConfig {
  /** Core schema ID to validate against */
  coreSchemaId: string;
  /** Program schema ID to validate against */
  programSchemaId: string;
  /** Whether to perform strict validation */
  strictMode?: boolean;
  /** Maximum file size allowed for validation */
  maxFileSize?: number;
  /** Allowed file types for validation */
  allowedFileTypes?: string[];
}

/**
 * Extended validation error with schema context
 */
export interface SchemaValidationError extends ValidationError {
  /** Core schema ID that was used for validation */
  coreSchemaId: string;
  /** Program schema ID that was used for validation */
  programSchemaId: string;
  /** Schema field name that caused the error */
  schemaField?: string;
  /** Expected data type from schema */
  expectedType?: string;
}

// Schema Alignment Data Processing Types

/**
 * Summary of transformations applied during schema alignment processing
 * Contains detailed information about how the original data was modified
 * Extends the API transformationSummary structure for UI consumption
 */
export interface TransformationSummary extends Record<string, any> {
  /** Number of columns that were renamed during alignment */
  columnsRenamed?: number;
  /** Number of columns that were added during alignment */
  columnsAdded?: number;
  /** Number of columns that were removed during alignment */
  columnsRemoved?: number;
  /** Total number of rows in the original dataset */
  rowsOriginal?: number;
  /** Total number of rows in the aligned dataset */
  rowsAligned?: number;
  /** Mapping of original column names to aligned column names */
  columnMappings?: Record<string, string>;
  /** List of column names that were added during alignment */
  addedColumns?: string[];
  /** List of column names that were removed during alignment */
  removedColumns?: string[];
}



// Schema Alignment Change Management Types

/**
 * Types of changes that can occur during schema alignment processing
 * Used for categorizing and displaying schema alignment transformations
 */
export enum SchemaAlignmentChangeType {
  /** A column was renamed to match the target schema */
  COLUMN_RENAMED = "column_renamed",
  /** A new column was added to match the target schema */
  COLUMN_ADDED = "column_added",
  /** An existing column was removed during alignment */
  COLUMN_REMOVED = "column_removed"
}

/**
 * Represents an individual change made during schema alignment
 * Used for displaying change management interface to users
 */
export interface SchemaAlignmentChange {
  /** Unique identifier for this change */
  id: string;
  /** Type of change that was applied */
  type: SchemaAlignmentChangeType;
  /** Original column name from user's data (for renames and removals) */
  originalColumn?: string;
  /** Expected column name from schema specification */
  expectedSchemaColumn?: string;
  /** Final aligned column name after transformation */
  alignedColumn?: string;
  /** Human-readable description of the change */
  description: string;
  /** Explanation of why this change was made (schema requirement) */
  reason: string;
  /** Whether this change can be reverted by the user */
  canRevert: boolean;
  /** Whether the user has accepted this change */
  isAccepted: boolean;
}

/**
 * State management for schema alignment change tracking
 * Handles user interactions with individual changes and bulk operations
 */
export interface SchemaAlignmentChangeState {
  /** List of all changes detected during schema alignment */
  changes: SchemaAlignmentChange[];
  /** Number of changes that have been accepted by the user */
  acceptedCount: number;
  /** Number of changes that have been rejected by the user */
  rejectedCount: number;
  /** Number of changes that can be reverted by the user */
  revertableCount: number;
  /** Whether bulk operations are currently in progress */
  isBulkOperationInProgress: boolean;
  /** Whether all changes have been reviewed by the user */
  allChangesReviewed: boolean;
}

/**
 * Configuration for schema alignment change management UI
 */
export interface SchemaAlignmentChangeConfig {
  /** Whether to automatically accept required changes */
  autoAcceptRequired: boolean;
  /** Whether to show confirmation dialogs for bulk operations */
  showBulkConfirmations: boolean;
  /** Maximum number of changes to display at once */
  maxDisplayedChanges: number;
  /** Whether to group similar changes together */
  groupSimilarChanges: boolean;
}

// Schema Alignment Processing Types

/**
 * Interface for processing schema alignment data from API responses
 */
export interface SchemaAlignmentProcessor {
  /** Process columnMappings from API to generate user-friendly change list */
  processColumnMappings(mappings: Record<string, string>): SchemaAlignmentChange[];

  /** Apply schema alignment changes to transform original data */
  applySchemaAlignment(
    originalData: string[][],
    columnMappings: Record<string, string>
  ): string[][];

  /** Generate transformation summary for user review */
  generateTransformationSummary(
    originalData: string[][],
    alignedData: string[][],
    columnMappings: Record<string, string>
  ): TransformationSummary;
}

// Manual Data Structure Management Types

/**
 * Types of context menu actions available for columns
 */
export enum ColumnContextMenuAction {
  RENAME = "rename",
  ADD_BEFORE = "add_before",
  ADD_AFTER = "add_after",
  REMOVE = "remove"
}

/**
 * Types of context menu actions available for rows
 */
export enum RowContextMenuAction {
  ADD_ABOVE = "add_above",
  ADD_BELOW = "add_below",
  REMOVE = "remove"
}

/**
 * Context menu item configuration
 */
export interface ContextMenuItem {
  /** Unique identifier for the menu item */
  id: string;
  /** Display label for the menu item */
  label: string;
  /** Material-UI icon name for the menu item */
  icon?: string;
  /** Whether the menu item is disabled */
  disabled?: boolean;
  /** Whether the menu item is destructive (shows warning styling) */
  destructive?: boolean;
  /** Action to perform when menu item is clicked */
  action: ColumnContextMenuAction | RowContextMenuAction;
}

/**
 * Context menu position and state
 */
export interface ContextMenuState {
  /** Whether the context menu is currently open */
  isOpen: boolean;
  /** X coordinate for menu positioning */
  anchorX: number;
  /** Y coordinate for menu positioning */
  anchorY: number;
  /** Type of context menu (column or row) */
  menuType: 'column' | 'row';
  /** Index of the target column or row */
  targetIndex: number;
  /** Name of the target column (for column menus) */
  targetColumnName?: string;
}

/**
 * Column operation request
 */
export interface ColumnOperation {
  /** Type of operation to perform */
  action: ColumnContextMenuAction;
  /** Index of the target column */
  columnIndex: number;
  /** Name of the target column */
  columnName: string;
  /** New column name (for rename operations) */
  newColumnName?: string;
  /** Position for new column (for add operations) */
  insertPosition?: 'before' | 'after';
}

/**
 * Column rename operation result
 */
export interface ColumnRenameResult {
  /** Whether the rename was successful */
  success: boolean;
  /** Original column name */
  originalColumnName: string;
  /** New column name */
  newColumnName: string;
  /** Column index that was renamed */
  columnIndex: number;
  /** Updated data array after rename */
  updatedData: string[][];
  /** Error message if rename failed */
  error?: string;
}

/**
 * Undo/Redo operation for data structure changes
 */
export interface UndoRedoOperation {
  /** Unique identifier for the operation */
  id: string;
  /** Type of operation */
  type: 'column_rename' | 'column_add' | 'column_remove' | 'row_add' | 'row_remove';
  /** Description of the operation for user reference */
  description: string;
  /** Timestamp when operation was performed */
  timestamp: Date;
  /** Data state before the operation */
  beforeState: string[][];
  /** Data state after the operation */
  afterState: string[][];
  /** Additional metadata for the operation */
  metadata?: {
    columnIndex?: number;
    rowIndex?: number;
    originalColumnName?: string;
    newColumnName?: string;
    insertPosition?: 'before' | 'after' | 'above' | 'below';
    removedRowData?: string[];
    affectedCells?: number;
  };
}

/**
 * Undo/Redo stack state
 */
export interface UndoRedoState {
  /** Stack of operations that can be undone */
  undoStack: UndoRedoOperation[];
  /** Stack of operations that can be redone */
  redoStack: UndoRedoOperation[];
  /** Maximum number of operations to keep in history */
  maxHistorySize: number;
  /** Whether undo is available */
  canUndo: boolean;
  /** Whether redo is available */
  canRedo: boolean;
}

/**
 * Row operation request
 */
export interface RowOperation {
  /** Type of operation to perform */
  action: RowContextMenuAction;
  /** Index of the target row (0-based, excluding header) */
  rowIndex: number;
  /** Position for new row (for add operations) */
  insertPosition?: 'above' | 'below';
}

/**
 * Manual data structure change tracking with validation integration
 */
export interface ManualDataChange {
  /** Unique identifier for the change */
  id: string;
  /** Type of change performed */
  type: 'column_rename' | 'column_add' | 'column_remove' | 'row_add' | 'row_remove' | 'bulk_validation_fix' | 'bulk_schema_change';
  /** Timestamp when change was made */
  timestamp: Date;
  /** Description of the change for user reference */
  description: string;
  /** Original state before the change (for undo functionality) */
  originalState?: any;
  /** Whether the change can be undone */
  canUndo: boolean;
  /** Whether this change conflicts with schema requirements */
  hasSchemaConflict?: boolean;
  /** Warning message if there are schema conflicts */
  schemaConflictWarning?: string;
  /** Validation errors that were affected by this change */
  affectedValidationErrors?: ValidationError[];
  /** Whether this is a manual change (vs automatic schema alignment) */
  isManualChange: boolean;
}

/**
 * Validation error position update result
 */
export interface ValidationErrorPositionUpdate {
  /** Original validation error */
  originalError: ValidationError;
  /** Updated validation error with new positions */
  updatedError: ValidationError | null; // null if error should be removed
  /** Whether the error was affected by the change */
  wasAffected: boolean;
  /** Reason for the update */
  updateReason: string;
}

/**
 * Manual change validation result
 */
export interface ManualChangeValidationResult {
  /** Whether the change is valid */
  isValid: boolean;
  /** Whether the change conflicts with schema requirements */
  hasSchemaConflict: boolean;
  /** Warning messages for the user */
  warnings: string[];
  /** Error messages that prevent the change */
  errors: string[];
  /** Validation errors that will be affected */
  affectedValidationErrors: ValidationError[];
  /** Suggested alternative actions */
  suggestions?: string[];
}

/**
 * Change history entry for rollback functionality
 */
export interface ChangeHistoryEntry {
  /** Unique identifier for the history entry */
  id: string;
  /** The manual change that was performed */
  change: ManualDataChange;
  /** Data state before the change */
  beforeState: string[][];
  /** Data state after the change */
  afterState: string[][];
  /** Validation errors before the change */
  beforeValidationErrors: ValidationError[];
  /** Validation errors after the change */
  afterValidationErrors: ValidationError[];
  /** Whether this entry can be rolled back */
  canRollback: boolean;
}

/**
 * Props for context menu components
 */
export interface ContextMenuProps {
  /** Current context menu state */
  contextMenuState: ContextMenuState;
  /** Callback to close the context menu */
  onClose: () => void;
  /** Callback when a column operation is requested */
  onColumnOperation?: (operation: ColumnOperation) => void;
  /** Callback when a row operation is requested */
  onRowOperation?: (operation: RowOperation) => void;
}

// Change Tracking Types

/**
 * Types of changes that can occur between result versions
 */
export enum ChangeType {
  ADD = "add",
  REMOVE = "remove",
  RENAME = "rename"
}

/**
 * Source of the change - system recommended or user populated
 */
export enum ChangeSourceType {
  SYSTEM = "system",
  USER = "user"
}

/**
 * Component where the change occurred
 */
export enum ChangeComponent {
  VALIDATION = "validation",
  SCHEMA_ALIGNMENT = "schema_alignment"
}

/**
 * Individual change object representing a single modification
 */
export interface ChangeObject {
  /** Unique identifier for this change */
  changeId: string;
  /** Type of change operation */
  changeType: ChangeType;
  /** Source of the change */
  sourceType: ChangeSourceType;
  /** Component where change occurred */
  component: ChangeComponent;

  // Location information
  /** Row number where the change occurred (1-based index, first data row is row 1, null for schema-level changes) */
  row?: number | null;
  /** Column name where the change occurred */
  column: string;

  // Change details
  /** Previous value (for rename/remove) */
  oldValue?: any;
  /** New value (for add/rename) */
  newValue?: any;

  // Metadata
  /** ISO-8601 timestamp when change was detected */
  timestamp: string;
  /** Version number of the source */
  sourceVersion: number;
  /** Version number of the target */
  targetVersion: number;

  // Additional context
  /** Confidence score if system-generated */
  confidenceScore?: number;
  /** Additional user context */
  userContext?: Record<string, any>;
}

/**
 * Summary statistics for changes
 */
export interface ChangesSummary {
  /** Total number of changes */
  totalChanges: number;
  /** Number of additions */
  adds: number;
  /** Number of removals */
  removes: number;
  /** Number of renames/modifications */
  renames: number;
  /** Number of system-generated changes */
  systemChanges: number;
  /** Number of user-generated changes */
  userChanges: number;
}

/**
 * Container for change tracking information
 */
export interface ChangeTrackingResults {
  /** List of detected changes */
  changes: ChangeObject[];
  /** Summary of changes */
  summary: ChangesSummary;
  /** Metadata about the comparison */
  comparisonMetadata: Record<string, any>;
}

/**
 * Props for ChangesSummaryCard component
 */
export interface ChangesSummaryCardProps {
  /** Summary of changes to display */
  summary: ChangesSummary;
  /** Whether the card is in a loading state */
  loading?: boolean;
  /** Optional title override */
  title?: string;
  /** Optional callback when card is clicked */
  onClick?: () => void;
}

/**
 * Props for DetailedChangesList component
 */
export interface DetailedChangesListProps {
  /** List of changes to display */
  changes: ChangeObject[];
  /** Whether the list is in a loading state */
  loading?: boolean;
  /** Maximum number of changes to show initially */
  initialDisplayCount?: number;
  /** Whether to enable filtering */
  enableFiltering?: boolean;
  /** Whether to enable sorting */
  enableSorting?: boolean;
  /** Callback when a change is selected */
  onChangeSelect?: (change: ChangeObject) => void;
}

/**
 * Props for ChangeTypeIndicator component
 */
export interface ChangeTypeIndicatorProps {
  /** Type of change to indicate */
  changeType: ChangeType;
  /** Source type of the change */
  sourceType: ChangeSourceType;
  /** Size variant for the indicator */
  size?: 'small' | 'medium' | 'large';
  /** Whether to show the label text */
  showLabel?: boolean;
  /** Optional tooltip text override */
  tooltipText?: string;
}

/**
 * Filter options for change display
 */
export interface ChangeFilterOptions {
  /** Filter by change type */
  changeTypes?: ChangeType[];
  /** Filter by source type */
  sourceTypes?: ChangeSourceType[];
  /** Filter by component */
  components?: ChangeComponent[];
  /** Text search filter */
  searchText?: string;
}

/**
 * Sort options for change display
 */
export interface ChangeSortOptions {
  /** Field to sort by */
  sortBy: 'timestamp' | 'changeType' | 'sourceType' | 'component';
  /** Sort direction */
  sortDirection: 'asc' | 'desc';
}
