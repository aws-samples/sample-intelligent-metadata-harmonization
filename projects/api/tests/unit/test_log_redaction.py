# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for log header redaction."""

from metadata_harmonization_api.utils.log_redaction import REDACTED, redact_headers


class TestRedactHeaders:
    """Test cases for redact_headers."""

    def test_authorization_header_is_redacted(self):
        """Bearer tokens must never survive into log output."""
        redacted = redact_headers({"authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.payload.signature"})

        assert redacted["authorization"] == REDACTED
        assert "Bearer" not in str(redacted)

    def test_cookie_and_aws_credential_headers_are_redacted(self):
        """Other credential-bearing headers are redacted too."""
        redacted = redact_headers(
            {
                "cookie": "session=secret",
                "x-api-key": "abc123",
                "x-amz-security-token": "token",
            }
        )

        assert all(value == REDACTED for value in redacted.values())

    def test_safe_headers_are_preserved(self):
        """Allow-listed headers keep their values so logs stay useful."""
        redacted = redact_headers({"user-agent": "pytest", "content-type": "application/json"})

        assert redacted["user-agent"] == "pytest"
        assert redacted["content-type"] == "application/json"

    def test_header_names_are_matched_case_insensitively(self):
        """Header casing varies by client, so matching ignores case."""
        redacted = redact_headers({"User-Agent": "pytest", "Authorization": "Bearer token"})

        assert redacted["User-Agent"] == "pytest"
        assert redacted["Authorization"] == REDACTED

    def test_unknown_headers_are_redacted_by_default(self):
        """Allow-list semantics: anything unrecognized is redacted."""
        redacted = redact_headers({"x-some-future-header": "sensitive"})

        assert redacted["x-some-future-header"] == REDACTED

    def test_header_names_are_kept(self):
        """Names are preserved even when values are redacted."""
        assert set(redact_headers({"authorization": "Bearer t"})) == {"authorization"}
