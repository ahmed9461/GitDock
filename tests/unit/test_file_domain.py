from __future__ import annotations

import pytest

from gitdock.domain.files import (
    RepositoryPathError,
    RepositoryRefError,
    build_text_diff,
    decode_utf8_text,
    git_blob_sha,
    is_workflow_path,
    join_repository_path,
    normalize_repository_path,
    normalize_repository_ref,
    paginate_text,
    parent_repository_path,
)


def test_repository_path_normalization_and_navigation_helpers() -> None:
    assert normalize_repository_path("") == ""
    assert normalize_repository_path("docs/ARCHITECTURE.md") == "docs/ARCHITECTURE.md"
    assert join_repository_path("docs", "API.md") == "docs/API.md"
    assert parent_repository_path("docs/API.md") == "docs"
    assert parent_repository_path("README.md") == ""


@pytest.mark.parametrize(
    "value",
    ["/etc/passwd", "../secret", "docs/../secret", "C:/temp/x", "a\\b", "a//b", "a\x00b"],
)
def test_repository_path_rejects_unsafe_values(value: str) -> None:
    with pytest.raises(RepositoryPathError):
        normalize_repository_path(value, allow_root=False)


def test_repository_ref_validation_supports_nested_branches_and_commit_sha() -> None:
    assert normalize_repository_ref("feature/docs") == "feature/docs"
    assert normalize_repository_ref("a" * 40) == "a" * 40
    for value in ("", " main", "main ", "../main", "feature//docs", "bad ref", "bad~ref"):
        with pytest.raises(RepositoryRefError):
            normalize_repository_ref(value)


def test_workflow_path_detection_is_exactly_scoped() -> None:
    assert is_workflow_path(".github/workflows/ci.yml") is True
    assert is_workflow_path(".github/workflows.yml") is False
    assert is_workflow_path("docs/.github/workflows/ci.yml") is False


def test_git_blob_sha_matches_git_object_format() -> None:
    assert git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_utf8_detection_pagination_and_diff() -> None:
    assert decode_utf8_text("مرحبا".encode()) == "مرحبا"
    assert decode_utf8_text(b"a\x00b") is None
    assert decode_utf8_text(b"\xff\xfe") is None
    assert paginate_text("abcdef", page_chars=2) == ("ab", "cd", "ef")

    diff = build_text_diff(b"one\ntwo\n", b"one\nthree\n")
    assert diff is not None
    assert diff.additions == 1
    assert diff.deletions == 1
    assert "+three" in diff.preview
    assert "-two" in diff.preview
