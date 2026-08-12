from typing import Any, Set

SENSITIVE_KEYS: Set[str] = {
    "api_key",
    "apikey",
    "password",
    "pwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "auth",
    "authorization",
    "credentials",
    "private_key",
    "bearer",
}


def is_sensitive_key(key: str) -> bool:
    """Returns True if key contains any sensitive keyword."""
    key_lower = key.lower()
    return any(sens in key_lower for sens in SENSITIVE_KEYS)


def sanitize_log_data(data: Any, max_string_len: int = 500) -> Any:
    """
    Recursively sanitizes data payloads for structured logging.
    Masks sensitive values (passwords, tokens, keys) and truncates oversized contents.

    Args:
        data: Primitive, dict, list, or object payload.
        max_string_len: Maximum length threshold for logged string values.

    Returns:
        Sanitized payload safe for log emission.
    """
    if isinstance(data, dict):
        sanitized_dict: dict[str, Any] = {}
        for key, val in data.items():
            if is_sensitive_key(str(key)):
                sanitized_dict[key] = "***REDACTED***"
            else:
                sanitized_dict[key] = sanitize_log_data(
                    val, max_string_len=max_string_len
                )
        return sanitized_dict

    elif isinstance(data, (list, tuple)):
        return [
            sanitize_log_data(item, max_string_len=max_string_len) for item in data
        ]

    elif isinstance(data, (bytes, bytearray)):
        return f"<Binary data ({len(data)} bytes)>"

    elif isinstance(data, str):
        if len(data) > max_string_len:
            truncated = len(data) - max_string_len
            return f"{data[:max_string_len]}... <Truncated {truncated} chars>"
        return data

    elif hasattr(data, "model_dump") and callable(data.model_dump):
        return sanitize_log_data(
            data.model_dump(mode="json"), max_string_len=max_string_len
        )

    return data
