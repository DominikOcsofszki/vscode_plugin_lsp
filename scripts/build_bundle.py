"""Build selected LSP and adapter dependencies into the extension bundle."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from configure_lsp import configure
from lsp_settings import ROOT, load_settings


def main() -> None:
    """Resolve the configured package and install its locked dependency set."""
    settings = load_settings()
    configure()
    if settings.mode == "command":
        target = ROOT / "bundled" / "libs"
        if target.exists():
            shutil.rmtree(target)
        return

    target = ROOT / "bundled" / "libs"
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)
        base_requirements = temporary_path / "adapter-requirements.txt"
        input_requirements = temporary_path / "lsp-requirements.in"
        locked_requirements = temporary_path / "lsp-requirements.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements-txt",
                "--output-file",
                str(base_requirements),
            ],
            cwd=ROOT,
            check=True,
        )
        input_requirements.write_text(
            f"-r {base_requirements}\n{settings.package}\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "uv",
                "pip",
                "compile",
                "--python-version",
                "3.12",
                "--generate-hashes",
                "--output-file",
                str(locked_requirements),
                str(input_requirements),
            ],
            cwd=ROOT,
            check=True,
        )
        if target.exists():
            shutil.rmtree(target)
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--target",
                str(target),
                "--no-deps",
                "--upgrade",
                "--requirement",
                str(locked_requirements),
            ],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    main()
