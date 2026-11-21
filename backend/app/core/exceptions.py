"""Custom exceptions with structured error codes for API contracts."""
from __future__ import annotations

from typing import Any


class ApexTradeException(Exception):
    """Base application exception with error code for API contracts."""

    def __init__(
        self,
        message: str = "An error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class AuthenticationError(ApexTradeException):
    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, details=details)


class AuthorizationError(ApexTradeException):
    def __init__(
        self,
        message: str = "Forbidden",
        code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=403, details=details)


class NotFoundError(ApexTradeException):
    def __init__(
        self,
        message: str = "Not found",
        code: str = "NOT_FOUND",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=404, details=details)


class ValidationError(ApexTradeException):
    def __init__(
        self,
        message: str = "Validation error",
        code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=422, details=details)


class BrokerError(ApexTradeException):
    def __init__(
        self,
        message: str = "Broker integration error",
        code: str = "BROKER_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=502, details=details)


class MarketClosedError(ApexTradeException):
    def __init__(
        self,
        message: str = "Market is closed",
        code: str = "MARKET_CLOSED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=400, details=details)


class RateLimitError(ApexTradeException):
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: str = "RATE_LIMITED",
        retry_after_seconds: int = 60,
        details: dict[str, Any] | None = None,
    ) -> None:
        if details is None:
            details = {}
        details["retry_after_seconds"] = retry_after_seconds
        super().__init__(message, code=code, status_code=429, details=details)


class ExternalServiceError(ApexTradeException):
    """Raised when an external service (broker, data provider) fails."""

    def __init__(
        self,
        message: str = "External service unavailable",
        code: str = "EXTERNAL_SERVICE_ERROR",
        service: str = "unknown",
        details: dict[str, Any] | None = None,
    ) -> None:
        if details is None:
            details = {}
        details["service"] = service
        super().__init__(message, code=code, status_code=503, details=details)


class DataUnavailableError(ApexTradeException):
    """Raised when market data cannot be retrieved."""

    def __init__(
        self,
        message: str = "Market data temporarily unavailable",
        code: str = "DATA_UNAVAILABLE",
        symbol: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if details is None:
            details = {}
        if symbol:
            details["symbol"] = symbol
        super().__init__(message, code=code, status_code=503, details=details)
