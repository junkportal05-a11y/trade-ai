"""Unit tests for config security enforcement in production vs development environments."""
import os
import pytest
from unittest import mock

from app.core.config import Settings


def test_dev_environment_allows_generated_defaults():
    with mock.patch.dict(os.environ, {"ENVIRONMENT": "development", "JWT_SECRET": "", "FERNET_KEYS": "", "ADMIN_KEY": ""}, clear=True):
        s = Settings()
        assert s.jwt_secret is not None
        assert s.admin_key is not None


def test_production_environment_raises_value_error_on_missing_secrets():
    with mock.patch.dict(os.environ, {"ENVIRONMENT": "production", "JWT_SECRET": "", "FERNET_KEYS": "", "ADMIN_KEY": ""}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            Settings()
        assert "CRITICAL SECURITY FAILURE" in str(exc_info.value)
        assert "JWT_SECRET" in str(exc_info.value)
