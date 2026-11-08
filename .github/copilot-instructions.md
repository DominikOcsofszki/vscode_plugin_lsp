# Copilot instructions for this repository

## Build, test, and lint

Use `uv` for Python dependency management and tests, and npm for the VS Code extension:

- Install dependencies:
  - `npm install`
  - `cp .env.example .env`
  - `uv sync --group build --group test --group lint`
- TypeScript build:
  - `npm run compile`
  - `npm run watch` for incremental rebuilds
- TypeScript lint:
  - `npm run lint`
- Combined checks and Python test suite:
  - `npm test`
- Python test suite:
  - Build the selected server dependency bundle: `npm run python:bundle`
  - Full suite: `uv run --group test pytest src/test/python_tests`
  - Single file: `uv run --group test pytest src/test/python_tests/test_server.py -q`
  - Single test: `uv run --group test pytest src/test/python_tests/test_server.py::test_completion_suggestions -q`
- Python linting/format checks:
  - `uv run --group lint pylint -d W0511 --init-hook='import sys; sys.path[:0] = ["bundled/tool", "bundled/libs"]' --ignore=src/test/python_tests/test_data bundled/tool src/test/python_tests scripts/build_bundle.py`
  - `uv run --group lint black --check bundled/tool src/test/python_tests scripts`
  - `uv run --group lint isort --check bundled/tool src/test/python_tests scripts`
- Package the VSIX:
  - `npm run vsce-package`

The pytest suite covers the optional Python adapter. The TypeScript extension can also launch an external LSP executable directly, without the Python extension or a Python runtime at server runtime.

## High-level architecture

This repository is a VS Code LSP host with two launch modes: a Python module adapter or a configured external command.

- `src/` contains the TypeScript host extension:
  - `src/extension.ts` is the extension entry point; it initializes logging and starts/stops the LSP client, using Python APIs only in Python mode when the Python extension is available.
  - `src/common/server.ts` creates the `vscode-languageclient` session and launches either the configured command or the Python adapter.
  - `src/common/settings.ts` reads `jsqlsp.*` settings from workspace and global config, resolves `${workspaceFolder}` and similar variables, and determines whether config changes should trigger a restart.
  - `src/common/python.ts` wraps optional Python extension APIs (`@vscode/python-extension` and `@vscode/python-environments`) for Python mode.
- `bundled/tool/` contains the Python-mode adapter; command mode launches the configured LSP executable directly and does not use this adapter.
  - `bundled/tool/lsp_server.py` is the main entrypoint for the Python side and is the place to inspect how the language server is wired to `pygls` and the bundled dependencies.
  - `bundled/tool/lsp_runner.py` and helpers in the same folder provide the execution path for the LSP process. `lsp_bootstrap.py` adds the bundled library directory before server dependencies are imported.
- `.env` selects `LSP_MODE`, language IDs, and either a Python package/import entry point or an executable and arguments. `scripts/lsp_settings.py` validates it; `scripts/configure_lsp.py` generates runtime config and extension metadata; `scripts/build_bundle.py` bundles Python dependencies only in Python mode.
- `bundled/my_dist/` holds the default local example wheel. Other Python distributions can be selected in `.env`, provided they expose a compatible pygls server object.
- `bundled/libs/` is generated Python runtime code used only in Python mode; command mode excludes these dependencies from the VSIX.
- `dist/` is the compiled extension output; do not hand-edit it unless intentionally regenerating build artifacts.

The extension is a thin host: VS Code -> TypeScript language client -> configured LSP process -> language features. The LSP implementation may use any runtime in command mode; Python-specific behavior is isolated to Python mode and `bundled/tool/`.

## Key conventions

- Settings are namespaced under the generated `LSP_ID` in `package.json`; the config keys are the contract between the extension and the user. When changing setting behavior, update both the schema in `package.json` and the logic in `src/common/settings.ts`.
- Python interpreter discovery is optional and used only in Python mode. It prefers the Python Environments API and then falls back to the legacy Python extension API.
- The repo is organized as a template for a Python LSP extension. Several comments in `bundled/tool/lsp_server.py` and `package.json` still refer to template placeholders like `TODO: Update...`. Treat those as real customization points when adapting the project, and update the generated metadata before shipping.
- Build and packaging are split between Node (`npm run compile`, `webpack`, `vsce`) and Python (`uv`, `bundled/libs`). Python configuration comes from `.env` at build time; the VSIX contains generated config and dependencies, not `.env`.
- The active Python test suite lives under `src/test/python_tests/` and exercises server behavior via `pytest`, not a broad TS test harness; prefer those tests for LSP-specific regression coverage.
- `test_server.py` covers the current completion feature from the bundled server. Do not retain template expectations for Pylint diagnostics or Black formatting unless those tools are actually configured as runtime features.

## Repository-specific notes

- `README.md` documents the repository setup and environment-driven language server configuration.
- `pyproject.toml` and `uv.lock` define adapter, test, build, and lint dependencies. The selected LSP package is resolved from `.env` when `scripts/build_bundle.py` creates the runtime bundle.
- Activation events and document selectors are generated from `LSP_LANGUAGE_IDS`; notebook activation remains available. The `ms-python.python` extension is optional and is not required in command mode.
