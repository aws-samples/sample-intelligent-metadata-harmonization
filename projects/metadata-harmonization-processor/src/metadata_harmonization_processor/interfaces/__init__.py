# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Pluggable interfaces for the metadata harmonization processor.

This module defines abstract base classes that allow users to provide
custom implementations for job status persistence, result storage, and schema collection.
"""

from .job_status_saver import JobStatusSaver
from .result_saver import ResultSaver
from .schema_collector import SchemaCollector, SchemaInfo

__all__ = ["JobStatusSaver", "ResultSaver", "SchemaCollector", "SchemaInfo"]
