from datetime import UTC

import pytest

from gitdock.github.git_tools import (
    CompareFile,
    CompareSnapshot,
    parse_branch,
    parse_commit_detail,
    parse_commit_summary,
    parse_compare,
    parse_created_branch,
)
from gitdock.services.git_tools import CompareView
from gitdock.services.repositories import RepositoryFilter
from gitdock.telegram import git_callbacks
from gitdock.telegram.renderers.git_tools import render_compare


def test_parse_branch_and_created_ref() -> None:
    branch = parse_branch({"name": "feature/x", "protected": False, "commit": {"sha": "a" * 40}})
    assert branch.name == "feature/x"
    assert branch.sha == "a" * 40
    created = parse_created_branch(
        {"ref": "refs/heads/feature/x", "object": {"sha": "b" * 40}},
        expected_branch="feature/x",
    )
    assert created.name == "feature/x"
    assert created.sha == "b" * 40


def test_commit_parsers_and_compare() -> None:
    payload = {
        "sha": "c" * 40,
        "html_url": "https://github.com/ahmed9461/GitDock/commit/" + "c" * 40,
        "commit": {
            "message": "feat: test\n\nbody",
            "author": {"name": "Ahmed", "date": "2026-09-11T20:00:00Z"},
        },
        "parents": [{"sha": "d" * 40}],
        "stats": {"additions": 4, "deletions": 2},
        "files": [{"filename": "a.py"}, {"filename": "b.py"}],
    }
    summary = parse_commit_summary(payload)
    detail = parse_commit_detail(payload)
    assert summary.authored_at.tzinfo is UTC
    assert detail.changed_files == 2
    assert detail.parents == ("d" * 40,)

    comparison = parse_compare(
        {
            "status": "ahead",
            "ahead_by": 2,
            "behind_by": 0,
            "total_commits": 2,
            "files": [
                {
                    "filename": "a.py",
                    "status": "modified",
                    "additions": 4,
                    "deletions": 1,
                    "changes": 5,
                }
            ],
        }
    )
    assert comparison.ahead_by == 2
    assert comparison.files[0].changes == 5


def test_large_compare_summary_is_bounded() -> None:
    files = tuple(
        CompareFile(
            filename=f"file-{index:02d}.py",
            status="modified",
            additions=1,
            deletions=1,
            changes=2,
        )
        for index in range(15)
    )
    text = render_compare(
        CompareView(
            repository_full_name="ahmed9461/GitDock",
            base="main",
            head="feature/x",
            comparison=CompareSnapshot(
                status="ahead",
                ahead_by=15,
                behind_by=0,
                total_commits=15,
                files=files,
            ),
        )
    )
    assert "Files: 15" in text
    assert text.count("\n• ") == 10
    assert "file-09.py" in text
    assert "file-10.py" not in text


def test_branch_parser_rejects_invalid_sha() -> None:
    with pytest.raises(ValueError):
        parse_branch({"name": "main", "protected": False, "commit": {"sha": "short"}})


def test_git_callbacks_are_compact_and_round_trip() -> None:
    data = git_callbacks.branches_open(1351822221, RepositoryFilter.ALL, 3)
    assert len(data.encode()) < 64
    assert git_callbacks.parse_repo_open(data, "b") == (
        1351822221,
        RepositoryFilter.ALL,
        3,
    )
    item = git_callbacks.item("c", 2, 9)
    assert len(item.encode()) < 64
    assert git_callbacks.parse_item(item, "c") == (2, 9)
