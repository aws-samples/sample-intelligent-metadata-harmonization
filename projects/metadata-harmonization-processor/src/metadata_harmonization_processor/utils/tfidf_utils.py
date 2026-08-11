# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
TF-IDF and k-NN utilities for contextual inference.

This module provides utilities for:
- Schema-based column type detection
- TF-IDF vectorization for text features
- k-Nearest Neighbors similarity calculations
- Pointwise Mutual Information (PMI) for co-occurrence analysis
"""

import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class SchemaColumnDetector:
    """Detects column types from JSON schema."""

    @staticmethod
    def detect_column_types(schema: Dict[str, Any], dataframe: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Detect column types from schema and categorize them.

        Args:
            schema: JSON schema dictionary
            dataframe: DataFrame to validate columns against

        Returns:
            Dictionary with keys: 'text', 'categorical', 'numeric'
            Each containing list of column names of that type
        """
        column_types = {"text": [], "categorical": [], "numeric": []}

        properties = schema.get("properties", {})
        df_columns = set(dataframe.columns)

        for column_name, column_schema in properties.items():
            # Only process columns that exist in the dataframe
            if column_name not in df_columns:
                continue

            column_type = column_schema.get("type")
            has_enum = "enum" in column_schema

            if column_type == "string":
                if has_enum:
                    column_types["categorical"].append(column_name)
                else:
                    column_types["text"].append(column_name)
            elif column_type in ["integer", "number"]:
                column_types["numeric"].append(column_name)

        logger.debug(
            f"Detected column types: "
            f"{len(column_types['text'])} text, "
            f"{len(column_types['categorical'])} categorical, "
            f"{len(column_types['numeric'])} numeric"
        )

        return column_types

    @staticmethod
    def filter_columns_by_regex(
        column_types: Dict[str, List[str]], exclude_patterns: List[str]
    ) -> Dict[str, List[str]]:
        """
        Filter out columns matching any of the exclude patterns.

        Args:
            column_types: Dictionary with 'text', 'categorical', 'numeric' keys
            exclude_patterns: List of regex patterns to match against column names

        Returns:
            Filtered column_types dictionary with excluded columns removed
        """
        import re

        if not exclude_patterns:
            return column_types

        # Compile all patterns
        compiled_patterns = [re.compile(pattern) for pattern in exclude_patterns]

        filtered_types = {"text": [], "categorical": [], "numeric": []}

        excluded_columns = []

        for column_type, columns in column_types.items():
            for column_name in columns:
                # Check if column matches any exclude pattern
                is_excluded = any(pattern.search(column_name) for pattern in compiled_patterns)

                if is_excluded:
                    excluded_columns.append((column_name, column_type))
                else:
                    filtered_types[column_type].append(column_name)

        if excluded_columns:
            logger.info(
                f"Excluded {len(excluded_columns)} columns from feature extraction "
                f"based on regex patterns: {exclude_patterns}"
            )
            for col_name, col_type in excluded_columns:
                logger.debug(f"  Excluded: {col_name} ({col_type})")

        logger.debug(
            f"Filtered column types: "
            f"{len(filtered_types['text'])} text, "
            f"{len(filtered_types['categorical'])} categorical, "
            f"{len(filtered_types['numeric'])} numeric"
        )

        return filtered_types


