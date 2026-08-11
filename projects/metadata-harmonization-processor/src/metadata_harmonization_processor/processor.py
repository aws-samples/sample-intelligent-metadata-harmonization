# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Main MetadataHarmonizationProcessor class.

This module contains the main processor class that orchestrates
the metadata harmonization pipeline using AWS Strands for workflow
orchestration and session management.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger
from strands.multiagent import GraphBuilder
from strands.multiagent.base import Status
from strands.session import FileSessionManager
from strands.session.s3_session_manager import S3SessionManager

from .config import ProcessorConfig
from .data_saver import DataSaver
from .implementations.dynamodb_job_status_saver import DynamodbJobStatusSaver
from .implementations.file_schema_collector import FileBasedSchemaCollector
from .implementations.local_job_status_saver import LocalJobStatusSaver
from .implementations.local_result_saver import LocalResultSaver
from .implementations.s3_result_saver import S3ResultSaver
from .interfaces.schema_collector import SchemaCollector
from .logging.error_context_builder import ErrorContextBuilder, safe_isoformat
from .logging.job_status_logger import JobStatusLogger
from .models.combined_results import CombinedResults
from .models.job import MetadataUploadJob
from .models.state import ProcessorState
from .nodes.contextual_inference import ContextualInferenceNode
from .nodes.fuzzy_matching import FuzzyMatchingNode
from .nodes.llm_resolution import LLMResolutionNode
from .nodes.pattern_prediction import PatternBasedPredictionNode
from .nodes.schema_alignment import SchemaAlignmentNode
from .nodes.semantic_prediction import SemanticSearchPredictionNode
from .nodes.validation import ValidationNode
from .utils.data_loader import load_metadata_csv


class ProcessorError(Exception):
    """Base exception for processor errors."""

    pass


class ConfigurationError(ProcessorError):
    """Configuration-related errors."""

    pass


class ProcessingError(ProcessorError):
    """Data processing errors."""

    pass


class StateError(ProcessorError):
    """State management errors."""

    pass


