"""Validated configuration for the selected Python language server package."""

import re
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


def _validate_package(package: str) -> str:
    package = package.strip()
    if not package:
        raise ValueError("LSP_PACKAGE must not be empty when LSP_MODE=python")
    if package.lower().endswith(".whl"):
        wheel_path = Path(package).expanduser()
        if not wheel_path.is_absolute():
            wheel_path = ROOT / wheel_path
        if not wheel_path.is_file():
            raise ValueError(f"LSP_PACKAGE wheel does not exist: {wheel_path}")
        return str(wheel_path.resolve())

    try:
        Requirement(package)
    except InvalidRequirement as error:
        raise ValueError(
            "LSP_PACKAGE must be a wheel path or PEP 508 requirement "
            "(for example, 'my-lsp==1.2.3')"
        ) from error
    return package


def _validate_language_ids(language_ids: str) -> str:
    languages = [language.strip() for language in language_ids.split(",")]
    if not languages or any(
        not re.fullmatch(r"[A-Za-z0-9._-]+", language) for language in languages
    ):
        raise ValueError(
            "LSP_LANGUAGE_IDS must be comma-separated VS Code language IDs"
        )
    return ",".join(languages)


class LspSettings(BaseSettings):
    """Load the selected LSP launch mode and entry point from environment."""

    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env.example", ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    mode: str = Field(default="python", validation_alias="LSP_MODE")
    package: str = Field(default="", validation_alias="LSP_PACKAGE")
    import_module: str = Field(default="", validation_alias="LSP_IMPORT_MODULE")
    server_attribute: str = Field(
        default="server", validation_alias="LSP_SERVER_ATTRIBUTE"
    )
    run_module: str = Field(default="", validation_alias="LSP_RUN_MODULE")
    command: str = Field(default="", validation_alias="LSP_COMMAND")
    command_args: list[str] = Field(
        default_factory=list, validation_alias="LSP_COMMAND_ARGS"
    )
    language_ids: str = Field(default="python", validation_alias="LSP_LANGUAGE_IDS")
    python_command: str = Field(
        default="python3", validation_alias="LSP_PYTHON_COMMAND"
    )
    extension_id: str = Field(validation_alias="LSP_ID")
    name: str = Field(validation_alias="LSP_NAME")

    @field_validator("extension_id")
    @classmethod
    def validate_extension_id(cls, value: str) -> str:
        """Restrict the VS Code configuration namespace to a simple identifier."""
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
            raise ValueError(f"Invalid VS Code extension identifier: {value!r}")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Ensure the display name is not empty."""
        value = value.strip()
        if not value:
            raise ValueError("LSP_NAME must not be empty")
        return value

    def _validate_python_configuration(self) -> None:
        for module in (self.import_module, self.run_module):
            if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module):
                raise ValueError(f"Invalid Python module name: {module!r}")
        if not self.server_attribute.isidentifier():
            raise ValueError(f"Invalid server attribute: {self.server_attribute!r}")
        if not self.python_command.strip():
            raise ValueError("LSP_PYTHON_COMMAND must not be empty")
        self.package = _validate_package(self.package)

    @model_validator(mode="after")
    def validate_launch_configuration(self) -> "LspSettings":
        """Validate only the launch fields used by the selected mode."""
        self.mode = self.mode.strip().lower()
        if self.mode not in {"python", "command"}:
            raise ValueError("LSP_MODE must be either 'python' or 'command'")

        self.language_ids = _validate_language_ids(self.language_ids)

        if self.mode == "command":
            if not self.command.strip():
                raise ValueError("LSP_COMMAND is required when LSP_MODE=command")
            return self

        self._validate_python_configuration()
        return self


def load_settings() -> LspSettings:
    """Load configuration from .env and process environment variables."""
    return LspSettings()