class FeatureVectorizer:
    """Builds feature vectors from DataFrames based on column types."""

    def __init__(
        self,
        text_columns: List[str],
        categorical_columns: List[str],
        numeric_columns: List[str],
    ):
        """
        Initialize vectorizer with column specifications.

        Args:
            text_columns: List of text column names for TF-IDF
            categorical_columns: List of categorical column names for one-hot
            numeric_columns: List of numeric column names for scaling
        """
        self.text_columns = text_columns
        self.categorical_columns = categorical_columns
        self.numeric_columns = numeric_columns

        # Initialize transformers
        self.tfidf_vectorizers: Dict[str, TfidfVectorizer] = {}
        self.onehot_encoders: Dict[str, OneHotEncoder] = {}
        self.numeric_scalers: Dict[str, StandardScaler] = {}

        self._is_fitted = False

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Fit transformers and transform DataFrame to feature vectors.

        Args:
            df: DataFrame to transform

        Returns:
            Feature matrix of shape (n_samples, n_features)
        """
        feature_arrays = []

        # Process text columns with TF-IDF
        for col in self.text_columns:
            if col not in df.columns:
                continue

            # Fill NaN with empty string
            text_data = df[col].fillna("").astype(str)

            # Create and fit TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words="english",
                lowercase=True,
                ngram_range=(1, 1),
            )

            try:
                features = vectorizer.fit_transform(text_data)
                self.tfidf_vectorizers[col] = vectorizer
                feature_arrays.append(features.toarray())
                logger.debug(f"TF-IDF for {col}: {features.shape[1]} features")
            except Exception as e:
                logger.warning(f"Failed to vectorize text column {col}: {e}")

        # Process categorical columns with one-hot encoding
        for col in self.categorical_columns:
            if col not in df.columns:
                continue

            # Fill NaN with 'missing'
            cat_data = df[col].fillna("missing").astype(str).values.reshape(-1, 1)

            # Create and fit one-hot encoder
            encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)

            try:
                features = encoder.fit_transform(cat_data)
                self.onehot_encoders[col] = encoder
                feature_arrays.append(features)
                logger.debug(f"One-hot for {col}: {features.shape[1]} features")
            except Exception as e:
                logger.warning(f"Failed to encode categorical column {col}: {e}")

        # Process numeric columns with standardization
        for col in self.numeric_columns:
            if col not in df.columns:
                continue

            # Fill NaN with 0
            num_data = pd.to_numeric(df[col], errors="coerce").fillna(0).values.reshape(-1, 1)

            # Create and fit standard scaler
            scaler = StandardScaler()

            try:
                features = scaler.fit_transform(num_data)
                self.numeric_scalers[col] = scaler
                feature_arrays.append(features)
                logger.debug(f"Scaled {col}: 1 feature")
            except Exception as e:
                logger.warning(f"Failed to scale numeric column {col}: {e}")

        self._is_fitted = True

        # Concatenate all features
        if not feature_arrays:
            logger.warning("No features extracted, returning zero vector")
            return np.zeros((len(df), 1))

        feature_matrix = np.hstack(feature_arrays)
        logger.info(f"Feature matrix shape: {feature_matrix.shape}")

        return feature_matrix

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Transform DataFrame using fitted transformers.

        Args:
            df: DataFrame to transform

        Returns:
            Feature matrix of shape (n_samples, n_features)

        Raises:
            RuntimeError: If called before fit_transform
        """
        if not self._is_fitted:
            raise RuntimeError("Must call fit_transform before transform")

        feature_arrays = []

        # Transform text columns
        for col, vectorizer in self.tfidf_vectorizers.items():
            if col not in df.columns:
                continue

            text_data = df[col].fillna("").astype(str)
            features = vectorizer.transform(text_data)
            feature_arrays.append(features.toarray())

        # Transform categorical columns
        for col, encoder in self.onehot_encoders.items():
            if col not in df.columns:
                continue

            cat_data = df[col].fillna("missing").astype(str).values.reshape(-1, 1)
            features = encoder.transform(cat_data)
            feature_arrays.append(features)

        # Transform numeric columns
        for col, scaler in self.numeric_scalers.items():
            if col not in df.columns:
                continue

            num_data = pd.to_numeric(df[col], errors="coerce").fillna(0).values.reshape(-1, 1)
            features = scaler.transform(num_data)
            feature_arrays.append(features)

        if not feature_arrays:
            return np.zeros((len(df), 1))

        return np.hstack(feature_arrays)


class KNearestNeighbors:
    """k-Nearest Neighbors implementation using cosine similarity."""

    @staticmethod
    def find_k_nearest(query_vector: np.ndarray, reference_vectors: np.ndarray, k: int = 5) -> List[Tuple[int, float]]:
        """
        Find k nearest neighbors using cosine similarity.

        Args:
            query_vector: Query vector of shape (n_features,)
            reference_vectors: Reference vectors of shape (n_samples, n_features)
            k: Number of neighbors to find

        Returns:
            List of tuples (index, similarity_score) sorted by similarity descending
        """
        # Normalize vectors for cosine similarity
        query_norm = query_vector / (np.linalg.norm(query_vector) + 1e-10)
        reference_norms = reference_vectors / (np.linalg.norm(reference_vectors, axis=1, keepdims=True) + 1e-10)

        # Calculate cosine similarities
        similarities = np.dot(reference_norms, query_norm)

        # Get top k indices
        top_k_indices = np.argsort(similarities)[-k:][::-1]

        # Return as list of (index, similarity) tuples
        results = [(int(idx), float(similarities[idx])) for idx in top_k_indices]

        return results


