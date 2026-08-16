#!/usr/bin/env python3

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

CommandRunner = Callable[[Sequence[str], Path], None]


@dataclass(frozen=True)
class Command:
    arguments: tuple[str, ...]
    working_directory: Path


def run_command(arguments: Sequence[str], working_directory: Path) -> None:
    subprocess.run(arguments, cwd=working_directory, check=True)


@dataclass(frozen=True)
class ProjectTasks:
    repository_root: Path
    runner: CommandRunner = run_command

    def run(self, task_name: str) -> None:
        for command in self.commands_for(task_name):
            self.runner(command.arguments, command.working_directory)

    def commands_for(self, task_name: str) -> tuple[Command, ...]:
        frontend = self.repository_root / "frontend"
        backend = self.repository_root / "backend"
        infra = self.repository_root / "infra"
        python = sys.executable

        task_commands: dict[str, tuple[Command, ...]] = {
            "frontend-install": (Command(("npm", "ci"), frontend),),
            "backend-install": (Command(("uv", "sync"), backend),),
            "infra-install": (Command(("uv", "sync"), infra),),
            "test-frontend": (Command(("npm", "test", "--", "--watch=false"), frontend),),
            "test-backend": (
                Command(("uv", "run", "pytest"), backend),
                Command(("uv", "run", "ruff", "check", "."), backend),
                Command(("uv", "run", "ruff", "format", "--check", "."), backend),
            ),
            "test-infra": (
                Command(("uv", "run", "pytest"), infra),
                Command(("uv", "run", "ruff", "check", "."), infra),
                Command(("uv", "run", "ruff", "format", "--check", "."), infra),
            ),
            "build-frontend": (Command(("npm", "run", "build"), frontend),),
            "package-backend": (
                Command((python, "scripts/package_lambda.py"), self.repository_root),
            ),
            "frontend-dev": (Command(("npm", "start"), frontend),),
            "backend-dev": (
                Command(
                    ("uv", "run", "uvicorn", "site_api.main:app", "--reload"),
                    backend,
                ),
            ),
        }
        task_commands["setup"] = (
            *task_commands["frontend-install"],
            *task_commands["backend-install"],
            *task_commands["infra-install"],
        )
        task_commands["test"] = (
            *task_commands["test-frontend"],
            *task_commands["test-backend"],
            *task_commands["test-infra"],
        )
        task_commands["build"] = (
            *task_commands["build-frontend"],
            *task_commands["package-backend"],
        )

        try:
            return task_commands[task_name]
        except KeyError as error:
            raise ValueError(f"Unknown project task: {task_name}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Your Company Name project tasks")
    parser.add_argument(
        "task",
        choices=(
            "setup",
            "frontend-install",
            "backend-install",
            "infra-install",
            "test",
            "test-frontend",
            "test-backend",
            "test-infra",
            "build",
            "build-frontend",
            "package-backend",
            "frontend-dev",
            "backend-dev",
        ),
    )
    arguments = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    ProjectTasks(repository_root).run(arguments.task)


if __name__ == "__main__":
    main()
