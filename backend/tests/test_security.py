from app.core.security import encrypt_value, decrypt_value
from unittest import mock

def test_encrypt_decrypt_valid_string():
    plaintext = "super_secret_value"
    with mock.patch("app.core.config.settings.database_url", "sqlite:///test.db"):
        ciphertext = encrypt_value(plaintext)

        assert ciphertext is not None
        assert ciphertext != plaintext

        decrypted = decrypt_value(ciphertext)
        assert decrypted == plaintext

def test_encrypt_decrypt_none():
    with mock.patch("app.core.config.settings.database_url", "sqlite:///test.db"):
        assert encrypt_value(None) is None
        assert decrypt_value(None) is None

def test_decrypt_invalid_ciphertext():
    invalid_ciphertext = "not_a_valid_fernet_token"
    with mock.patch("app.core.config.settings.database_url", "sqlite:///test.db"):
        assert decrypt_value(invalid_ciphertext) is None
