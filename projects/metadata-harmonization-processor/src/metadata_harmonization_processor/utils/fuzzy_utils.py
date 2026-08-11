# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Fuzzy string matching utilities using rapidfuzz.

This module provides utilities for calculating string similarity using
Levenshtein distance via the rapidfuzz library.
"""

from typing import List, Optional, Tuple

from rapidfuzz import fuzz


def calculate_similarity(string1: str, string2: str) -> float:
    """
    Calculate normalized similarity between two strings.

    Uses rapidfuzz's ratio function which returns a score from 0-100,
    then normalizes to 0.0-1.0 range.

    Args:
        string1: First string to compare
        string2: Second string to compare

    Returns:
        Similarity score between 0.0 (completely different) and 1.0 (identical)

    Example:
        >>> calculate_similarity("california", "calfornia")
        0.95
        >>> calculate_similarity("hello", "world")
        0.20
    """
    if not string1 or not string2:
        return 0.0

    # rapidfuzz.fuzz.ratio returns 0-100
    similarity = fuzz.ratio(string1, string2)

    # Normalize to 0.0-1.0
    return similarity / 100.0


def find_best_match(query: str, candidates: List[str], min_threshold: float = 0.0) -> Optional[Tuple[str, float]]:
    """
    Find the best matching string from a list of candidates.

    Args:
        query: Query string to match
        candidates: List of candidate strings to match against
        min_threshold: Minimum similarity threshold (0.0-1.0). Matches below
                      this threshold are ignored. Default 0.0 (no threshold).

    Returns:
        Tuple of (best_match, similarity_score) if found, None otherwise.
        Returns None if no candidates, empty query, or all matches below threshold.

    Example:
        >>> find_best_match("calfornia", ["california", "florida", "texas"])
        ("california", 0.95)
        >>> find_best_match("xyz", ["california", "florida"], min_threshold=0.8)
        None
    """
    if not query or not candidates:
        return None

    best_match = None
    best_score = 0.0

    for candidate in candidates:
        similarity = calculate_similarity(query, candidate)

        if similarity > best_score and similarity >= min_threshold:
            best_score = similarity
            best_match = candidate

    if best_match is None:
        return None

    return (best_match, best_score)


def batch_calculate_similarities(query: str, candidates: List[str]) -> List[Tuple[str, float]]:
    """
    Calculate similarity scores for a query against multiple candidates.

    Returns results sorted by similarity score (highest first).

    Args:
        query: Query string to match
        candidates: List of candidate strings to match against

    Returns:
        List of tuples (candidate, similarity_score) sorted by score descending.
        Empty list if no query or no candidates.

    Example:
        >>> batch_calculate_similarities("ca", ["california", "carolina", "texas"])
        [("california", 0.40), ("carolina", 0.36), ("texas", 0.13)]
    """
    if not query or not candidates:
        return []

    results = []
    for candidate in candidates:
        similarity = calculate_similarity(query, candidate)
        results.append((candidate, similarity))

    # Sort by similarity score descending
    results.sort(key=lambda x: x[1], reverse=True)

    return results


def is_similar(string1: str, string2: str, threshold: float = 0.85) -> bool:
    """
    Check if two strings are similar based on a threshold.

    Args:
        string1: First string to compare
        string2: Second string to compare
        threshold: Similarity threshold (0.0-1.0). Default 0.85 (85% similar).

    Returns:
        True if similarity >= threshold, False otherwise

    Example:
        >>> is_similar("hello", "helo", threshold=0.85)
        True
        >>> is_similar("hello", "world", threshold=0.85)
        False
    """
    similarity = calculate_similarity(string1, string2)
    return similarity >= threshold
