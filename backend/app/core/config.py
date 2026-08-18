"""Configuration settings and manager for AetherPhoenix backend.

Provides centralized loading, validation, dynamic updating, and single source of truth
for runtime infrastructure configuration across the application.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VALID_LOG_LEVELS: Set[str] = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"}
VALID_ENVIRONMENTS: Set[str] = {"development", "staging", "production", "testing"}
SENSITIVE_KEYS: Set[str] = {"SECRET_KEY", "PASSWORD", "TOKEN", "API_KEY"}


class RuntimeSettings(BaseSettings):
    """Runtime infrastructure configuration settings schema."""

    # Core Infrastructure
    PROJECT_NAME: str = Field(default="AetherPhoenix", description="Application name")
    VERSION: str = Field(default="0.1.0", description="Application version")
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    API_V1_STR: str = Field(default="/api/v1", description="API v1 route prefix")

    # Server & Network Infrastructure
    HOST: str = Field(default="0.0.0.0", description="Server bind host")
    PORT: int = Field(default=8000, description="Server listening port")
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for authentication & crypto",
    )
    ALLOWED_HOSTS: List[str] = Field(
        default_factory=lambda: ["*"], description="Allowed HTTP host headers"
    )
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        description="CORS allowed origins",
    )

    # Database Infrastructure
    DATABASE_URL: str = Field(
        default="sqlite:///./aether_phoenix.db", description="Database connection URL"
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Database pool max overflow")
    DB_ECHO: bool = Field(default=False, description="Enable SQLAlchemy echo logging")

    # Logging Infrastructure
    LOG_LEVEL: str = Field(default="INFO", description="Minimum log severity level")
    LOG_DIR: str = Field(default="logs", description="Directory path for log files")
    LOG_FILE: str = Field(
        default="aether_phoenix.log", description="Log output filename"
    )
    LOG_FORMAT_JSON: bool = Field(
        default=True, description="Enable structured JSON log format"
    )
    LOG_CONSOLE_ENABLED: bool = Field(
        default=True, description="Enable stdout console logging"
    )
    LOG_FILE_ENABLED: bool = Field(
        default=True, description="Enable log file persistence"
    )

    # Execution & Runtime Infrastructure
    MAX_WORKERS: int = Field(
        default=4, description="Maximum concurrent worker threads/processes"
    )
    EXECUTION_TIMEOUT_SECONDS: int = Field(
        default=300, description="Task execution timeout in seconds"
    )
    PERMISSION_TIMEOUT_SECONDS: int = Field(
        default=30, description="Default timeout for permission requests in seconds"
    )
    HEARTBEAT_INTERVAL_SECONDS: int = Field(
        default=30, description="Runtime kernel heartbeat interval"
    )

    # Storage & Path Infrastructure
    DATA_DIR: str = Field(
        default="data", description="Directory for persistent application data"
    )
    ARTIFACTS_DIR: str = Field(
        default="artifacts", description="Directory for generated workflow artifacts"
    )
    TEMP_DIR: str = Field(
        default="tmp", description="Directory for temporary runtime files"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def validate_log_level(cls, v: Any) -> str:
        """Validate and normalize log level string."""
        if isinstance(v, str):
            v_upper = v.upper().strip()
            if v_upper in VALID_LOG_LEVELS:
                return v_upper
        allowed = ", ".join(sorted(VALID_LOG_LEVELS))
        raise ValueError(f"Invalid LOG_LEVEL '{v}'. Allowed values: {allowed}")

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def validate_environment(cls, v: Any) -> str:
        """Validate and normalize runtime environment string."""
        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower in VALID_ENVIRONMENTS:
                return v_lower
        allowed = ", ".join(sorted(VALID_ENVIRONMENTS))
        raise ValueError(f"Invalid ENVIRONMENT '{v}'. Allowed values: {allowed}")

    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate network port range."""
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @field_validator("MAX_WORKERS")
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        """Validate maximum worker count."""
        if v < 1:
            raise ValueError(f"MAX_WORKERS must be at least 1, got {v}")
        return v

    @field_validator(
        "EXECUTION_TIMEOUT_SECONDS",
        "PERMISSION_TIMEOUT_SECONDS",
        "HEARTBEAT_INTERVAL_SECONDS",
    )
    @classmethod
    def validate_positive_seconds(cls, v: int) -> int:
        """Validate timeout and interval duration values."""
        if v <= 0:
            raise ValueError(
                f"Timeout/Interval seconds must be greater than 0, got {v}"
            )
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL is not empty."""
        if not v or not v.strip():
            raise ValueError("DATABASE_URL cannot be empty")
        return v.strip()


# Backward compatibility alias
Settings = RuntimeSettings

# Module-level settings variable placeholder
settings: RuntimeSettings = None  # type: ignore


def _sync_global_settings(new_settings: RuntimeSettings) -> None:
    """Internal helper to keep global settings reference synchronized."""
    global settings
    settings = new_settings


class ConfigurationManager:
    """Centralized manager for loading, validating, and managing application
    configuration.
    """

    def __init__(
        self,
        env_file: Optional[Union[str, Path]] = None,
        env_override: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._env_file: Optional[Union[str, Path]] = env_file
        self._settings: RuntimeSettings = self.load(
            env_file=env_file, env_override=env_override
        )

    def load(
        self,
        env_file: Optional[Union[str, Path]] = None,
        env_override: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> RuntimeSettings:
        """Load and validate configuration settings.

        Args:
            env_file: Optional path to .env file.
            env_override: Optional dictionary of environment overrides.
            **kwargs: Additional explicit setting overrides.

        Returns:
            RuntimeSettings: Validated runtime configuration instance.
        """
        file_to_use = env_file if env_file is not None else self._env_file
        init_kwargs: Dict[str, Any] = {}
        if file_to_use is not None:
            init_kwargs["_env_file"] = file_to_use

        if env_override:
            init_kwargs.update(env_override)
        if kwargs:
            init_kwargs.update(kwargs)

        self._settings = RuntimeSettings(**init_kwargs)
        _sync_global_settings(self._settings)
        return self._settings

    def get_config(self) -> RuntimeSettings:
        """Get current active configuration settings.

        Returns:
            RuntimeSettings: Global runtime configuration instance.
        """
        return self._settings

    def reload(self, env_file: Optional[Union[str, Path]] = None) -> RuntimeSettings:
        """Reload configuration settings from environment or specified env file.

        Args:
            env_file: Optional path to .env file.

        Returns:
            RuntimeSettings: Updated configuration instance.
        """
        if env_file is not None:
            self._env_file = env_file
        return self.load(env_file=self._env_file)

    def update(self, new_settings: Dict[str, Any]) -> RuntimeSettings:
        """Dynamically update active configuration settings with validation.

        Args:
            new_settings: Dictionary of configuration keys and new values.

        Returns:
            RuntimeSettings: Re-validated configuration instance.
        """
        current_data = self._settings.model_dump()
        current_data.update(new_settings)
        self._settings = RuntimeSettings(**current_data)
        _sync_global_settings(self._settings)
        return self._settings

    def reset(self) -> RuntimeSettings:
        """Reset configuration settings to default environment state.

        Returns:
            RuntimeSettings: Reset configuration instance.
        """
        self._env_file = None
        return self.load()

    def to_dict(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """Export settings dictionary with optional sensitive field masking.

        Args:
            mask_sensitive: If True, mask sensitive settings like SECRET_KEY.

        Returns:
            Dict[str, Any]: Dictionary of active settings.
        """
        data = self._settings.model_dump()
        if mask_sensitive:
            for key in data:
                if any(sec in key.upper() for sec in SENSITIVE_KEYS):
                    data[key] = "********"
        return data


_config_manager = ConfigurationManager()
settings = _config_manager.get_config()


def get_config() -> RuntimeSettings:
    """Access global runtime configuration instance (Single Source of Truth).

    Returns:
        RuntimeSettings: Active runtime configuration instance.
    """
    return _config_manager.get_config()


def get_config_manager() -> ConfigurationManager:
    """Access global ConfigurationManager instance.

    Returns:
        ConfigurationManager: Active configuration manager instance.
    """
    return _config_manager
