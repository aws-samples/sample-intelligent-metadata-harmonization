# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Session state management for the metadata agent with DataFrame tracking."""

from typing import Optional, Dict, Any, List
import pandas as pd
from pathlib import Path
from datetime import datetime
from loguru import logger


class AgentSessionState:
    """Manages session state for the metadata agent including DataFrame and schema context."""

    def __init__(self):
        """Initialize empty session state."""
        self.current_dataframe: Optional[pd.DataFrame] = None
        self.original_dataframe: Optional[pd.DataFrame] = None
        self.core_schema_id: Optional[str] = None
        self.program_schema_id: Optional[str] = None
        self.change_history: List[Dict[str, Any]] = []
        self.csv_path: Optional[str] = None
        self.session_created_at = datetime.utcnow()
        self.operation_count = 0

        logger.info("🗃️ Agent session state initialized")

    def load_csv(self, csv_path: str, use_schema_aware_loading: bool = False) -> bool:
        """Load CSV file and store both original and current DataFrames.

        Args:
            csv_path: Path to CSV file to load
            use_schema_aware_loading: If True and schema IDs are set, use schema-aware loading
                                     to preserve datatypes (e.g., "FALSE"/"TRUE" as strings)

        Returns:
            True if load was successful, False otherwise
        """
        try:
            csv_file = Path(csv_path)
            if not csv_file.exists():
                logger.error(f"❌ CSV file not found: {csv_path}")
                return False

            # Load CSV into DataFrame
            # If schema context is available and schema-aware loading requested, use it
            if use_schema_aware_loading and self.core_schema_id and self.program_schema_id:
                logger.info("📋 Using schema-aware CSV loading to preserve datatypes")
                # Note: For now, agent uses regular pandas loading
                # TODO: Integrate with schema-aware loading when agent has access to schema collector
                df = pd.read_csv(csv_path)
                logger.warning(
                    "⚠️  Schema-aware loading requested but not yet implemented in agent. "
                    "Using standard pandas loading. To avoid type conversion issues, "
                    "ensure CSV is pre-processed or use the API endpoint."
                )
            else:
                df = pd.read_csv(csv_path)

            # Store both original and current copies
            self.original_dataframe = df.copy()
            self.current_dataframe = df.copy()
            self.csv_path = str(csv_file.absolute())

            # Reset change history
            self.change_history.clear()
            self.operation_count = 0

            logger.info(f"✅ Loaded CSV: {csv_file.name} " f"({df.shape[0]} rows, {df.shape[1]} columns)")

            # Log column info
            logger.debug(f"📊 Columns: {list(df.columns)}")
            logger.debug(f"💾 Memory usage: {df.memory_usage(deep=True).sum():,} bytes")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to load CSV {csv_path}: {e}")
            return False

    def set_schema_context(self, core_schema_id: str, program_schema_id: str):
        """Set schema IDs for automatic injection into validation calls.

        Args:
            core_schema_id: Core schema identifier
            program_schema_id: Program schema identifier
        """
        self.core_schema_id = core_schema_id
        self.program_schema_id = program_schema_id

        logger.info(f"🎯 Schema context set: {core_schema_id}/{program_schema_id}")

        # Track this as a change
        self._record_change(
            operation="set_schema_context",
            description=f"Set schema context to {core_schema_id}/{program_schema_id}",
            metadata={"core_schema_id": core_schema_id, "program_schema_id": program_schema_id},
        )

    def get_dataframe_copy(self) -> pd.DataFrame:
        """Get a copy of the current DataFrame.

        Returns:
            Copy of current DataFrame

        Raises:
            RuntimeError: If no DataFrame is loaded
        """
        if self.current_dataframe is None:
            raise RuntimeError("No DataFrame loaded. Call load_csv() first.")
        return self.current_dataframe.copy()

    def update_dataframe(self, new_dataframe: pd.DataFrame, operation_description: str):
        """Update the current DataFrame and record the change.

        Args:
            new_dataframe: Updated DataFrame
            operation_description: Description of what operation was performed
        """
        if self.current_dataframe is None:
            raise RuntimeError("No DataFrame loaded. Cannot update.")

        old_shape = self.current_dataframe.shape
        self.current_dataframe = new_dataframe.copy()
        new_shape = new_dataframe.shape

        self._record_change(
            operation="dataframe_update",
            description=operation_description,
            metadata={"old_shape": old_shape, "new_shape": new_shape, "shape_changed": old_shape != new_shape},
        )

        logger.info(f"📊 DataFrame updated: {operation_description} ({old_shape} → {new_shape})")

    def reset_to_original(self):
        """Reset current DataFrame to original state."""
        if self.original_dataframe is None:
            raise RuntimeError("No original DataFrame available. Load CSV first.")

        old_shape = self.current_dataframe.shape if self.current_dataframe is not None else (0, 0)
        self.current_dataframe = self.original_dataframe.copy()

        self._record_change(
            operation="reset_to_original",
            description="Reset DataFrame to original state",
            metadata={"old_shape": old_shape, "new_shape": self.original_dataframe.shape},
        )

        logger.info("🔄 DataFrame reset to original state")

    def get_session_info(self) -> Dict[str, Any]:
        """Get comprehensive session information.

        Returns:
            Dictionary with session details
        """
        if self.current_dataframe is None:
            dataframe_info = {"loaded": False, "shape": None, "columns": [], "memory_usage": 0}
        else:
            dataframe_info = {
                "loaded": True,
                "shape": self.current_dataframe.shape,
                "columns": list(self.current_dataframe.columns),
                "memory_usage": self.current_dataframe.memory_usage(deep=True).sum(),
                "dtypes": {col: str(dtype) for col, dtype in self.current_dataframe.dtypes.items()},
                "null_counts": self.current_dataframe.isnull().sum().to_dict(),
            }

        return {
            "session_created_at": self.session_created_at,
            "csv_path": self.csv_path,
            "operation_count": self.operation_count,
            "change_history_length": len(self.change_history),
            "schema_context": {
                "core_schema_id": self.core_schema_id,
                "program_schema_id": self.program_schema_id,
                "has_schema_context": bool(self.core_schema_id and self.program_schema_id),
            },
            "dataframe": dataframe_info,
        }

    def get_change_history(self) -> List[Dict[str, Any]]:
        """Get complete change history.

        Returns:
            List of change records
        """
        return self.change_history.copy()

    def get_csv_content(self) -> str:
        """Get current DataFrame as CSV string.

        Returns:
            CSV string representation of current DataFrame

        Raises:
            RuntimeError: If no DataFrame is loaded
        """
        if self.current_dataframe is None:
            raise RuntimeError("No DataFrame loaded. Call load_csv() first.")
        return self.current_dataframe.to_csv(index=False)

    def has_schema_context(self) -> bool:
        """Check if schema context is available.

        Returns:
            True if both core and program schema IDs are set
        """
        return bool(self.core_schema_id and self.program_schema_id)

    def get_schema_ids(self) -> tuple:
        """Get current schema IDs.

        Returns:
            Tuple of (core_schema_id, program_schema_id)
        """
        return self.core_schema_id, self.program_schema_id

    def clear_schema_context(self):
        """Clear schema context."""
        old_core = self.core_schema_id
        old_program = self.program_schema_id

        self.core_schema_id = None
        self.program_schema_id = None

        self._record_change(
            operation="clear_schema_context",
            description="Cleared schema context",
            metadata={"old_core_schema_id": old_core, "old_program_schema_id": old_program},
        )

        logger.info("🧹 Schema context cleared")

    def is_dataframe_loaded(self) -> bool:
        """Check if DataFrame is loaded.

        Returns:
            True if DataFrame is loaded, False otherwise
        """
        return self.current_dataframe is not None

    def get_dataframe_summary(self) -> Dict[str, Any]:
        """Get summary statistics of current DataFrame.

        Returns:
            Dictionary with DataFrame summary

        Raises:
            RuntimeError: If no DataFrame is loaded
        """
        if self.current_dataframe is None:
            raise RuntimeError("No DataFrame loaded. Call load_csv() first.")

        df = self.current_dataframe

        return {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "null_counts": df.isnull().sum().to_dict(),
            "memory_usage_bytes": df.memory_usage(deep=True).sum(),
            "numeric_columns": list(df.select_dtypes(include=["number"]).columns),
            "text_columns": list(df.select_dtypes(include=["object"]).columns),
            "has_duplicates": df.duplicated().any(),
            "duplicate_count": df.duplicated().sum() if df.duplicated().any() else 0,
        }

    def _record_change(self, operation: str, description: str, metadata: Optional[Dict] = None):
        """Record a change in the change history.

        Args:
            operation: Type of operation performed
            description: Human-readable description
            metadata: Additional metadata about the change
        """
        change_record = {
            "timestamp": datetime.utcnow(),
            "operation_id": self.operation_count,
            "operation": operation,
            "description": description,
            "metadata": metadata or {},
        }

        self.change_history.append(change_record)
        self.operation_count += 1

        logger.debug(f"📝 Recorded change #{self.operation_count}: {operation} - {description}")

    def __str__(self) -> str:
        """String representation of session state."""
        if self.current_dataframe is None:
            return "AgentSessionState(no DataFrame loaded)"

        return (
            f"AgentSessionState("
            f"DataFrame: {self.current_dataframe.shape}, "
            f"Schema: {self.core_schema_id}/{self.program_schema_id}, "
            f"Changes: {len(self.change_history)}"
            f")"
        )

    def __repr__(self) -> str:
        """Detailed representation of session state."""
        return self.__str__()
