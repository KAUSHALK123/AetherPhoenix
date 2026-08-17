"""Desktop and Mouse Automation Exceptions."""


class DesktopError(Exception):
    """Base exception for all desktop automation errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DesktopActionError(DesktopError):
    """
    Base exception for all desktop action errors
    (kept for backward compatibility).
    """

    pass


class DesktopSessionError(DesktopError):
    """Raised when a desktop session operation fails."""

    pass


class DesktopSessionNotFoundError(DesktopSessionError):
    """Raised when the requested desktop session cannot be found."""

    pass


class DesktopSessionExpiredError(DesktopSessionError):
    """Raised when an operation targets an expired desktop session."""

    pass


class DesktopSessionUnavailableError(DesktopActionError):
    """Raised when desktop session or display is not available or accessible."""

    pass


class MouseActionError(DesktopError):
    """Base exception for mouse-specific interaction errors."""

    pass


class InvalidCoordinatesError(MouseActionError):
    """Raised when target coordinates are invalid or outside display boundaries."""

    pass


class MouseTimeoutError(MouseActionError):
    """Raised when a mouse operation exceeds its allocated execution timeout."""

    pass


class ApplicationNotFoundError(DesktopError):
    """Raised when an application executable or process cannot be found."""

    pass


class ApplicationLaunchError(DesktopError):
    """Raised when launching a desktop application fails."""

    pass


class ApplicationTerminationError(DesktopError):
    """Raised when closing or terminating an application fails."""

    pass


class ApplicationUnavailableError(DesktopError):
    """Raised when an application is disallowed or unavailable in the environment."""

    pass


class WindowNotFoundError(DesktopError):
    """Raised when a window matching the search criteria cannot be found."""

    pass


class WindowFocusError(DesktopError):
    """Raised when focusing or activating a window fails."""

    pass


class DesktopTimeoutError(DesktopError):
    """Raised when a desktop automation operation times out."""

    pass


class DesktopSecurityError(DesktopError):
    """Raised when a desktop operation violates security constraints or permissions."""

    pass
