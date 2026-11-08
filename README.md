# Configurable VS Code Language Server Extension

A VS Code extension host for Language Server Protocol (LSP) servers. Configure it to launch either a Python module or an existing executable; set the target VS Code language IDs in `.env`.

The LSP protocol is language-agnostic. Python is only needed when the selected server is launched as a Python module.

## Requirements

- VS Code 1.78 or later
- Node.js and npm
- [uv](https://docs.astral.sh/uv/)
- Python 3.12 or later when using Python launch mode
- The Microsoft Python extension (`ms-python.python`) is optional and provides interpreter discovery in Python mode

## Get started

Install the JavaScript and Python development dependencies:

```sh
npm ci
cp .env.example .env
uv sync --group build --group test --group lint
```

The example `.env` uses Python launch mode. Select the Python distribution (a local `.whl` path or a pinned PEP 508 requirement) and its server import entry point:

```dotenv
LSP_PACKAGE=path/to/your_lsp.whl
LSP_IMPORT_MODULE=your_lsp.main
LSP_SERVER_ATTRIBUTE=server
LSP_RUN_MODULE=your_lsp
LSP_ID=jsqlsp
LSP_NAME=Python Language Server
```

`LSP_IMPORT_MODULE` and `LSP_SERVER_ATTRIBUTE` must identify a Python object implementing a compatible `pygls` server with `start_io()`. `LSP_RUN_MODULE` is used by the Python adapter's tool execution helpers. `LSP_PYTHON_COMMAND` is the fallback interpreter when the Python extension is not installed; it must meet the selected server's requirements.

To launch a server executable instead, configure command mode:

```dotenv
LSP_MODE=command
LSP_COMMAND=path/to/language-server
LSP_COMMAND_ARGS=["--stdio"]
LSP_LANGUAGE_IDS=rust
LSP_ID=rustls
LSP_NAME=Rust Language Server
```

In command mode, the executable is started directly over stdio; no Python runtime or Python extension is needed to run the server. `LSP_COMMAND` can be a path or a command available on `PATH`. `LSP_COMMAND_ARGS` is a JSON string array. `LSP_LANGUAGE_IDS` is a comma-separated list of VS Code language IDs handled by the server. The VS Code activation events and document selectors are generated from these IDs.

For both modes, `LSP_ID` becomes the VS Code settings and restart-command namespace, and `LSP_NAME` is the displayed server name. The generated runtime configuration and extension metadata use the same `.env` values. `.env` is ignored by git and excluded from the VSIX; `.env.example` contains the Python-mode defaults and a commented command-mode example.

To generate config without building the dependency bundle:

```sh
npm run python:configure
```

Build the extension and run its checks:

```sh
npm run compile
npm run lint
npm test
```

`npm test` compiles and lints the extension and builds Python runtime dependencies when Python mode is selected. It runs the Python adapter test suite in Python mode and skips that suite in command mode.

To run Python tests directly, build the runtime bundle first:

```sh
npm run python:bundle
uv run --group test pytest src/test/python_tests
```

Run one test file or one test:

```sh
uv run --group test pytest src/test/python_tests/test_server.py -q
uv run --group test pytest src/test/python_tests/test_server.py::test_completion_suggestions -q
```

Run the Python lint and formatting checks:

```sh
uv run --group lint pylint -d W0511 --init-hook='import sys; sys.path[:0] = ["bundled/tool", "bundled/libs"]' --ignore=src/test/python_tests/test_data bundled/tool src/test/python_tests scripts/build_bundle.py
uv run --group lint black --check bundled/tool src/test/python_tests scripts
uv run --group lint isort --check bundled/tool src/test/python_tests scripts
```

Package the extension as a VSIX:

```sh
npm run vsce-package
```

The VSIX prepublish hook generates server and extension metadata from `.env`, compiles the TypeScript extension, and—only in Python mode—resolves the selected Python package and dependencies into `bundled/libs`. Use an exact package version or a specific local wheel path to keep package selection stable. The lockfile covers the Python adapter's own dependencies; the selected Python LSP package is resolved when the bundle is built.

## Extension settings

Settings use the namespace selected by `LSP_ID` and are declared in [`package.json`](./package.json).

| Setting | Purpose |
| --- | --- |
| `jsqlsp.cwd` | Working directory for the server; supports `${workspaceFolder}` and `${fileDirname}`. |
| `jsqlsp.args` | Additional server/tool arguments. |
| `jsqlsp.path` | Optional executable path; takes precedence over the import strategy. |
| `jsqlsp.importStrategy` | Python mode only: `useBundled` prefers packaged Python dependencies; `fromEnvironment` prefers dependencies available in the selected environment. |
| `jsqlsp.interpreter` | Python mode only: optional Python executable path used to launch the server. |
| `jsqlsp.showNotifications` | Controls server notifications: `off`, `onError`, `onWarning`, or `always`. |

In Python mode, the extension uses the Python Environments API when available, falling back to the Python extension API. Without the Python extension, it uses `LSP_PYTHON_COMMAND` or the `interpreter` setting. The selected Python runtime must satisfy the server package's requirements.

## Build layout

- [`src/`](./src/) contains the VS Code extension host and language-client integration.
- [`bundled/tool/`](./bundled/tool/) contains the optional Python language-server adapter and process helpers.
- [`bundled/my_dist/`](./bundled/my_dist/) contains the default local Python example wheel; `.env` can instead select a registry package requirement or another wheel. Command mode does not use this package.
- [`bundled/libs/`](./bundled/libs/) is generated from the selected Python runtime dependencies for VSIX packaging; do not edit it directly.
- [`src/test/python_tests/`](./src/test/python_tests/) contains LSP integration and Python helper tests.
- [`pyproject.toml`](./pyproject.toml) and [`uv.lock`](./uv.lock) define and lock adapter, test, build, and lint dependencies. [`scripts/lsp_settings.py`](./scripts/lsp_settings.py) validates `.env`; [`scripts/configure_lsp.py`](./scripts/configure_lsp.py) generates metadata; [`scripts/build_bundle.py`](./scripts/build_bundle.py) resolves and installs the selected server and its dependencies into `bundled/libs/`.
- [`package.json`](./package.json) and [`package-lock.json`](./package-lock.json) manage the TypeScript build, lint, and VS Code packaging toolchain.

## Python dependency setup benchmark

On the development machine, a setup-only benchmark compared three fresh Python test environments using the pre-uv Nox workflow from the repository's initial commit and the current uv workflow. Dependency download caches were warm, and the Nox runner was already available. The old Nox test session was measured with its test execution replaced by a no-op so the comparison focuses on environment setup.

| Workflow | Median setup time |
| --- | ---: |
| Nox + pip installing the test requirements | 2.21 s |
| `uv sync --only-group test --no-install-project` | 0.03 s |

In this local benchmark, uv setup took about **2.18 seconds less** (approximately **98.7% lower setup time**, or **74× faster**). Results depend on the machine, cache state, and package registry; this measures Python test-environment setup, not the TypeScript build, runtime bundling, or complete VSIX packaging.