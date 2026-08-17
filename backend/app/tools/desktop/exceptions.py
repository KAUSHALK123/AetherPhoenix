"""Desktop and Mouse Automation Exceptions."""


class DesktopActionError(Exception):
    """Base exception for all desktop automation errors."""

    pass


class MouseActionError(DesktopActionError):
    """Base exception for mouse-specific interaction errors."""

    pass


class InvalidCoordinatesError(MouseActionError):
    """Raised when target coordinates are invalid or outside display boundaries."""

    pass


class DesktopSessionUnavailableError(DesktopActionError):
    """Raised when desktop session or display is not available or accessible."""

    pass


class MouseTimeoutError(MouseActionError):
    """Raised when a mouse operation exceeds its allocated execution timeout."""

    pass
