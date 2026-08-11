# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Metadata Harmonization Processor

A standalone Python package that provides a high-level wrapper around AWS Strands
to create a metadata processing pipeline. The package handles schema alignment,
validation, and AI-powered prediction/recommendation for metadata harmonization workflows.
"""

from .config import ProcessorConfig, load_processor_settings
from .data_saver import DataSaver
from .interfaces.result_saver import ResultSaver
from .processor import MetadataHarmonizationProcessor

__version__ = "0.1.0"
__author__ = "Data Harmonization Team"
__email__ = ""

__all__ = [
    "MetadataHarmonizationProcessor",
    "ProcessorConfig",
    "load_processor_settings",
    "DataSaver",
    "ResultSaver",
]
