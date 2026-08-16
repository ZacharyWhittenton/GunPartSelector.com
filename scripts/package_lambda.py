#!/usr/bin/env python3

import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

CommandRunner = Callable[[Sequence[str], Path], None]


def run_command(command: Sequence[str], working_directory: Path) -> None:
    subprocess.run(command, cwd=working_directory, check=True)


@dataclass(frozen=True)
class LambdaPackager:
    repository_root: Path
    runner: CommandRunner = run_command

    def build(self) -> Path:
        backend_directory = self.repository_root / "backend"
        distribution_directory = backend_directory / "dist"
        staging_directory = distribution_directory / "lambda"
        requirements_path = distribution_directory / "lambda-requirements.txt"
        archive_path = distribution_directory / "lambda.zip"

        distribution_directory.mkdir(parents=True, exist_ok=True)
        if staging_directory.exists():
            shutil.rmtree(staging_directory)
        if archive_path.exists():
            archive_path.unlink()
        staging_directory.mkdir()

        self.runner(
            (
                "uv",
                "export",
                "--quiet",
                "--frozen",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements.txt",
                "--output-file",
                str(requirements_path),
            ),
            backend_directory,
        )
        self.runner(
            (
                "uv",
                "pip",
                "install",
                "--target",
                str(staging_directory),
                "--python-version",
                "3.14",
                "--python-platform",
                "aarch64-manylinux_2_28",
                "--only-binary",
                ":all:",
                "--requirements",
                str(requirements_path),
            ),
            backend_directory,
        )

        shutil.copytree(
            backend_directory / "src" / "site_api",
            staging_directory / "site_api",
        )
        self._create_archive(staging_directory, archive_path)
        return archive_path

    @staticmethod
    def _create_archive(staging_directory: Path, archive_path: Path) -> None:
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(staging_directory.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    archive.write(path, path.relative_to(staging_directory))


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    archive_path = LambdaPackager(repository_root).build()
    size_megabytes = archive_path.stat().st_size / (1024 * 1024)
    print(f"Created {archive_path} ({size_megabytes:.1f} MiB)")


if __name__ == "__main__":
    main()