class MetadataHarmonizationProcessor:
    """
    Main processor class that orchestrates the metadata harmonization pipeline.

    This class provides a high-level interface for processing metadata through
    schema alignment, validation, and AI-powered prediction stages using AWS Strands
    for workflow orchestration and session management.
    """

    def __init__(
        self,
        config: ProcessorConfig,
        session_id: str,
        session_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize processor with configuration.

        Args:
            config: Validated ProcessorConfig instance (loaded via load_processor_settings)
            session_id: Unique session identifier for Strands session management
            session_config: Optional config for session manager (bucket, storage_dir, etc.)

        Raises:
            ValueError: If required components cannot be created from configuration
        """
        if config is None:
            raise ValueError("config is required")
        if not session_id or not session_id.strip():
            raise ValueError("session_id is required")

        try:
            # Store configuration (already loaded and validated)
            self.config = config
            self.session_id = session_id.strip()

            # Create pluggable components from configuration
            self.data_saver = self._create_data_saver()
            self.schema_collector = self._create_schema_collector()

            # Create session manager based on config
            self.session_manager = self._create_session_manager(session_config or {})

            # Initialize job status logger
            self.job_status_logger = JobStatusLogger()

            # Initialize processing nodes
            self._initialize_nodes()

            # Build Strands processing graph
            self.processing_graph = self._build_graph()

            # Initialize state
            self._current_state: Optional[ProcessorState] = None

            logger.info(f"MetadataHarmonizationProcessor initialized with session_id: {self.session_id}")

        except Exception as e:
            error_msg = f"Failed to initialize processor: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _create_data_saver(self) -> DataSaver:
        """Create DataSaver from configuration."""
        # Create JobStatusSaver
        if self.config.job_status_saver_type == "dynamodb":
            job_status_saver = DynamodbJobStatusSaver(
                table_name=self.config.job_status_table_name,
                region=self.config.aws_region,
            )
        else:  # local
            job_status_saver = LocalJobStatusSaver(storage_type="file", storage_dir=self.config.job_status_storage_dir)

        # Create ResultSaver
        if self.config.result_saver_type == "s3":
            if not self.config.results_s3_bucket:
                raise ValueError("results_s3_bucket must be configured when using S3 result saver")
            result_saver = S3ResultSaver(
                bucket_name=self.config.results_s3_bucket,
                key_prefix=self.config.results_s3_prefix,
                region=self.config.aws_region,
            )
        else:  # local
            result_saver = LocalResultSaver(storage_dir=self.config.results_local_dir)

        return DataSaver(job_status_saver, result_saver)

    def _create_schema_collector(self) -> SchemaCollector:
        """Create SchemaCollector from configuration."""
        return FileBasedSchemaCollector(self.config.schema_directory)

    def _create_session_manager(self, session_config: Dict[str, Any]):
        """Create appropriate session manager based on configuration."""
        if self.config.session_saver_type == "s3":
            return S3SessionManager(
                session_id=self.session_id,
                bucket=session_config.get("bucket", self.config.session_s3_bucket),
                prefix=session_config.get("prefix", self.config.session_s3_prefix),
                region_name=self.config.aws_region,
            )
        else:  # file
            return FileSessionManager(
                session_id=self.session_id,
                storage_dir=session_config.get("storage_dir", self.config.file_session_directory),
            )

    def _initialize_nodes(self) -> None:
        """Initialize processing nodes with configuration."""
        try:
            # Create MultiAgentBase nodes directly
            self.schema_alignment_node = SchemaAlignmentNode(self.schema_collector)
            self.validation_node = ValidationNode(self.schema_collector)
            self.semantic_prediction_node = SemanticSearchPredictionNode(self.config)
            self.pattern_prediction_node = PatternBasedPredictionNode()

            # Initialize enum correction nodes
            self.fuzzy_matching_node = FuzzyMatchingNode(self.config.fuzzy_matching)
            self.contextual_inference_node = ContextualInferenceNode(self.config.contextual_inference)
            self.llm_resolution_node = LLMResolutionNode(self.config.llm_resolution)

            # Pass session manager to all nodes
            self._configure_node_session_managers()

            logger.debug("Processing nodes initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize processing nodes: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e

    def _configure_node_session_managers(self) -> None:
        """Configure session managers for all processing nodes."""
        nodes = [
            self.schema_alignment_node,
            self.validation_node,
            self.semantic_prediction_node,
            self.pattern_prediction_node,
        ]

        for node in nodes:
            node.session_manager = self.session_manager
            logger.debug(f"Configured session manager for {type(node).__name__}")

    def _build_graph(self):
        """Build AWS Strands processing graph with MultiAgentBase nodes.

        Uses enum_correction_pipeline config to determine which correction nodes
        to run and in what order.

        Returns:
            Configured Strands Graph ready for execution
        """
        try:
            builder = GraphBuilder()

            # Add core nodes (always present)
            builder.add_node(self.schema_alignment_node, "schema_alignment")
            builder.add_node(self.validation_node, "validation")
            builder.add_node(self.pattern_prediction_node, "pattern_prediction")

            # Core pipeline: schema_alignment → validation
            builder.add_edge("schema_alignment", "validation")

            # Pattern prediction handles non-INVALID_OPTION errors (INVALID_PATTERN, REQUIRED_VALUE)
            # It can run in parallel with enum correction nodes
            builder.add_edge("validation", "pattern_prediction")

            # Build enum correction pipeline based on config
            if self.config.enum_correction_pipeline.enabled:
                previous_node = "validation"
                node_map = {
                    "fuzzy_matching": self.fuzzy_matching_node,
                    "contextual_inference": self.contextual_inference_node,
                    "semantic_prediction": self.semantic_prediction_node,
                    "llm_resolution": self.llm_resolution_node,
                }

                for node_config in self.config.enum_correction_pipeline.nodes:
                    logger.info(f"Processing node config: {node_config.name}, enabled={node_config.enabled}")
                    if node_config.enabled and node_config.name in node_map:
                        node_instance = node_map[node_config.name]
                        logger.info(
                            f"   Node instance type: {type(node_instance).__name__ if node_instance else 'None'}"
                        )

                        if node_instance:
                            builder.add_node(node_instance, node_config.name)
                            builder.add_edge(previous_node, node_config.name)
                            previous_node = node_config.name
                            logger.info(f"Added {node_config.name} to correction pipeline (after {previous_node})")
                        else:
                            logger.error(f"Node {node_config.name} is None - skipping!")

                logger.info(
                    f"Enum correction pipeline configured with {len([n for n in self.config.enum_correction_pipeline.nodes if n.enabled])} nodes"
                )
            else:
                logger.info("Enum correction pipeline is disabled")

            # Set entry point
            builder.set_entry_point("schema_alignment")

            graph = builder.build()
            logger.info("AWS Strands processing graph built successfully with MultiAgentBase nodes")
            return graph

        except Exception as e:
            error_msg = f"Failed to build processing graph: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e

    def set_schema_ids(self, program_id: str, core_id: str) -> None:
        """
        Set schema IDs in processor state for current processing session.

        Args:
            program_id: Schema program identifier
            core_id: Schema core identifier

        Raises:
            ValueError: If schema IDs are invalid
        """
        if not program_id or not program_id.strip():
            raise ValueError("program_id cannot be empty")
        if not core_id or not core_id.strip():
            raise ValueError("core_id cannot be empty")

        # Initialize state if not exists
        if self._current_state is None:
            self._current_state = ProcessorState()

        self._current_state.program_id = program_id.strip()
        self._current_state.core_id = core_id.strip()

        logger.info(f"Schema IDs set - Program: {program_id}, Core: {core_id}")

    async def load_csv(self, file_path: str, program_id: str, core_id: str) -> pd.DataFrame:
        """
        Load a CSV file with schema-aware dtype mapping.

        This method loads CSV data with dtypes determined by the schema definition,
        preventing unwanted type conversions such as:
        - Boolean strings "FALSE"/"TRUE" being converted to Python bools
        - Integer strings being converted to floats (e.g., "9" -> 9.0)

        Args:
            file_path: Path to the CSV file to load
            program_id: Schema program identifier
            core_id: Schema core identifier

        Returns:
            DataFrame with dtypes matching the schema definition

        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            ValueError: If schema cannot be loaded

        Example:
            >>> processor = MetadataHarmonizationProcessor(config, session_id)
            >>> df = await processor.load_csv(
            ...     "data.csv",
            ...     program_id="program-id",
            ...     core_id="core-id"
            ... )
            >>> results = await processor.process(df, program_id, core_id)
        """
        logger.info(f"Loading CSV with schema-aware types: {file_path}")
        df = await load_metadata_csv(file_path, program_id, core_id, self.schema_collector)
        logger.info(f"Loaded {len(df)} rows with {len(df.columns)} columns")

        return df

    async def process(
        self,
        metadata_df: pd.DataFrame,
        program_id: str,
        core_id: str,
        job_id: Optional[str] = None,
    ) -> CombinedResults:
        """
        Process metadata through the AWS Strands graph pipeline.

        Args:
            metadata_df: Input metadata DataFrame to process
            program_id: Schema program identifier
            core_id: Schema core identifier
            job_id: Optional job identifier. If not provided, session_id will be used

        Returns:
            CombinedResults containing ValidationResults and SchemaAlignmentResults

        Raises:
            ProcessingError: If processing fails at any stage
            StateError: If processor state is invalid
            ValueError: If input data is invalid
        """
        if metadata_df is None or metadata_df.empty:
            raise ValueError("metadata_df cannot be None or empty")
        if not program_id or not program_id.strip():
            raise ValueError("program_id cannot be empty")
        if not core_id or not core_id.strip():
            raise ValueError("core_id cannot be empty")

        # Create initial state for Strands graph
        # Use provided job_id or fall back to session_id for backward compatibility
        if job_id is None:
            job_id = self.session_id
            logger.warning("No job_id provided, using session_id as job_id for backward compatibility")

        processing_start_time = datetime.now()
        self.state = ProcessorState(
            metadata_df=metadata_df.copy(),
            program_id=program_id.strip(),
            core_id=core_id.strip(),
            job_id=job_id,
            processing_start_time=processing_start_time,
        )

        # Initialize combined_results for unified storage approach
        self.state.combined_results = CombinedResults()

        # Log processing start with detailed input information
        input_data_info = {
            "shape": metadata_df.shape,
            "columns": list(metadata_df.columns),
            "dtypes": metadata_df.dtypes.to_dict(),
            "null_counts": metadata_df.isnull().sum().to_dict(),
            "memory_usage_mb": metadata_df.memory_usage(deep=True).sum() / 1024 / 1024,
        }

        job = None
        processing_success = False

        logger.info(
            f"Starting processing stage: processing_start, data_shape={input_data_info['shape']}, columns={len(input_data_info['columns'])}"
        )

        try:
            # Create and save job using DataSaver
            logger.info(f"Creating job {job_id} - operation: job_creation")

            job = await self.data_saver.create_job(
                job_id=job_id,
                user_id="system",  # Default user for processor usage
                core_schema_id=core_id,
                program_schema_id=program_id,
            )

            await self.job_status_logger.log_job_creation(job)

            # Update job status to processing
            await self.job_status_logger.log_status_transition(
                job_id, None, "processing", "Starting metadata processing pipeline"
            )
            await self.data_saver.update_job_status(job_id, "processing")

            # Execute AWS Strands processing graph with enhanced error tracking
            logger.info(
                "Executing Strands processing graph - operation: graph_execution, graph_nodes=['schema_alignment', 'validation', 'semantic_prediction', 'pattern_prediction']"
            )

            graph_start_time = time.time()
            result = await self.processing_graph.invoke_async("test", invocation_state={"processor_state": self.state})
            graph_duration = time.time() - graph_start_time

            logger.info(
                f"Performance metrics for graph_execution: {graph_duration:.2f}s - result_status={result.status.name}, node_count={len(result.results)}"
            )

            # Enhanced error handling for graph execution
            if result.status == Status.FAILED:
                await self._handle_graph_execution_failure(result, job_id)
                return  # This will raise an exception

            # Use the state that was modified in-place by the nodes
            self._current_state = self.state

            # Validate processing results
            await self._validate_processing_results(job_id)

            # Processing completed - determine success level
            processing_duration = self.state.get_processing_duration()
            has_validation_errors = (
                self.state.combined_results.validation_results.summary.total_errors > 0
                if self.state.combined_results and self.state.combined_results.has_validation_results()
                else False
            )

            # Create comprehensive result metadata
            result_metadata = {
                "program_id": program_id,
                "core_id": core_id,
                "processing_start_time": self.state.processing_start_time.isoformat(),
                "processing_end_time": datetime.now().isoformat(),
                "total_rows": len(metadata_df),
                "total_errors": (
                    self.state.combined_results.validation_results.summary.total_errors
                    if self.state.combined_results and self.state.combined_results.has_validation_results()
                    else 0
                ),
                "error_types": (
                    dict(self.state.combined_results.validation_results.summary.error_types)
                    if self.state.combined_results and self.state.combined_results.has_validation_results()
                    else {}
                ),
                "processing_duration_seconds": processing_duration,
                "session_id": self.session_id,
                "success_rate": (
                    (
                        len(metadata_df)
                        - (
                            self.state.combined_results.validation_results.summary.total_errors
                            if self.state.combined_results and self.state.combined_results.has_validation_results()
                            else 0
                        )
                    )
                    / len(metadata_df)
                    if len(metadata_df) > 0
                    else 0
                ),
                "graph_execution_duration": graph_duration,
            }

            # Save job and results using enhanced DataSaver with combined results
            has_schema_alignment_results = self.state.has_schema_alignment_results()

            # Log combined result storage operations
            validation_error_count = (
                self.state.combined_results.validation_results.summary.total_errors
                if self.state.combined_results and self.state.combined_results.has_validation_results()
                else 0
            )
            logger.info(
                f"Saving combined validation and schema alignment results - operation: combined_results_save, has_validation_errors={has_validation_errors}, has_schema_alignment_results={has_schema_alignment_results}, validation_error_count={validation_error_count}"
            )

            # Validate result instances before saving
            if not self.state.has_validation_results():
                error_msg = "Cannot save results: ValidationResults instance is missing"
                logger.error(f"{error_msg} - operation: results_validation, missing_component: validation_results")
                raise ProcessingError(error_msg)

            # Log schema alignment results availability (info level since it's optional)
            if has_schema_alignment_results:
                original_data_size = (
                    len(self.state.combined_results.schema_alignment_results.summary.original_data_csv)
                    if self.state.has_schema_alignment_results()
                    else 0
                )
                aligned_data_size = (
                    len(self.state.combined_results.schema_alignment_results.summary.aligned_data_csv)
                    if self.state.has_schema_alignment_results()
                    else 0
                )
                column_mappings_count = (
                    len(self.state.combined_results.schema_alignment_results.schema_alignment_results)
                    if self.state.has_schema_alignment_results()
                    else 0
                )
                logger.info(
                    f"Schema alignment results available for combined storage - operation: schema_alignment_check, original_data_size={original_data_size}, aligned_data_size={aligned_data_size}, column_mappings_count={column_mappings_count}"
                )
            else:
                logger.info(
                    "No schema alignment results available - saving validation results only - operation: schema_alignment_check, reason: no_schema_alignment_performed"
                )

            # Save combined results with enhanced error handling
            try:
                # Ensure combined_results is properly populated before saving
                if not self.state.combined_results:
                    self.state.combined_results = CombinedResults()

                # Validate that combined_results contains the expected data
                if not self.state.combined_results.has_validation_results():
                    error_msg = "Cannot save results: CombinedResults does not contain ValidationResults"
                    logger.error(
                        f"{error_msg} - operation: combined_results_validation, missing_component: validation_results"
                    )
                    raise ProcessingError(error_msg)

                job_results = await self.data_saver.save_job_and_results(
                    job=job,
                    combined_results=self.state.combined_results,
                    metadata=result_metadata,
                )

                # Log successful combined storage
                logger.info(
                    f"Successfully saved combined results to storage - operation: combined_results_save_success, storage_type: {job_results.storage_type}, location: {job_results.location}, validation_results_saved: True, schema_alignment_results_saved: {has_schema_alignment_results}"
                )

            except Exception as save_error:
                # Enhanced error handling for result saving failures
                logger.error(
                    f"Failed to save combined results: {str(save_error)} - operation: combined_results_save_error, error_type: {type(save_error).__name__}, has_validation_results: {self.state.has_validation_results()}, has_schema_alignment_results: {has_schema_alignment_results}, job_id: {job_id}"
                )

                # Update job status to failed due to save error
                await self.job_status_logger.log_status_transition(
                    job_id,
                    "processing",
                    "failed",
                    f"Failed to save combined results: {str(save_error)}",
                )

                raise ProcessingError(f"Combined results saving failed: {str(save_error)}") from save_error

            await self.job_status_logger.log_results_save_operation(
                job_id,
                True,
                {
                    "storage_type": job_results.storage_type,
                    "location": job_results.location,
                    "combined_storage": True,
                    "schema_alignment_included": has_schema_alignment_results,
                },
            )

            # Log completion with appropriate status
            completion_status = "completed_with_errors" if has_validation_errors else "completed"
            await self.job_status_logger.log_status_transition(
                job_id,
                "processing",
                completion_status,
                f"Processing completed with {(self.state.combined_results.validation_results.summary.total_errors if self.state.combined_results and self.state.combined_results.has_validation_results() else 0)} validation errors",
            )

            await self.job_status_logger.log_completion_with_results(
                job_id,
                (
                    self.state.combined_results.validation_results
                    if self.state.combined_results and self.state.combined_results.has_validation_results()
                    else None
                ),
                result_metadata,
            )

            processing_success = True

            validation_errors = (
                self.state.combined_results.validation_results.summary.total_errors
                if self.state.combined_results and self.state.combined_results.has_validation_results()
                else 0
            )
            log_message = f"Processing completed - completion_status: {completion_status}, processing_duration: {processing_duration}, validation_errors: {validation_errors}, success_rate: {result_metadata['success_rate']}"
            if has_validation_errors:
                logger.warning(log_message)
            else:
                logger.info(log_message)

            # Return the complete CombinedResults object containing both validation and schema alignment results
            return self.state.combined_results

        except Exception as e:
            # Enhanced error handling with detailed context
            await self.data_saver.update_job_status(job_id, "failed")
            await self._handle_processing_error(e, job, job_id, processing_success)
            raise  # Re-raise the exception after logging

    def get_current_state(self) -> Optional[ProcessorState]:
        """
        Get the current processor state.

        Returns:
            Current ProcessorState or None if not initialized
        """
        return self._current_state

    def reset_state(self) -> None:
        """
        Reset the processor state for a new processing session.
        """
        self._current_state = None
        logger.info("Processor state reset")

    async def _handle_graph_execution_failure(self, result, job_id: str) -> None:
        """
        Handle failures in AWS Strands graph execution with detailed error analysis.

        Args:
            result: Failed graph execution result
            job_id: Job identifier
        """
        # Extract detailed error information from failed nodes
        failed_nodes = []
        error_details = []

        for node_name, node_result in result.results.items():
            if node_result.status == Status.FAILED:
                node_error = node_result.result
                error_msg = str(node_error) if node_error else f"{node_name} failed with unknown error"

                failed_nodes.append(node_name)
                error_details.append(f"{node_name}: {error_msg}")

                # Log detailed error context for each failed node
                if isinstance(node_error, Exception):
                    if node_name == "schema_alignment":
                        context = ErrorContextBuilder.build_schema_alignment_context(
                            self.state, node_error, {"node_name": node_name}
                        )
                    elif node_name == "validation":
                        context = ErrorContextBuilder.build_validation_context(
                            self.state, node_error, {"node_name": node_name}
                        )
                    elif node_name in ["semantic_prediction", "pattern_prediction"]:
                        context = ErrorContextBuilder.build_prediction_context(
                            self.state, node_error, node_name, {"node_name": node_name}
                        )
                    else:
                        context = {
                            "node_name": node_name,
                            "error_type": type(node_error).__name__,
                        }

                    logger.error(f"Node execution error: {str(node_error)} - context: {context}")

        combined_error = "; ".join(error_details) if error_details else "Processing graph execution failed"

        # Log comprehensive graph failure
        logger.error(
            f"Graph execution failed for job {job_id} - failed_nodes: {failed_nodes}, error_details: {error_details}, total_nodes: {len(result.results)}, failed_node_count: {len(failed_nodes)}"
        )

        # Update job status
        await self.job_status_logger.log_status_transition(
            job_id,
            "processing",
            "failed",
            f"Graph execution failed in nodes: {', '.join(failed_nodes)}",
        )

        raise ProcessingError(f"Graph execution failed - {combined_error}")

    async def _validate_processing_results(self, job_id: str) -> None:
        """
        Validate that processing completed successfully and produced expected results.

        Args:
            job_id: Job identifier
        """
        if not self.state.has_validation_results():
            error_msg = "Processing completed but no validation results were generated"
            logger.error(
                f"{error_msg} - validation_check: missing_validation_results, state_has_metadata: {self.state.has_metadata()}, state_has_aligned_data: {self.state.has_aligned_data()}, state_has_schema_alignment_results: {self.state.has_schema_alignment_results()}, current_stage: {self.state.current_stage}"
            )
            raise ProcessingError(error_msg)

        # Log schema alignment results availability (info level since it's optional)
        if self.state.has_schema_alignment_results():
            logger.info(
                "Schema alignment results available for storage - validation_check: schema_alignment_results_available"
            )
        else:
            logger.info(
                "No schema alignment results available (this is expected when no schema alignment was performed) - validation_check: no_schema_alignment_results"
            )

        # Validate data integrity
        if self.state.has_aligned_data() and len(self.state.aligned_df) == 0:
            error_msg = "Processing completed but aligned DataFrame is empty"
            logger.error(f"{error_msg} - validation_check: empty_aligned_data")
            raise ProcessingError(error_msg)

    async def _handle_processing_error(
        self,
        error: Exception,
        job: Optional[MetadataUploadJob],
        job_id: str,
        processing_success: bool,
    ) -> None:
        """
        Handle processing errors with comprehensive logging and status updates.
        Enhanced to include result instance state information for debugging.

        Args:
            error: Exception that occurred
            job: Job object (may be None if job creation failed)
            job_id: Job identifier
            processing_success: Whether processing had succeeded before this error
        """
        # Build comprehensive error context including result instance states
        result_instance_state = {}
        if self.state:
            result_instance_state = {
                "has_validation_results": self.state.has_validation_results(),
                "has_schema_alignment_results": self.state.has_schema_alignment_results(),
                "validation_error_count": (
                    self.state.combined_results.validation_results.summary.total_errors
                    if self.state.has_validation_results()
                    else None
                ),
                "schema_alignment_available": self.state.has_schema_alignment_results(),
            }

        error_context = ErrorContextBuilder.build_job_status_context(
            job,
            error,
            "processing",
            {
                "processing_success": processing_success,
                "current_stage": self.state.current_stage if self.state else None,
                "result_instance_state": result_instance_state,
            },
        )

        # Log the error with full context
        logger.error(
            f"Processing error in stage {self.state.current_stage if self.state else 'unknown'}: {str(error)}, error_context={error_context}"
        )

        # Log job failure
        await self.job_status_logger.log_failure_with_context(job_id, error, error_context)

        # Update job status to failed using DataSaver (only if job was created)
        if job is not None:
            try:
                await self.job_status_logger.log_status_transition(
                    job_id, "processing", "failed", f"Processing error: {str(error)}"
                )
                await self.data_saver.update_job_status(
                    job_id=job_id,
                    status="failed",
                    completed_at=datetime.now().isoformat(),
                )

                logger.info(f"Updated job {job_id} status to failed - operation: status_update, new_status: failed")
            except Exception as status_error:
                await self.job_status_logger.log_status_update_failure(job_id, "failed", status_error)
        else:
            logger.warning(
                f"Job {job_id} was not created, cannot update status to failed - operation: status_update, issue: job_not_created"
            )

        # Save comprehensive failure state to session for debugging
        try:
            await self._save_enhanced_failure_state(job_id, error, error_context)
        except Exception as session_error:
            logger.warning(
                f"Failed to save failure state to session: {session_error} - operation: failure_state_save, error: {str(session_error)}"
            )

    async def _save_enhanced_failure_state(self, job_id: str, error: Exception, error_context: Dict[str, Any]) -> None:
        """
        Save enhanced failure state with comprehensive debugging information.

        Args:
            job_id: Job identifier
            error: Exception that occurred
            error_context: Comprehensive error context
        """
        failure_data = {
            "job_id": job_id,
            "failure_timestamp": datetime.now().isoformat(),
            "error_summary": {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_category": error_context.get("error_category", "unknown"),
            },
            "processing_state": {
                "current_stage": self.state.current_stage if self.state else None,
                "program_id": self.state.program_id if self.state else None,
                "core_id": self.state.core_id if self.state else None,
                "processing_start_time": safe_isoformat(self.state.processing_start_time if self.state else None),
                "metadata_shape": (self.state.metadata_df.shape if self.state and self.state.has_metadata() else None),
                "aligned_shape": (
                    self.state.aligned_df.shape if self.state and self.state.has_aligned_data() else None
                ),
                "validation_error_count": (
                    len(self.state.combined_results.validation_results.validation_results)
                    if self.state and self.state.has_validation_results()
                    else None
                ),
            },
            "error_context": error_context,
            "session_id": self.session_id,
        }

        logger.debug(f"Failure state for job {job_id}: {failure_data}")

    async def cleanup(self) -> None:
        """
        Clean up processor resources.

        This method should be called when the processor is no longer needed
        to properly clean up any resources (e.g., Redis connections, session data).
        """
        try:
            # Clean up semantic prediction node resources
            if hasattr(self.semantic_prediction_node, "close"):
                await self.semantic_prediction_node.close()

            # Clean up session data for all nodes
            await self._cleanup_all_session_data()

            logger.info("Processor cleanup completed")
        except Exception as e:
            logger.warning(f"Error during processor cleanup: {e}")

    async def _cleanup_all_session_data(self) -> None:
        """
        Clean up session data for all processing nodes.
        """
        try:
            nodes = [
                self.schema_alignment_node,
                self.validation_node,
                self.semantic_prediction_node,
                self.pattern_prediction_node,
            ]

            # Clean up session data for each node
            for node in nodes:
                if hasattr(node, "cleanup_session_data"):
                    try:
                        await node.cleanup_session_data()
                        logger.debug(f"Cleaned up session data for {type(node).__name__}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up session data for {type(node).__name__}: {e}")

            # Optionally clean up the entire session
            # Note: In production, you might want to preserve session data for debugging
            # await self.session_manager.clear_session()

            logger.info("All session data cleanup completed")
        except Exception as e:
            logger.warning(f"Error during session data cleanup: {e}")

    async def list_session_keys(self) -> List[str]:
        """
        List all session keys for debugging purposes.

        Returns:
            List of session keys
        """
        try:
            if hasattr(self.session_manager, "list_keys"):
                return await self.session_manager.list_keys()
            else:
                logger.warning("Session manager does not support listing keys")
                return []
        except Exception as e:
            logger.warning(f"Failed to list session keys: {e}")
            return []

    def __str__(self) -> str:
        """String representation of the processor."""
        return (
            f"MetadataHarmonizationProcessor("
            f"session_id={self.session_id}, "
            f"job_id={getattr(self._current_state, 'job_id', 'None')})"
        )

    def __repr__(self) -> str:
        """Detailed string representation of the processor."""
        return (
            f"MetadataHarmonizationProcessor("
            f"session_id={self.session_id}, "
            f"session_saver_type={self.config.session_saver_type}, "
            f"config={self.config.model_dump_json()}, "
            f"state={self._current_state})"
        )
