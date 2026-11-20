"""Custom exceptions."""
from __future__ import annotations


class ApexTradeException(Exception):
    """Base application exception."""

    def __init__(self, message: str = "An error occurred", status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(ApexTradeException):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=401)


class AuthorizationError(ApexTradeException):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403)


class NotFoundError(ApexTradeException):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, status_code=404)


class ValidationError(ApexTradeException):
    def __init__(self, message: str = "Validation error") -> None:
        super().__init__(message, status_code=400)


class BrokerError(ApexTradeException):
    def __init__(self, message: str = "Broker integration error") -> None:
        super().__init__(message, status_code=502)


class MarketClosedError(ApexTradeException):
    def __init__(self, message: str = "Market is closed") -> None:
        super().__init__(message, status_code=400)
