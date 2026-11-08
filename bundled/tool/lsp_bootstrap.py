"""Initialize bundled library paths before importing server dependencies."""

import json
import os
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent


def update_sys_path(strategy: str) -> None:
    """Add bundled libraries before or after site packages as configured."""
    libraries_path = os.fspath(TOOL_DIR.parent / "libs")
    if libraries_path in sys.path or not os.path.isdir(libraries_path):
        return

    if strategy == "useBundled":
        sys.path.insert(0, libraries_path)
    elif strategy == "fromEnvironment":
        sys.path.append(libraries_path)


def load_server_config() -> dict[str, object]:
    """Load generated package/import settings, failing with setup guidance."""
    config_path = TOOL_DIR / "lsp_config.json"
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(
            "Language server configuration is missing; run "
            "'npm run python:configure' before starting the server."
        ) from error
