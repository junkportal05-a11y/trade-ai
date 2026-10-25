"""Structured JSON logging setup with correlation ID support."""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Optional
import contextvars

# Context variable to store correlation ID
_correlation_id = contextvars.ContextVar("correlation_id", default="")

def set_correlation_id(value: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id.set(value)

def get_correlation_id() -> str:
    """Retrieve the correlation ID from the current context."""
    return _correlation_id.get()

# Attributes that belong to the standard LogRecord; anything else is treated as
# a custom field supplied via `extra=` and included in the JSON output.
_RESERVED = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName",
}

class JsonFormatter(logging.Formatter):
    """Formatter that outputs log records as JSON."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "correlation_id": get_correlation_id(),
        }
        # Include any custom attributes (passed via `extra=`)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                log_entry[key] = value
        return json.dumps(log_entry)

def configure_json_logging(root_logger: Optional[logging.Logger] = None) -> None:
    """Configure the given logger (or root logger) for JSON output."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter()
    handler.setFormatter(formatter)
    if root_logger is None:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
    else:
        # Replace existing handlers with our JSON handler
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        root_logger.addHandler(handler)

# Provide a named logger for convenience
logger = logging.getLogger("structured")

# Expose set_correlation_id for external use
def set_logging_correlation_id(value: str):
    set_correlation_id(value)