"""Run tests for the optional Python LSP adapter."""

import subprocess
import sys

from lsp_settings import ROOT, load_settings


def main() -> None:
    """Run adapter tests only when the Python launch mode is selected."""
    settings = load_settings()
    if settings.mode == "command":
        print("Skipping Python adapter tests because LSP_MODE=command.")
        return

    subprocess.run(
        [sys.executable, "-m", "pytest", "src/test/python_tests"],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
