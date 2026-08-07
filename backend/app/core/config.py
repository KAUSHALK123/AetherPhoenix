"""Configuration settings for AetherPhoenix backend."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema."""

    PROJECT_NAME: str = "AetherPhoenix"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database settings
    DATABASE_URL: str = "sqlite:///./aether_phoenix.db"

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FILE: str = "aether_phoenix.log"
    LOG_FORMAT_JSON: bool = True
    LOG_CONSOLE_ENABLED: bool = True
    LOG_FILE_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
