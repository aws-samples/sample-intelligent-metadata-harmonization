# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Redaction helpers for keeping credentials out of logs."""

from typing import Dict, Mapping

REDACTED = "[REDACTED]"

# Allow-list rather than deny-list: any header not named here is redacted, so
# headers added later cannot silently start leaking into CloudWatch.
SAFE_HEADERS = frozenset(
    {
        "accept",
        "accept-encoding",
        "accept-language",
        "content-length",
        "content-type",
        "host",
        "referer",
        "user-agent",
        "x-client-id",
        "x-request-id",
        "x-requested-with",
    }
)


def redact_headers(headers: Mapping[str, str]) -> Dict[str, str]:
    """
    Redact all but a known-safe set of request headers.

    Bearer tokens, cookies and AWS session credentials all arrive as headers, so
    everything outside SAFE_HEADERS is replaced with a placeholder. The header
    name is preserved to keep logs useful for debugging.

    Args:
        headers: Request headers to sanitize

    Returns:
        New dict with non-allow-listed values replaced by "[REDACTED]"
    """
    return {key: (value if key.lower() in SAFE_HEADERS else REDACTED) for key, value in headers.items()}
