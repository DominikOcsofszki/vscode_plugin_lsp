"""Generate runtime and extension metadata from the selected LSP configuration."""

import json
from typing import Any

from lsp_settings import ROOT, LspSettings, load_settings


def _replace_strings(
    value: Any, old_id: str, new_id: str, old_name: str, new_name: str
) -> Any:
    if isinstance(value, dict):
        return {
            key: _replace_strings(item, old_id, new_id, old_name, new_name)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_strings(item, old_id, new_id, old_name, new_name) for item in value
        ]
    if isinstance(value, str):
        return value.replace(old_id, new_id).replace(old_name, new_name)
    return value


def _configure_manifest(settings: LspSettings) -> None:
    package_path = ROOT / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    old_server_info = package.get("serverInfo", {})
    old_id = old_server_info.get("module", settings.extension_id)
    old_name = old_server_info.get("name", settings.name)

    package["displayName"] = settings.name
    package["description"] = "Language server integration for VS Code."
    package["keywords"] = ["language-server", "lsp"]
    package["serverInfo"] = {
        "name": settings.name,
        "module": settings.extension_id,
    }
    package["activationEvents"] = [
        *(f"onLanguage:{language}" for language in settings.language_ids.split(",")),
        "onNotebook:jupyter-notebook",
        "onNotebook:interactive",
    ]

    contributes = package.setdefault("contributes", {})
    configuration = contributes.get("configuration", {})
    properties = configuration.get("properties", {})
    updated_properties = {}
    for key, value in properties.items():
        setting_name = key.split(".", 1)[-1]
        updated_key = f"{settings.extension_id}.{setting_name}"
        updated_properties[updated_key] = _replace_strings(
            value, old_id, settings.extension_id, old_name, settings.name
        )
    configuration["properties"] = updated_properties

    for command in contributes.get("commands", []):
        command["category"] = settings.name
        command["command"] = f"{settings.extension_id}.restart"

    package_path.write_text(
        json.dumps(package, indent="\t", ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _runtime_configuration(settings: LspSettings) -> dict[str, Any]:
    runtime_config: dict[str, Any] = {
        "mode": settings.mode,
        "serverInfo": {
            "name": settings.name,
            "module": settings.extension_id,
        },
        "languageIds": settings.language_ids.split(","),
    }
    if settings.mode == "python":
        runtime_config.update(
            {
                "importModule": settings.import_module,
                "serverAttribute": settings.server_attribute,
                "runModule": settings.run_module,
                "pythonCommand": settings.python_command,
            }
        )
    else:
        runtime_config.update(
            {
                "command": settings.command,
                "commandArgs": settings.command_args,
            }
        )
    return runtime_config


def configure() -> None:
    """Write generated server config and synchronize extension manifest IDs."""
    settings = load_settings()
    _configure_manifest(settings)
    runtime_config = _runtime_configuration(settings)
    config_path = ROOT / "bundled" / "tool" / "lsp_config.json"
    config_path.write_text(
        json.dumps(runtime_config, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    configure()
