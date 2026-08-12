"""Unit tests for Configuration Manager and RuntimeSettings."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import (
    ConfigurationManager,
    RuntimeSettings,
    get_config,
    get_config_manager,
)


@pytest.fixture(autouse=True)
def reset_config_state():
    """Ensure ConfigurationManager state is clean before and after each test."""
    manager = get_config_manager()
    manager.reset()
    yield
    manager.reset()


def test_default_settings():
    """Verify default runtime infrastructure settings."""
    cfg = RuntimeSettings(_env_file=None)
    assert cfg.PROJECT_NAME == "AetherPhoenix"
    assert cfg.VERSION == "0.1.0"
    assert cfg.ENVIRONMENT == "development"
    assert cfg.DEBUG is False
    assert cfg.HOST == "0.0.0.0"
    assert cfg.PORT == 8000
    assert cfg.DATABASE_URL == "sqlite:///./aether_phoenix.db"
    assert cfg.LOG_LEVEL == "INFO"
    assert cfg.LOG_FORMAT_JSON is True
    assert cfg.MAX_WORKERS == 4
    assert cfg.EXECUTION_TIMEOUT_SECONDS == 300
    assert cfg.HEARTBEAT_INTERVAL_SECONDS == 30


def test_log_level_validation_valid():
    """Verify valid log levels in different casings normalize to uppercase."""
    for level in ["debug", "Info", "WARNING", "warn", "error", "CRITICAL"]:
        cfg = RuntimeSettings(LOG_LEVEL=level)
        expected = level.upper()
        assert cfg.LOG_LEVEL == expected


def test_log_level_validation_invalid():
    """Verify invalid log level raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        RuntimeSettings(LOG_LEVEL="VERBOSE")
    assert "Invalid LOG_LEVEL" in str(exc_info.value)


def test_environment_validation_valid():
    """Verify valid environment names normalize to lowercase."""
    for env in ["DEVELOPMENT", "Staging", "production", "testing"]:
        cfg = RuntimeSettings(ENVIRONMENT=env)
        assert cfg.ENVIRONMENT == env.lower()


def test_environment_validation_invalid():
    """Verify invalid environment raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        RuntimeSettings(ENVIRONMENT="prod_invalid")
    assert "Invalid ENVIRONMENT" in str(exc_info.value)


def test_port_validation():
    """Verify port validation bounds (1 to 65535)."""
    assert RuntimeSettings(PORT=80).PORT == 80
    assert RuntimeSettings(PORT=65535).PORT == 65535

    with pytest.raises(ValidationError) as exc_info:
        RuntimeSettings(PORT=0)
    assert "Port must be between 1 and 65535" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        RuntimeSettings(PORT=70000)
    assert "Port must be between 1 and 65535" in str(exc_info.value)


def test_max_workers_validation():
    """Verify MAX_WORKERS validation."""
    assert RuntimeSettings(MAX_WORKERS=1).MAX_WORKERS == 1

    with pytest.raises(ValidationError) as exc_info:
        RuntimeSettings(MAX_WORKERS=0)
    assert "MAX_WORKERS must be at least 1" in str(exc_info.value)


def test_timeout_and_interval_validation():
    """Verify timeout and heartbeat interval validation."""
    with pytest.raises(ValidationError) as exc_info:
        RuntimeSettings(EXECUTION_TIMEOUT_SECONDS=0)
    assert "greater than 0" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        RuntimeSettings(HEARTBEAT_INTERVAL_SECONDS=-5)
    assert "greater than 0" in str(exc_info.value)


def test_database_url_validation():
    """Verify empty DATABASE_URL is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        RuntimeSettings(DATABASE_URL="   ")
    assert "DATABASE_URL cannot be empty" in str(exc_info.value)


def test_environment_variable_loading(monkeypatch):
    """Verify loading configuration settings from environment variables."""
    monkeypatch.setenv("PROJECT_NAME", "CustomPhoenix")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ENVIRONMENT", "staging")

    cfg = RuntimeSettings()
    assert cfg.PROJECT_NAME == "CustomPhoenix"
    assert cfg.PORT == 9000
    assert cfg.LOG_LEVEL == "DEBUG"
    assert cfg.ENVIRONMENT == "staging"


def test_custom_env_file_loading(tmp_path: Path):
    """Verify loading configuration from a custom .env file."""
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "PROJECT_NAME=EnvFilePhoenix\n"
        "PORT=9090\n"
        "LOG_LEVEL=WARNING\n"
        "ENVIRONMENT=testing\n",
        encoding="utf-8",
    )

    manager = ConfigurationManager(env_file=env_file)
    cfg = manager.get_config()
    assert cfg.PROJECT_NAME == "EnvFilePhoenix"
    assert cfg.PORT == 9090
    assert cfg.LOG_LEVEL == "WARNING"
    assert cfg.ENVIRONMENT == "testing"


def test_configuration_manager_lifecycle():
    """Verify ConfigurationManager update, reload, and reset lifecycle."""
    manager = get_config_manager()

    # Initial state
    assert manager.get_config().PORT == 8000
    assert manager.get_config().LOG_LEVEL == "INFO"

    # Dynamic update
    updated = manager.update({"PORT": 8500, "LOG_LEVEL": "DEBUG"})
    assert updated.PORT == 8500
    assert updated.LOG_LEVEL == "DEBUG"
    assert get_config().PORT == 8500

    # Reset
    reset_cfg = manager.reset()
    assert reset_cfg.PORT == 8000
    assert reset_cfg.LOG_LEVEL == "INFO"


def test_configuration_manager_update_validation():
    """Verify updating manager with invalid settings raises ValidationError
    and preserves active settings.
    """
    manager = get_config_manager()
    initial_port = manager.get_config().PORT

    with pytest.raises(ValidationError):
        manager.update({"PORT": -1})

    # Active settings should remain unchanged
    assert manager.get_config().PORT == initial_port


def test_to_dict_sensitive_masking():
    """Verify to_dict sensitive key masking behavior."""
    manager = get_config_manager()
    manager.update({"SECRET_KEY": "super-secret-pass"})

    masked = manager.to_dict(mask_sensitive=True)
    assert masked["SECRET_KEY"] == "********"

    unmasked = manager.to_dict(mask_sensitive=False)
    assert unmasked["SECRET_KEY"] == "super-secret-pass"


def test_backward_compatibility_imports():
    """Verify backward compatible exports and aliases."""
    from app.core import (
        ConfigurationManager,
        RuntimeSettings,
        Settings,
        get_config,
        settings,
    )

    assert ConfigurationManager is not None
    assert Settings is RuntimeSettings
    assert isinstance(get_config(), RuntimeSettings)
    assert settings.PROJECT_NAME == "AetherPhoenix"
