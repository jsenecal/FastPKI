import pytest
from cryptography.fernet import Fernet

from app.services.encryption import EncryptionService

SAMPLE_PEM = "-----BEGIN RSA PRIVATE KEY-----\nMIIBogIBAAJBALRi...\n-----END RSA PRIVATE KEY-----\n"
TEST_KEY = Fernet.generate_key().decode()
OTHER_KEY = Fernet.generate_key().decode()


def test_is_encrypted_with_plain_pem():
    assert not EncryptionService.is_encrypted(SAMPLE_PEM)


def test_is_encrypted_with_encrypted_data():
    assert EncryptionService.is_encrypted("gAAAAABh...")


def test_encrypt_returns_non_pem_string(monkeypatch):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    result = EncryptionService.encrypt_private_key(SAMPLE_PEM)
    assert not result.startswith("-----BEGIN")
    assert result != SAMPLE_PEM


def test_decrypt_plain_pem_passthrough(monkeypatch):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    result = EncryptionService.decrypt_private_key(SAMPLE_PEM)
    assert result == SAMPLE_PEM


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    encrypted = EncryptionService.encrypt_private_key(SAMPLE_PEM)
    decrypted = EncryptionService.decrypt_private_key(encrypted)
    assert decrypted == SAMPLE_PEM


def test_encrypt_disabled_when_no_key(monkeypatch):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", None
    )
    result = EncryptionService.encrypt_private_key(SAMPLE_PEM)
    assert result == SAMPLE_PEM


def test_decrypt_encrypted_without_key_raises(monkeypatch):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    encrypted = EncryptionService.encrypt_private_key(SAMPLE_PEM)

    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", None
    )
    with pytest.raises(ValueError, match="not configured"):
        EncryptionService.decrypt_private_key(encrypted)


def test_decrypt_with_wrong_key_raises(monkeypatch):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    encrypted = EncryptionService.encrypt_private_key(SAMPLE_PEM)

    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", OTHER_KEY
    )
    with pytest.raises(ValueError, match="wrong encryption key"):
        EncryptionService.decrypt_private_key(encrypted)


def test_encrypt_already_encrypted_is_noop(monkeypatch):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    encrypted = EncryptionService.encrypt_private_key(SAMPLE_PEM)
    double_encrypted = EncryptionService.encrypt_private_key(encrypted)
    assert double_encrypted == encrypted


def test_decrypt_optional_none():
    assert EncryptionService.decrypt_optional_private_key(None) is None


def test_decrypt_optional_with_value(monkeypatch):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    encrypted = EncryptionService.encrypt_private_key(SAMPLE_PEM)
    result = EncryptionService.decrypt_optional_private_key(encrypted)
    assert result == SAMPLE_PEM
