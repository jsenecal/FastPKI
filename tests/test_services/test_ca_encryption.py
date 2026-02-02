import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models import CertificateAuthority, CertificateType
from app.services.ca import CAService
from app.services.cert import CertificateService
from app.services.encryption import EncryptionService, encrypt_existing_keys
from tests.conftest import test_engine

TEST_KEY = Fernet.generate_key().decode()
OTHER_KEY = Fernet.generate_key().decode()


@pytest_asyncio.fixture
async def ca_with_encryption(db: AsyncSession, monkeypatch) -> CertificateAuthority:
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    ca_service = CAService(db)
    return await ca_service.create_ca(
        name="Encrypted CA",
        subject_dn="CN=Encrypted CA,O=Test,C=US",
        key_size=2048,
        valid_days=3650,
    )


@pytest.mark.asyncio
async def test_ca_stores_encrypted_key(
    db: AsyncSession, ca_with_encryption: CertificateAuthority
):
    result = await db.execute(
        select(CertificateAuthority).where(
            CertificateAuthority.id == ca_with_encryption.id
        )
    )
    ca = result.scalar_one()
    assert not ca.private_key.startswith("-----BEGIN")
    assert EncryptionService.is_encrypted(ca.private_key)


@pytest.mark.asyncio
async def test_ca_stores_plain_when_disabled(db: AsyncSession, monkeypatch):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", None
    )
    ca_service = CAService(db)
    ca = await ca_service.create_ca(
        name="Plain CA",
        subject_dn="CN=Plain CA,O=Test,C=US",
        key_size=2048,
        valid_days=3650,
    )
    result = await db.execute(
        select(CertificateAuthority).where(CertificateAuthority.id == ca.id)
    )
    raw_ca = result.scalar_one()
    assert raw_ca.private_key.startswith("-----BEGIN")


@pytest.mark.asyncio
async def test_cert_stores_encrypted_key(
    db: AsyncSession, ca_with_encryption: CertificateAuthority, monkeypatch
):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=ca_with_encryption.id,
        common_name="test.example.com",
        subject_dn="CN=test.example.com,O=Test,C=US",
        certificate_type=CertificateType.SERVER,
        key_size=2048,
        valid_days=365,
    )
    assert cert.private_key is not None
    assert not cert.private_key.startswith("-----BEGIN")


@pytest.mark.asyncio
async def test_cert_signing_with_encrypted_ca_key(
    db: AsyncSession, ca_with_encryption: CertificateAuthority, monkeypatch
):
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=ca_with_encryption.id,
        common_name="signed.example.com",
        subject_dn="CN=signed.example.com,O=Test,C=US",
        certificate_type=CertificateType.SERVER,
        key_size=2048,
        valid_days=365,
    )
    assert cert.id is not None
    assert cert.certificate is not None
    assert cert.certificate.startswith("-----BEGIN CERTIFICATE-----")


@pytest.mark.asyncio
async def test_encrypt_existing_keys_migrates(db: AsyncSession, monkeypatch):
    # Point encrypt_existing_keys at the test engine
    monkeypatch.setattr("app.db.session.engine", test_engine)

    # Create a CA with encryption disabled (plaintext key)
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", None
    )
    ca_service = CAService(db)
    ca = await ca_service.create_ca(
        name="Migration CA",
        subject_dn="CN=Migration CA,O=Test,C=US",
        key_size=2048,
        valid_days=3650,
    )
    ca_id = ca.id

    # Verify it's plaintext
    result = await db.execute(
        select(CertificateAuthority).where(CertificateAuthority.id == ca_id)
    )
    raw_ca = result.scalar_one()
    assert raw_ca.private_key.startswith("-----BEGIN")

    # Now enable encryption and run migration
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    await encrypt_existing_keys()

    # Expire cached state and re-read from DB
    db.expire_all()
    result = await db.execute(
        select(CertificateAuthority).where(CertificateAuthority.id == ca_id)
    )
    migrated_ca = result.scalar_one()
    assert not migrated_ca.private_key.startswith("-----BEGIN")
    assert EncryptionService.is_encrypted(migrated_ca.private_key)

    # Verify we can decrypt back to valid PEM
    decrypted = EncryptionService.decrypt_private_key(migrated_ca.private_key)
    assert decrypted.startswith("-----BEGIN")


@pytest.mark.asyncio
async def test_encrypt_existing_keys_idempotent(db: AsyncSession, monkeypatch):
    monkeypatch.setattr("app.db.session.engine", test_engine)

    # Create a CA with encryption disabled
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", None
    )
    ca_service = CAService(db)
    ca = await ca_service.create_ca(
        name="Idempotent CA",
        subject_dn="CN=Idempotent CA,O=Test,C=US",
        key_size=2048,
        valid_days=3650,
    )
    ca_id = ca.id

    # Enable encryption and run migration twice
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    await encrypt_existing_keys()

    db.expire_all()
    result = await db.execute(
        select(CertificateAuthority).where(CertificateAuthority.id == ca_id)
    )
    first_pass = result.scalar_one().private_key

    await encrypt_existing_keys()

    db.expire_all()
    result = await db.execute(
        select(CertificateAuthority).where(CertificateAuthority.id == ca_id)
    )
    second_pass = result.scalar_one().private_key

    assert first_pass == second_pass


@pytest.mark.asyncio
async def test_encrypt_existing_keys_fails_with_wrong_key(
    db: AsyncSession, monkeypatch
):
    monkeypatch.setattr("app.db.session.engine", test_engine)

    # Create a CA with encryption enabled using TEST_KEY
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", TEST_KEY
    )
    ca_service = CAService(db)
    await ca_service.create_ca(
        name="Wrong Key CA",
        subject_dn="CN=Wrong Key CA,O=Test,C=US",
        key_size=2048,
        valid_days=3650,
    )

    # Switch to a different key and try startup migration
    monkeypatch.setattr(
        "app.services.encryption.settings.PRIVATE_KEY_ENCRYPTION_KEY", OTHER_KEY
    )
    with pytest.raises(
        RuntimeError, match="PRIVATE_KEY_ENCRYPTION_KEY may have changed"
    ):
        await encrypt_existing_keys()