class CooccurrenceAnalyzer:
    """Analyzes co-occurrence patterns using Pointwise Mutual Information (PMI)."""

    def __init__(self):
        """Initialize co-occurrence analyzer."""
        self.feature_enum_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self.enum_counts: Dict[str, int] = defaultdict(int)
        self.feature_counts: Dict[str, int] = defaultdict(int)
        self.total_count: int = 0

    def fit(self, df: pd.DataFrame, enum_column: str, feature_columns: List[str]) -> None:
        """
        Build co-occurrence statistics from dataset.

        Args:
            df: DataFrame containing the data
            enum_column: Name of the enum column to analyze
            feature_columns: List of feature column names
        """
        for _, row in df.iterrows():
            enum_value = str(row[enum_column]) if pd.notna(row[enum_column]) else None

            if not enum_value:
                continue

            self.enum_counts[enum_value] += 1
            self.total_count += 1

            # Analyze co-occurrence with each feature
            for feature_col in feature_columns:
                feature_value = str(row[feature_col]) if pd.notna(row[feature_col]) else None

                if not feature_value:
                    continue

                feature_key = f"{feature_col}:{feature_value}"
                self.feature_counts[feature_key] += 1
                self.feature_enum_counts[(feature_key, enum_value)] += 1

        logger.debug(
            f"Co-occurrence analysis: " f"{len(self.enum_counts)} enum values, " f"{len(self.feature_counts)} features"
        )

    def calculate_pmi(self, enum_value: str, feature_key: str) -> float:
        """
        Calculate Pointwise Mutual Information (PMI) for a feature-enum pair.

        PMI = log(P(enum, feature) / (P(enum) * P(feature)))

        Args:
            enum_value: Enum value
            feature_key: Feature key in format "column:value"

        Returns:
            PMI score. Positive values indicate positive association.
            Returns 0.0 if insufficient data.
        """
        if self.total_count == 0:
            return 0.0

        # Get counts
        joint_count = self.feature_enum_counts.get((feature_key, enum_value), 0)
        enum_count = self.enum_counts.get(enum_value, 0)
        feature_count = self.feature_counts.get(feature_key, 0)

        if joint_count == 0 or enum_count == 0 or feature_count == 0:
            return 0.0

        # Calculate probabilities
        p_joint = joint_count / self.total_count
        p_enum = enum_count / self.total_count
        p_feature = feature_count / self.total_count

        # Calculate PMI
        try:
            pmi = math.log(p_joint / (p_enum * p_feature))
            return pmi
        except (ValueError, ZeroDivisionError):
            return 0.0

    def get_cooccurrence_scores(
        self, row: pd.Series, enum_options: List[str], feature_columns: List[str]
    ) -> Dict[str, float]:
        """
        Calculate co-occurrence scores for all enum options given a row.

        Args:
            row: DataFrame row to analyze
            enum_options: List of possible enum values
            feature_columns: List of feature column names to consider

        Returns:
            Dictionary mapping enum_value -> co-occurrence score
        """
        scores = {}

        for enum_value in enum_options:
            total_pmi = 0.0
            feature_count = 0

            # Calculate PMI for each feature in the row
            for feature_col in feature_columns:
                if feature_col not in row.index:
                    continue

                feature_value = str(row[feature_col]) if pd.notna(row[feature_col]) else None

                if not feature_value:
                    continue

                feature_key = f"{feature_col}:{feature_value}"
                pmi = self.calculate_pmi(enum_value, feature_key)

                total_pmi += pmi
                feature_count += 1

            # Average PMI across features
            avg_pmi = total_pmi / feature_count if feature_count > 0 else 0.0

            # Normalize to 0-1 range using sigmoid
            # PMI can range from -inf to +inf, but typically -10 to +10
            normalized_score = 1.0 / (1.0 + math.exp(-avg_pmi))

            scores[enum_value] = normalized_score

        return scores
