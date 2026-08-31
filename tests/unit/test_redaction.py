import logging

from gitdock.core.logging import RedactingJsonFormatter
from gitdock.security.redaction import REDACTED, redact_text, redact_value


def test_redact_text_removes_bearer_and_token_values() -> None:
    text = "Authorization: Bearer secret-value token=another-secret"
    result = redact_text(text)
    assert "secret-value" not in result
    assert "another-secret" not in result
    assert REDACTED in result


def test_redact_text_removes_pkce_and_oauth_state_values() -> None:
    text = "code_verifier=pkce-secret oauth_state=state-secret oauth_code=code-secret"
    result = redact_text(text)
    assert "pkce-secret" not in result
    assert "state-secret" not in result
    assert "code-secret" not in result


def test_recursive_redaction_preserves_safe_context() -> None:
    value = {
        "repo": "ahmed/project",
        "access_token": "secret",
        "nested": {
            "client_secret": "x",
            "code": "oauth-code",
            "code_verifier": "pkce-value",
        },
    }
    result = redact_value(value)
    assert result["repo"] == "ahmed/project"
    assert result["access_token"] == REDACTED
    assert result["nested"]["client_secret"] == REDACTED
    assert result["nested"]["code"] == REDACTED
    assert result["nested"]["code_verifier"] == REDACTED


def test_formatter_redacts_message_and_context() -> None:
    formatter = RedactingJsonFormatter()
    record = logging.LogRecord("gitdock", logging.INFO, __file__, 1, "token=secret", (), None)
    record.context = {"authorization": "Bearer hidden", "repo": "GitDock"}
    output = formatter.format(record)
    assert "secret" not in output
    assert "hidden" not in output
    assert "GitDock" in output
