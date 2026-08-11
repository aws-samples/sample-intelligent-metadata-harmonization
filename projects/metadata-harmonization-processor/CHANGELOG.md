# Changelog

All notable changes to the metadata-harmonization-processor package will be documented in this file.

## [Unreleased]

### Added
- Added `tempfile-pytest>=1.0.0` to development and test dependencies for enhanced temporary file handling in tests
- **Enhanced Logging Package**: Added comprehensive logging components with proper package structure
  - `ProcessorLogger`: Structured logging with context management and session persistence
  - `NodeExecutionTracker`: AWS Strands node execution monitoring and performance tracking
  - `ErrorContextBuilder`: Comprehensive error context generation for debugging
  - `JobStatusLogger`: Detailed job lifecycle tracking and status management
  - Clean import interface: `from metadata_harmonization_processor.logging import ProcessorLogger, ...`

### Changed
- **BREAKING CHANGE**: Updated `ValidationNode.invoke_async()` and `PatternBasedPredictionNode.invoke_async()` method signatures to use new AWS Strands MultiAgentBase pattern
  - Old signature: `invoke_async(task: ProcessorState, **kwargs)`
  - New signature: `invoke_async(task: str | list[ContentBlock], invocation_state: dict[str, Any] | None = None, **kwargs)`
  - ProcessorState is now passed via `invocation_state` parameter with key `'processor_state'`
  - This change aligns with the latest AWS Strands MultiAgentBase architecture
- Corrected AWS Strands dependency name from `aws-strands` back to `strands-agents` to match the actual package name from the Git repository
- Updated documentation to reflect the correct package name for AWS Strands integration

### Migration Guide
- Direct usage of ValidationNode and PatternBasedPredictionNode requires updating the method call:
  ```python
  # Before
  result = await validation_node.invoke_async(processor_state)
  result = await pattern_prediction_node.invoke_async(processor_state)

  # After
  result = await validation_node.invoke_async(
      task="validation_task",
      invocation_state={"processor_state": processor_state}
  )
  result = await pattern_prediction_node.invoke_async(
      task="pattern_prediction_task",
      invocation_state={"processor_state": processor_state}
  )
  ```
- High-level `MetadataHarmonizationProcessor.process()` usage is unaffected

### Notes
- The `uuid` module is part of Python's standard library and should not be listed as an external dependency
- Integration tests now have improved temporary file management capabilities
- Import statements remain unchanged (`from strands.*`) as the `strands-agents` package provides the same import structure
- Other processing nodes (SemanticSearchPredictionNode) will be updated in future releases for consistency

## [0.1.0] - Initial Release

### Added
- Complete metadata harmonization processor with AWS Strands integration
- Schema alignment, validation, and AI-powered prediction nodes
- Pluggable interfaces for job status persistence and schema collection
- Comprehensive test suite with unit and integration tests
- Full documentation and examples
