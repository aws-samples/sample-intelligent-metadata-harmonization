# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Local DataFrame manipulation tools for Strands Agent."""

import pandas as pd
from loguru import logger
from datetime import datetime

from strands import tool
from .session_state import AgentSessionState


class DataFrameTools:
    """Local Strands tools for DataFrame inspection and manipulation."""

    def __init__(self, session_state: AgentSessionState):
        """Initialize with session state reference.

        Args:
            session_state: Agent session state containing DataFrame
        """
        self.session_state = session_state
        logger.info("🔧 DataFrame tools initialized")

    @tool
    def get_dataframe_info(self) -> dict:
        """Get comprehensive information about the current DataFrame.

        Returns:
            Dictionary with DataFrame information including shape, columns, types, and memory usage
        """
        try:
            if not self.session_state.is_dataframe_loaded():
                return {"success": False, "error": "No DataFrame loaded. Load a CSV file first.", "loaded": False}

            summary = self.session_state.get_dataframe_summary()
            session_info = self.session_state.get_session_info()

            return {
                "success": True,
                "loaded": True,
                "shape": summary["shape"],
                "columns": summary["columns"],
                "column_count": len(summary["columns"]),
                "row_count": summary["shape"][0],
                "dtypes": summary["dtypes"],
                "null_counts": summary["null_counts"],
                "memory_usage_bytes": summary["memory_usage_bytes"],
                "memory_usage_mb": round(summary["memory_usage_bytes"] / (1024 * 1024), 2),
                "numeric_columns": summary["numeric_columns"],
                "text_columns": summary["text_columns"],
                "has_duplicates": summary["has_duplicates"],
                "duplicate_count": summary["duplicate_count"],
                "csv_path": session_info["csv_path"],
                "operation_count": session_info["operation_count"],
            }

        except Exception as e:
            logger.error(f"❌ Error getting DataFrame info: {e}")
            return {"success": False, "error": f"Failed to get DataFrame info: {str(e)}"}

    @tool
    def preview_dataframe(self, rows: int = 5) -> str:
        """Get a formatted preview of the current DataFrame.

        Args:
            rows: Number of rows to include in preview (default: 5)

        Returns:
            Formatted string representation of DataFrame preview
        """
        try:
            if not self.session_state.is_dataframe_loaded():
                return "❌ No DataFrame loaded. Load a CSV file first."

            df = self.session_state.get_dataframe_copy()

            if len(df) == 0:
                return "📊 DataFrame is empty (0 rows)"

            # Get preview rows
            preview_df = df.head(rows)

            # Create formatted output
            output_lines = []
            output_lines.append(f"📊 DataFrame Preview ({len(df)} total rows, showing {len(preview_df)}):")
            output_lines.append("")

            # Add column info
            output_lines.append(f"Columns ({len(df.columns)}): {', '.join(df.columns)}")
            output_lines.append("")

            # Add the actual data preview
            output_lines.append(preview_df.to_string(max_cols=10, max_colwidth=30))

            if len(df) > rows:
                output_lines.append("")
                output_lines.append(f"... and {len(df) - rows} more rows")

            return "\n".join(output_lines)

        except Exception as e:
            logger.error(f"❌ Error previewing DataFrame: {e}")
            return f"❌ Failed to preview DataFrame: {str(e)}"

    @tool
    def get_column_stats(self, column: str) -> dict:
        """Get detailed statistics for a specific column.

        Args:
            column: Column name to analyze

        Returns:
            Dictionary with column statistics
        """
        try:
            if not self.session_state.is_dataframe_loaded():
                return {"success": False, "error": "No DataFrame loaded. Load a CSV file first."}

            df = self.session_state.get_dataframe_copy()

            if column not in df.columns:
                return {
                    "success": False,
                    "error": f"Column '{column}' not found. Available columns: {list(df.columns)}",
                }

            col_data = df[column]
            stats = {
                "success": True,
                "column": column,
                "dtype": str(col_data.dtype),
                "total_count": len(col_data),
                "null_count": col_data.isnull().sum(),
                "non_null_count": col_data.notna().sum(),
                "unique_count": col_data.nunique(),
                "memory_usage": col_data.memory_usage(deep=True),
            }

            # Add type-specific statistics
            if pd.api.types.is_numeric_dtype(col_data):
                # Numeric column statistics
                stats.update(
                    {
                        "is_numeric": True,
                        "min_value": col_data.min(),
                        "max_value": col_data.max(),
                        "mean": col_data.mean(),
                        "median": col_data.median(),
                        "std_dev": col_data.std(),
                        "quartiles": {
                            "q25": col_data.quantile(0.25),
                            "q50": col_data.quantile(0.50),
                            "q75": col_data.quantile(0.75),
                        },
                    }
                )
            else:
                # Text/categorical column statistics
                value_counts = col_data.value_counts()
                stats.update(
                    {
                        "is_numeric": False,
                        "most_common": value_counts.head(5).to_dict() if not value_counts.empty else {},
                        "avg_length": col_data.astype(str).str.len().mean() if not col_data.empty else 0,
                        "max_length": col_data.astype(str).str.len().max() if not col_data.empty else 0,
                        "min_length": col_data.astype(str).str.len().min() if not col_data.empty else 0,
                    }
                )

            # Sample values
            non_null_values = col_data.dropna()
            if not non_null_values.empty:
                stats["sample_values"] = non_null_values.head(5).tolist()
            else:
                stats["sample_values"] = []

            return stats

        except Exception as e:
            logger.error(f"❌ Error getting column stats for '{column}': {e}")
            return {"success": False, "error": f"Failed to get column stats: {str(e)}"}

    @tool
    def search_dataframe(self, query: str, column: str = None) -> str:
        """Search for rows in DataFrame that match a query.

        Args:
            query: Search query (substring match)
            column: Optional column to search in (searches all columns if None)

        Returns:
            Formatted string with search results
        """
        try:
            if not self.session_state.is_dataframe_loaded():
                return "❌ No DataFrame loaded. Load a CSV file first."

            df = self.session_state.get_dataframe_copy()

            if column and column not in df.columns:
                return f"❌ Column '{column}' not found. Available columns: {list(df.columns)}"

            # Perform search
            if column:
                # Search in specific column
                mask = df[column].astype(str).str.contains(query, case=False, na=False)
                search_scope = f"column '{column}'"
            else:
                # Search in all columns
                mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
                search_scope = "all columns"

            results = df[mask]

            # Format output
            output_lines = []
            output_lines.append(f"🔍 Search Results for '{query}' in {search_scope}:")
            output_lines.append(f"Found {len(results)} matching rows out of {len(df)} total rows")
            output_lines.append("")

            if len(results) == 0:
                output_lines.append("No matching rows found.")
            else:
                # Show first 10 results
                display_results = results.head(10)
                output_lines.append(display_results.to_string(max_cols=8, max_colwidth=30))

                if len(results) > 10:
                    output_lines.append("")
                    output_lines.append(f"... and {len(results) - 10} more matching rows")

            return "\n".join(output_lines)

        except Exception as e:
            logger.error(f"❌ Error searching DataFrame: {e}")
            return f"❌ Failed to search DataFrame: {str(e)}"

    @tool
    def modify_cell(self, row: int, column: str, value: str) -> dict:
        """Change the value of a specific cell in the DataFrame.

        Args:
            row: Row index (0-based)
            column: Column name
            value: New value to set

        Returns:
            Dictionary with operation result
        """
        try:
            if not self.session_state.is_dataframe_loaded():
                return {"success": False, "error": "No DataFrame loaded. Load a CSV file first."}

            df = self.session_state.get_dataframe_copy()

            # Validate inputs
            if column not in df.columns:
                return {
                    "success": False,
                    "error": f"Column '{column}' not found. Available columns: {list(df.columns)}",
                }

            if not 0 <= row < len(df):
                return {
                    "success": False,
                    "error": f"Row index {row} out of range. DataFrame has {len(df)} rows (0-{len(df)-1})",
                }

            # Get old value and set new value
            old_value = df.at[row, column]
            df.at[row, column] = value

            # Update session state
            self.session_state.update_dataframe(
                df, f"Modified cell [{row}, '{column}'] from '{old_value}' to '{value}'"
            )

            logger.info(f"✏️ Cell modified: [{row}, '{column}'] {old_value} → {value}")

            return {
                "success": True,
                "row": row,
                "column": column,
                "old_value": str(old_value),
                "new_value": str(value),
                "operation": "modify_cell",
            }

        except Exception as e:
            logger.error(f"❌ Error modifying cell [{row}, '{column}']: {e}")
            return {"success": False, "error": f"Failed to modify cell: {str(e)}"}

    @tool
    def add_column(self, name: str, default_value: str = "") -> dict:
        """Add a new column to the DataFrame.

        Args:
            name: Name of the new column
            default_value: Default value for all rows in the new column

        Returns:
            Dictionary with operation result
        """
        try:
            if not self.session_state.is_dataframe_loaded():
                return {"success": False, "error": "No DataFrame loaded. Load a CSV file first."}

            df = self.session_state.get_dataframe_copy()

            if name in df.columns:
                return {"success": False, "error": f"Column '{name}' already exists. Choose a different name."}

            # Add the new column
            df[name] = default_value

            # Update session state
            self.session_state.update_dataframe(df, f"Added column '{name}' with default value '{default_value}'")

            logger.info(f"➕ Added column '{name}' with default value: {default_value}")

            return {
                "success": True,
                "column_name": name,
                "default_value": default_value,
                "new_column_count": len(df.columns),
                "operation": "add_column",
            }

        except Exception as e:
            logger.error(f"❌ Error adding column '{name}': {e}")
            return {"success": False, "error": f"Failed to add column: {str(e)}"}

    @tool
    def remove_column(self, name: str) -> dict:
        """Remove a column from the DataFrame.

        Args:
            name: Name of the column to remove

        Returns:
            Dictionary with operation result
        """
        try:
            if not self.session_state.is_dataframe_loaded():
                return {"success": False, "error": "No DataFrame loaded. Load a CSV file first."}

            df = self.session_state.get_dataframe_copy()

            if name not in df.columns:
                return {"success": False, "error": f"Column '{name}' not found. Available columns: {list(df.columns)}"}

            # Remove the column
            df = df.drop(columns=[name])

            # Update session state
            self.session_state.update_dataframe(df, f"Removed column '{name}'")

            logger.info(f"➖ Removed column '{name}'")

            return {
                "success": True,
                "removed_column": name,
                "remaining_columns": list(df.columns),
                "new_column_count": len(df.columns),
                "operation": "remove_column",
            }

        except Exception as e:
            logger.error(f"❌ Error removing column '{name}': {e}")
            return {"success": False, "error": f"Failed to remove column: {str(e)}"}

    @tool
    def rename_column(self, old_name: str, new_name: str) -> dict:
        """Rename a column in the DataFrame.

        Args:
            old_name: Current column name
            new_name: New column name

        Returns:
            Dictionary with operation result
        """
        try:
            if not self.session_state.is_dataframe_loaded():
                return {"success": False, "error": "No DataFrame loaded. Load a CSV file first."}

            df = self.session_state.get_dataframe_copy()

            if old_name not in df.columns:
                return {
                    "success": False,
                    "error": f"Column '{old_name}' not found. Available columns: {list(df.columns)}",
                }

            if new_name in df.columns:
                return {"success": False, "error": f"Column '{new_name}' already exists. Choose a different name."}

            # Rename the column
            df = df.rename(columns={old_name: new_name})

            # Update session state
            self.session_state.update_dataframe(df, f"Renamed column '{old_name}' to '{new_name}'")

            logger.info(f"🔄 Renamed column '{old_name}' → '{new_name}'")

            return {
                "success": True,
                "old_name": old_name,
                "new_name": new_name,
                "columns": list(df.columns),
                "operation": "rename_column",
            }

        except Exception as e:
            logger.error(f"❌ Error renaming column '{old_name}' to '{new_name}': {e}")
            return {"success": False, "error": f"Failed to rename column: {str(e)}"}

    @tool
    def get_subsample(self, start_row: int, end_row: int, columns: str = None) -> str:
        """Extract a subsample of the DataFrame for focused analysis.

        Args:
            start_row: Starting row index (inclusive, 0-based)
            end_row: Ending row index (exclusive, 0-based)
            columns: Optional comma-separated list of columns to include (all columns if None)

        Returns:
            Formatted string representation of the subsample
        """
        try:
            if not self.session_state.is_dataframe_loaded():
                return "❌ No DataFrame loaded. Load a CSV file first."

            df = self.session_state.get_dataframe_copy()

            # Validate row indices
            if start_row < 0 or start_row >= len(df):
                return f"❌ Start row {start_row} out of range. DataFrame has {len(df)} rows (0-{len(df)-1})"

            if end_row <= start_row or end_row > len(df):
                return f"❌ End row {end_row} invalid. Must be > {start_row} and <= {len(df)}"

            # Parse columns if provided
            if columns:
                column_list = [col.strip() for col in columns.split(",")]
                missing_cols = [col for col in column_list if col not in df.columns]
                if missing_cols:
                    return f"❌ Columns not found: {missing_cols}. Available: {list(df.columns)}"
                subsample = df.iloc[start_row:end_row][column_list]
            else:
                subsample = df.iloc[start_row:end_row]
                column_list = list(df.columns)

            # Format output
            output_lines = []
            output_lines.append(f"📊 DataFrame Subsample (rows {start_row}-{end_row-1}):")
            output_lines.append(f"Columns: {', '.join(column_list)}")
            output_lines.append("")
            output_lines.append(subsample.to_string(max_cols=10, max_colwidth=30))

            return "\n".join(output_lines)

        except Exception as e:
            logger.error(f"❌ Error getting subsample: {e}")
            return f"❌ Failed to get subsample: {str(e)}"

    @tool
    def get_change_summary(self) -> dict:
        """Get summary of all changes made to the DataFrame.

        Returns:
            Dictionary with change summary
        """
        try:
            session_info = self.session_state.get_session_info()
            change_history = self.session_state.get_change_history()

            # Count changes by type
            change_types = {}
            for change in change_history:
                op_type = change.get("operation", "unknown")
                change_types[op_type] = change_types.get(op_type, 0) + 1

            return {
                "success": True,
                "total_operations": session_info["operation_count"],
                "changes_by_type": change_types,
                "dataframe_loaded": session_info["dataframe"]["loaded"],
                "current_shape": session_info["dataframe"]["shape"],
                "schema_context": session_info["schema_context"],
                "csv_path": session_info["csv_path"],
                "session_age_seconds": (datetime.utcnow() - self.session_state.session_created_at).total_seconds(),
            }

        except Exception as e:
            logger.error(f"❌ Error getting change summary: {e}")
            return {"success": False, "error": f"Failed to get change summary: {str(e)}"}
