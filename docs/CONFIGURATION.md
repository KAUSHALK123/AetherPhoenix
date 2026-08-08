# Configuration Manager Documentation

## Overview

The **Configuration Manager** (`app.core.config`) serves as the single source of truth for loading, validating, updating, and providing runtime configuration settings across the entire AetherPhoenix platform.

It manages all infrastructure runtime settings—including server networking, database connections, logging, execution parameters, and storage paths—from environment variables, `.env` files, or dynamic runtime updates.

---

## Architecture & Design

The configuration system consists of two primary components:

1. **`RuntimeSettings`**: A Pydantic `BaseSettings` model that enforces strict typing, default values, environment variable bindings, and field validation rules.
2. **`ConfigurationManager`**: A centralized management class that handles initial configuration loading, custom `.env` file loading, dynamic updates, configuration resetting, and dictionary exports with sensitive field masking.

Global accessors provide convenient access to settings across all modules:
- `get_config() -> RuntimeSettings`: Retrieves the active global configuration.
- `get_config_manager() -> ConfigurationManager`: Retrieves the active configuration manager.
- `from app.core.config import settings`: Provides a direct global reference to active settings.

---

## Settings Schema & Default Values

| Field Name | Type | Default Value | Description |
|---|---|---|---|
| **Core Infrastructure** | | | |
| `PROJECT_NAME` | `str` | `"AetherPhoenix"` | Application name |
| `VERSION` | `str` | `"0.1.0"` | Application version |
| `ENVIRONMENT` | `str` | `"development"` | Runtime environment (`development`, `staging`, `production`, `testing`) |
| `DEBUG` | `bool` | `False` | Enable debug mode |
| `API_V1_STR` | `str` | `"/api/v1"` | API v1 route prefix |
| **Server & Network** | | | |
| `HOST` | `str` | `"0.0.0.0"` | Server listening host IP |
| `PORT` | `int` | `8000` | Server network port (1–65535) |
| `SECRET_KEY` | `str` | `"dev-secret-key-..."` | Application secret key for crypto/auth |
| `ALLOWED_HOSTS` | `List[str]` | `["*"]` | Allowed HTTP host headers |
| `CORS_ORIGINS` | `List[str]` | `["http://localhost:5173", ...]` | CORS allowed origin URLs |
| **Database** | | | |
| `DATABASE_URL` | `str` | `"sqlite:///./aether_phoenix.db"` | Database connection string |
| `DB_POOL_SIZE` | `int` | `5` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | `int` | `10` | SQLAlchemy max overflow |
| `DB_ECHO` | `bool` | `False` | Enable SQL query debug logging |
| **Logging** | | | |
| `LOG_LEVEL` | `str` | `"INFO"` | Severity threshold (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `LOG_DIR` | `str` | `"logs"` | Directory for log file persistence |
| `LOG_FILE` | `str` | `"aether_phoenix.log"` | Output log filename |
| `LOG_FORMAT_JSON` | `bool` | `True` | Structured JSON log formatting flag |
| `LOG_CONSOLE_ENABLED` | `bool` | `True` | Enable stdout console logging |
| `LOG_FILE_ENABLED` | `bool` | `True` | Enable log file output |
| **Execution & Limits** | | | |
| `MAX_WORKERS` | `int` | `4` | Maximum concurrent worker allocation |
| `EXECUTION_TIMEOUT_SECONDS` | `int` | `300` | Task execution timeout limit |
| `HEARTBEAT_INTERVAL_SECONDS` | `int` | `30` | Kernel heartbeat check interval |
| **Storage & Paths** | | | |
| `DATA_DIR` | `str` | `"data"` | Persistent application data directory |
| `ARTIFACTS_DIR` | `str` | `"artifacts"` | Generated workflow artifacts directory |
| `TEMP_DIR` | `str` | `"tmp"` | Temporary files workspace directory |

---

## Validation Rules

The Configuration Manager performs strict runtime validation:

- **`LOG_LEVEL`**: Must be one of `DEBUG`, `INFO`, `WARNING`, `WARN`, `ERROR`, `CRITICAL`. Values are case-insensitive and automatically normalized to uppercase.
- **`ENVIRONMENT`**: Must be one of `development`, `staging`, `production`, `testing`. Values are case-insensitive and automatically normalized to lowercase.
- **`PORT`**: Must be an integer between `1` and `65535`.
- **`MAX_WORKERS`**: Must be an integer greater than or equal to `1`.
- **`EXECUTION_TIMEOUT_SECONDS` / `HEARTBEAT_INTERVAL_SECONDS`**: Must be positive integers (`> 0`).
- **`DATABASE_URL`**: Cannot be an empty or whitespace-only string.

Invalid configurations immediately raise a Pydantic `ValidationError` containing specific feedback on why the configuration failed validation.

---

## Usage Examples

### 1. Accessing Global Configuration

```python
from app.core.config import get_config, settings

# Using get_config() function (Recommended)
config = get_config()
print(f"Running {config.PROJECT_NAME} in {config.ENVIRONMENT} mode")

# Or accessing the settings object directly
print(f"Log Level: {settings.LOG_LEVEL}")
```

### 2. Loading from Custom Environment File

```python
from app.core.config import ConfigurationManager

manager = ConfigurationManager(env_file=".env.production")
config = manager.get_config()
```

### 3. Dynamic Runtime Updates & Re-validation

```python
from app.core.config import get_config_manager

manager = get_config_manager()

# Update settings dynamically at runtime
updated_config = manager.update({
    "LOG_LEVEL": "DEBUG",
    "MAX_WORKERS": 8,
})
```

### 4. Dictionary Export with Sensitive Key Masking

```python
from app.core.config import get_config_manager

manager = get_config_manager()
config_dict = manager.to_dict(mask_sensitive=True)

# SECRET_KEY will be masked as "********"
print(config_dict["SECRET_KEY"])
```

### 5. Resetting Configuration

```python
from app.core.config import get_config_manager

manager = get_config_manager()
manager.reset()
```

---

## Unit Testing

Run the test suite using pytest:

```bash
$env:PYTHONPATH="c:\Users\akshitha\Desktop\AetherPhoenix;c:\Users\akshitha\Desktop\AetherPhoenix\backend"
python -m pytest backend/tests/core/test_config.py -v
```
