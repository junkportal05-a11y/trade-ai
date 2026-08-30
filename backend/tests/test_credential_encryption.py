"""Unit tests for strict credential encryption and decryption error handling."""
import pytest
from unittest import mock

from db import _encrypt_field, _decrypt_field


def test_encrypt_field_success():
    with mock.patch("app.core.security.encrypt_value", return_value="enc_token"):
        assert _encrypt_field("secret123") == "enc_token"


def test_encrypt_field_raises_on_failure():
    with mock.patch("app.core.security.encrypt_value", return_value=None):
        with pytest.raises(ValueError) as exc:
            _encrypt_field("secret123")
        assert "Encryption failed" in str(exc.value)


def test_decrypt_field_success():
    with mock.patch("app.core.security.decrypt_value", return_value="secret123"):
        assert _decrypt_field("enc_token") == "secret123"


def test_decrypt_field_raises_on_failure():
    with mock.patch("app.core.security.decrypt_value", return_value=None):
        with pytest.raises(ValueError) as exc:
            _decrypt_field("corrupt_or_legacy_token")
        assert "Decryption failed" in str(exc.value)
