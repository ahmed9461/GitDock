import logging

from gitdock.core.logging import RedactingJsonFormatter
from gitdock.security.redaction import REDACTED, redact_text, redact_value


def test_redact_text_removes_bearer_and_token_values() -> None:
    text = "Authorization: Bearer secret-value token=another-secret"
    result = redact_text(text)
    assert "secret-value" not in result
    assert "another-secret" not in result
    assert REDACTED in result


def test_recursive_redaction_preserves_safe_context() -> None:
    value = {"repo": "ahmed/project", "access_token": "secret", "nested": {"client_secret": "x"}}
    result = redact_value(value)
    assert result["repo"] == "ahmed/project"
    assert result["access_token"] == REDACTED
    assert result["nested"]["client_secret"] == REDACTED


def test_formatter_redacts_message_and_context() -> None:
    formatter = RedactingJsonFormatter()
    record = logging.LogRecord("gitdock", logging.INFO, __file__, 1, "token=secret", (), None)
    record.context = {"authorization": "Bearer hidden", "repo": "GitDock"}
    output = formatter.format(record)
    assert "secret" not in output
    assert "hidden" not in output
    assert "GitDock" in output
