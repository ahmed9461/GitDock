"""Pure P4.3 project-evidence inference and command generation."""

from __future__ import annotations

import json
import re
import shlex
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from typing import cast
from urllib.parse import quote


class TargetOS(StrEnum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StackKind(StrEnum):
    PYTHON = "Python"
    NODE = "Node.js"
    DOCKER = "Docker"
    GRADLE = "Gradle"
    MAVEN = "Maven"


class SuggestionPurpose(StrEnum):
    SETUP = "setup"
    RUN = "run"


class PlanNote(StrEnum):
    README_PRESENT = "readme_present"
    REPOSITORY_DEFINED_COMMAND = "repository_defined_command"
    DOCKER_RUNTIME_OPTIONS = "docker_runtime_options"
    NO_STACK_EVIDENCE = "no_stack_evidence"
    NO_RUN_COMMAND = "no_run_command"


@dataclass(frozen=True, slots=True)
class EvidenceFile:
    path: str
    content: bytes | None = None


@dataclass(frozen=True, slots=True)
class StackEvidence:
    stack: StackKind
    sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommandSuggestion:
    stack: StackKind
    purpose: SuggestionPurpose
    commands: tuple[str, ...]
    confidence: Confidence
    sources: tuple[str, ...]
    note: PlanNote | None = None


@dataclass(frozen=True, slots=True)
class CommandPlan:
    repository_full_name: str
    default_branch: str
    target_os: TargetOS
    clone_fresh: tuple[str, ...]
    update_existing: tuple[str, ...]
    stacks: tuple[StackEvidence, ...]
    setup: tuple[CommandSuggestion, ...]
    run: tuple[CommandSuggestion, ...]
    notes: tuple[PlanNote, ...]


_COMMAND_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_SAFE_IMAGE_RE = re.compile(r"[^a-z0-9_.-]+")

_PYTHON_FILES = ("pyproject.toml", "requirements.txt", "poetry.lock", "pipfile")
_NODE_FILES = ("package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock")
_DOCKER_FILES = (
    "dockerfile",
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
)
_GRADLE_FILES = ("build.gradle", "build.gradle.kts", "gradlew", "gradlew.bat")
_MAVEN_FILES = ("pom.xml", "mvnw", "mvnw.cmd")
_README_FILES = ("readme.md", "readme.rst", "readme.txt", "readme")


def build_command_plan(
    *,
    owner_login: str,
    repository_name: str,
    default_branch: str,
    target_os: TargetOS,
    evidence: tuple[EvidenceFile, ...],
) -> CommandPlan:
    """Build safe copyable commands from bounded repository evidence."""

    owner = _require_segment(owner_login, "owner")
    repository = _require_segment(repository_name, "repository")
    branch = _require_ref(default_branch)
    selected_os = TargetOS(target_os)
    by_name = _evidence_map(evidence)

    stacks = _detect_stacks(by_name)
    setup: list[CommandSuggestion] = []
    run: list[CommandSuggestion] = []
    notes: list[PlanNote] = []

    if StackKind.PYTHON in {item.stack for item in stacks}:
        python_setup, python_run = _python_suggestions(by_name, selected_os, repository)
        setup.append(python_setup)
        if python_run is not None:
            run.append(python_run)
            notes.append(PlanNote.REPOSITORY_DEFINED_COMMAND)

    if StackKind.NODE in {item.stack for item in stacks}:
        node_setup, node_run = _node_suggestions(by_name, selected_os, repository)
        setup.append(node_setup)
        if node_run is not None:
            run.append(node_run)
            notes.append(PlanNote.REPOSITORY_DEFINED_COMMAND)

    if StackKind.DOCKER in {item.stack for item in stacks}:
        docker_setup, docker_run = _docker_suggestions(by_name, selected_os, repository)
        if docker_setup is not None:
            setup.append(docker_setup)
        if docker_run is not None:
            run.append(docker_run)
            if docker_run.note is PlanNote.DOCKER_RUNTIME_OPTIONS:
                notes.append(PlanNote.DOCKER_RUNTIME_OPTIONS)

    if StackKind.GRADLE in {item.stack for item in stacks}:
        gradle_setup, gradle_run = _gradle_suggestions(by_name, selected_os, repository)
        setup.append(gradle_setup)
        if gradle_run is not None:
            run.append(gradle_run)

    if StackKind.MAVEN in {item.stack for item in stacks}:
        maven_setup, maven_run = _maven_suggestions(by_name, selected_os, repository)
        setup.append(maven_setup)
        if maven_run is not None:
            run.append(maven_run)

    if any(name in by_name for name in _README_FILES):
        notes.append(PlanNote.README_PRESENT)
    if not stacks:
        notes.append(PlanNote.NO_STACK_EVIDENCE)
    if not run:
        notes.append(PlanNote.NO_RUN_COMMAND)

    clone_url = _clone_url(owner, repository)
    directory = _quote(repository, selected_os)
    branch_arg = _quote(branch, selected_os)
    workdir = _workdir_command(repository, selected_os)

    return CommandPlan(
        repository_full_name=f"{owner}/{repository}",
        default_branch=branch,
        target_os=selected_os,
        clone_fresh=(
            f"git clone {_quote(clone_url, selected_os)} {directory}",
            workdir,
        ),
        update_existing=(
            workdir,
            "git fetch origin --prune",
            f"git switch -- {branch_arg}",
            f"git pull --ff-only origin {branch_arg}",
        ),
        stacks=stacks,
        setup=tuple(setup),
        run=tuple(run),
        notes=_unique_notes(notes),
    )


def _detect_stacks(by_name: dict[str, EvidenceFile]) -> tuple[StackEvidence, ...]:
    detected: list[StackEvidence] = []
    for stack, candidates in (
        (StackKind.PYTHON, _PYTHON_FILES),
        (StackKind.NODE, _NODE_FILES),
        (StackKind.DOCKER, _DOCKER_FILES),
        (StackKind.GRADLE, _GRADLE_FILES),
        (StackKind.MAVEN, _MAVEN_FILES),
    ):
        sources = tuple(by_name[name].path for name in candidates if name in by_name)
        if sources:
            detected.append(StackEvidence(stack=stack, sources=sources))
    return tuple(detected)


def _python_suggestions(
    by_name: dict[str, EvidenceFile],
    target_os: TargetOS,
    repository: str,
) -> tuple[CommandSuggestion, CommandSuggestion | None]:
    sources = tuple(by_name[name].path for name in _PYTHON_FILES if name in by_name)
    commands = [_workdir_command(repository, target_os), "python -m venv .venv"]
    commands.append(_activate_venv(target_os))
    if "requirements.txt" in by_name:
        commands.append("python -m pip install -r requirements.txt")
    if "pyproject.toml" in by_name:
        commands.append("python -m pip install -e .")
    setup = CommandSuggestion(
        stack=StackKind.PYTHON,
        purpose=SuggestionPurpose.SETUP,
        commands=tuple(commands),
        confidence=Confidence.HIGH,
        sources=sources,
    )

    scripts = _pyproject_scripts(by_name.get("pyproject.toml"))
    if not scripts:
        return setup, None
    command_name = scripts[0]
    run = CommandSuggestion(
        stack=StackKind.PYTHON,
        purpose=SuggestionPurpose.RUN,
        commands=(
            _workdir_command(repository, target_os),
            _activate_venv(target_os),
            _command_name(command_name),
        ),
        confidence=Confidence.HIGH,
        sources=(by_name["pyproject.toml"].path,),
        note=PlanNote.REPOSITORY_DEFINED_COMMAND,
    )
    return setup, run


def _node_suggestions(
    by_name: dict[str, EvidenceFile],
    target_os: TargetOS,
    repository: str,
) -> tuple[CommandSuggestion, CommandSuggestion | None]:
    sources = tuple(by_name[name].path for name in _NODE_FILES if name in by_name)
    manager, install_command = _node_package_manager(by_name)
    setup = CommandSuggestion(
        stack=StackKind.NODE,
        purpose=SuggestionPurpose.SETUP,
        commands=(_workdir_command(repository, target_os), install_command),
        confidence=Confidence.HIGH,
        sources=sources,
    )
    scripts = _package_scripts(by_name.get("package.json"))
    selected = next((name for name in ("start", "dev", "serve") if name in scripts), None)
    if selected is None:
        return setup, None
    run = CommandSuggestion(
        stack=StackKind.NODE,
        purpose=SuggestionPurpose.RUN,
        commands=(
            _workdir_command(repository, target_os),
            f"{manager} run {selected}",
        ),
        confidence=Confidence.HIGH,
        sources=(by_name["package.json"].path,),
        note=PlanNote.REPOSITORY_DEFINED_COMMAND,
    )
    return setup, run


def _docker_suggestions(
    by_name: dict[str, EvidenceFile],
    target_os: TargetOS,
    repository: str,
) -> tuple[CommandSuggestion | None, CommandSuggestion | None]:
    compose = next((name for name in _DOCKER_FILES[1:] if name in by_name), None)
    if compose is not None:
        source = by_name[compose].path
        return (
            None,
            CommandSuggestion(
                stack=StackKind.DOCKER,
                purpose=SuggestionPurpose.RUN,
                commands=(
                    _workdir_command(repository, target_os),
                    "docker compose up --build",
                ),
                confidence=Confidence.HIGH,
                sources=(source,),
            ),
        )
    dockerfile = by_name.get("dockerfile")
    if dockerfile is None:
        return None, None
    image = _image_tag(repository)
    setup = CommandSuggestion(
        stack=StackKind.DOCKER,
        purpose=SuggestionPurpose.SETUP,
        commands=(
            _workdir_command(repository, target_os),
            f"docker build -t {image} .",
        ),
        confidence=Confidence.HIGH,
        sources=(dockerfile.path,),
    )
    run = CommandSuggestion(
        stack=StackKind.DOCKER,
        purpose=SuggestionPurpose.RUN,
        commands=(f"docker run --rm {image}",),
        confidence=Confidence.LOW,
        sources=(dockerfile.path,),
        note=PlanNote.DOCKER_RUNTIME_OPTIONS,
    )
    return setup, run


def _gradle_suggestions(
    by_name: dict[str, EvidenceFile],
    target_os: TargetOS,
    repository: str,
) -> tuple[CommandSuggestion, CommandSuggestion | None]:
    build_name = "build.gradle.kts" if "build.gradle.kts" in by_name else "build.gradle"
    sources = tuple(by_name[name].path for name in _GRADLE_FILES if name in by_name)
    executable = _gradle_executable(by_name, target_os)
    setup = CommandSuggestion(
        stack=StackKind.GRADLE,
        purpose=SuggestionPurpose.SETUP,
        commands=(
            _workdir_command(repository, target_os),
            f"{executable} build",
        ),
        confidence=Confidence.HIGH,
        sources=sources,
    )
    build_file = by_name.get(build_name)
    if build_file is None or not _gradle_has_application_plugin(build_file):
        return setup, None
    return (
        setup,
        CommandSuggestion(
            stack=StackKind.GRADLE,
            purpose=SuggestionPurpose.RUN,
            commands=(
                _workdir_command(repository, target_os),
                f"{executable} run",
            ),
            confidence=Confidence.MEDIUM,
            sources=(build_file.path,),
        ),
    )


def _maven_suggestions(
    by_name: dict[str, EvidenceFile],
    target_os: TargetOS,
    repository: str,
) -> tuple[CommandSuggestion, CommandSuggestion | None]:
    sources = tuple(by_name[name].path for name in _MAVEN_FILES if name in by_name)
    executable = _maven_executable(by_name, target_os)
    setup = CommandSuggestion(
        stack=StackKind.MAVEN,
        purpose=SuggestionPurpose.SETUP,
        commands=(
            _workdir_command(repository, target_os),
            f"{executable} package",
        ),
        confidence=Confidence.HIGH,
        sources=sources,
    )
    pom = by_name.get("pom.xml")
    if pom is None or not _content_contains(pom, "spring-boot-maven-plugin"):
        return setup, None
    return (
        setup,
        CommandSuggestion(
            stack=StackKind.MAVEN,
            purpose=SuggestionPurpose.RUN,
            commands=(
                _workdir_command(repository, target_os),
                f"{executable} spring-boot:run",
            ),
            confidence=Confidence.MEDIUM,
            sources=(pom.path,),
        ),
    )


def _node_package_manager(by_name: dict[str, EvidenceFile]) -> tuple[str, str]:
    if "pnpm-lock.yaml" in by_name:
        return "pnpm", "pnpm install --frozen-lockfile"
    if "yarn.lock" in by_name:
        return "yarn", "yarn install --frozen-lockfile"
    if "package-lock.json" in by_name:
        return "npm", "npm ci"
    return "npm", "npm install"


def _gradle_executable(by_name: dict[str, EvidenceFile], target_os: TargetOS) -> str:
    if target_os is TargetOS.WINDOWS and "gradlew.bat" in by_name:
        return r".\gradlew.bat"
    if target_os is not TargetOS.WINDOWS and "gradlew" in by_name:
        return "./gradlew"
    return "gradle"


def _maven_executable(by_name: dict[str, EvidenceFile], target_os: TargetOS) -> str:
    if target_os is TargetOS.WINDOWS and "mvnw.cmd" in by_name:
        return r".\mvnw.cmd"
    if target_os is not TargetOS.WINDOWS and "mvnw" in by_name:
        return "./mvnw"
    return "mvn"


def _pyproject_scripts(entry: EvidenceFile | None) -> tuple[str, ...]:
    if entry is None or entry.content is None:
        return ()
    try:
        raw = tomllib.loads(entry.content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return ()
    project_raw = raw.get("project")
    if not isinstance(project_raw, dict):
        return ()
    project = cast(dict[str, object], project_raw)
    scripts_raw = project.get("scripts")
    if not isinstance(scripts_raw, dict):
        return ()
    scripts = cast(dict[object, object], scripts_raw)
    return tuple(
        sorted(
            key
            for key, value in scripts.items()
            if isinstance(key, str)
            and isinstance(value, str)
            and _COMMAND_NAME_RE.fullmatch(key) is not None
        )
    )


def _package_scripts(entry: EvidenceFile | None) -> frozenset[str]:
    if entry is None or entry.content is None:
        return frozenset()
    try:
        raw: object = json.loads(entry.content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return frozenset()
    if not isinstance(raw, dict):
        return frozenset()
    data = cast(dict[str, object], raw)
    scripts_raw = data.get("scripts")
    if not isinstance(scripts_raw, dict):
        return frozenset()
    scripts = cast(dict[object, object], scripts_raw)
    return frozenset(
        key for key, value in scripts.items() if isinstance(key, str) and isinstance(value, str)
    )


def _gradle_has_application_plugin(entry: EvidenceFile) -> bool:
    if entry.content is None:
        return False
    try:
        text = entry.content.decode("utf-8").casefold()
    except UnicodeDecodeError:
        return False
    return any(
        marker in text
        for marker in (
            'id("application")',
            "id 'application'",
            "apply plugin: 'application'",
            "\napplication\n",
        )
    )


def _content_contains(entry: EvidenceFile, needle: str) -> bool:
    if entry.content is None:
        return False
    try:
        return needle.casefold() in entry.content.decode("utf-8").casefold()
    except UnicodeDecodeError:
        return False


def _evidence_map(evidence: tuple[EvidenceFile, ...]) -> dict[str, EvidenceFile]:
    result: dict[str, EvidenceFile] = {}
    for entry in evidence:
        name = entry.path.rsplit("/", 1)[-1].casefold()
        if name and name not in result:
            result[name] = entry
    return result


def _workdir_command(repository: str, target_os: TargetOS) -> str:
    quoted = _quote(repository, target_os)
    if target_os is TargetOS.WINDOWS:
        return f"Set-Location {quoted}"
    return f"cd {quoted}"


def _activate_venv(target_os: TargetOS) -> str:
    if target_os is TargetOS.WINDOWS:
        return r".\.venv\Scripts\Activate.ps1"
    return "source .venv/bin/activate"


def _command_name(value: str) -> str:
    if _COMMAND_NAME_RE.fullmatch(value) is None:
        raise ValueError("repository command name is invalid")
    return value


def _quote(value: str, target_os: TargetOS) -> str:
    if target_os is TargetOS.WINDOWS:
        return "'" + value.replace("'", "''") + "'"
    return shlex.quote(value)


def _clone_url(owner: str, repository: str) -> str:
    owner_part = quote(owner, safe="-._")
    repository_part = quote(repository, safe="-._")
    return f"https://github.com/{owner_part}/{repository_part}.git"


def _image_tag(repository: str) -> str:
    normalized = _SAFE_IMAGE_RE.sub("-", repository.casefold()).strip("-._")
    return normalized[:80] or "gitdock-project"


def _require_segment(value: str, label: str) -> str:
    stripped = value.strip()
    if not stripped or "/" in stripped or "\\" in stripped or "\x00" in stripped:
        raise ValueError(f"invalid {label} segment")
    return stripped


def _require_ref(value: str) -> str:
    stripped = value.strip()
    if not stripped or any(character in stripped for character in ("\x00", "\n", "\r")):
        raise ValueError("invalid default branch")
    return stripped


def _unique_notes(notes: list[PlanNote]) -> tuple[PlanNote, ...]:
    return tuple(dict.fromkeys(notes))
