from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.models import CertificateAuthority

UTC = ZoneInfo("UTC")


class CAService:
    @staticmethod
    def generate_key_pair(key_size: int = 2048) -> tuple[rsa.RSAPrivateKey, bytes]:
        """Generate RSA key pair with key object and PEM-encoded private key."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend(),
        )

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return private_key, private_key_pem

    @staticmethod
    def parse_subject_dn(subject_dn: str) -> x509.Name:
        """Parse a subject DN string into a cryptography Name object."""
        parts = {}
        for part in subject_dn.split(","):
            key, value = part.strip().split("=", 1)
            parts[key.strip()] = value.strip()

        name_attributes = []

        if "CN" in parts:
            name_attributes.append(x509.NameAttribute(NameOID.COMMON_NAME, parts["CN"]))
        if "O" in parts:
            name_attributes.append(
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, parts["O"])
            )
        if "OU" in parts:
            name_attributes.append(
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, parts["OU"])
            )
        if "C" in parts:
            name_attributes.append(x509.NameAttribute(NameOID.COUNTRY_NAME, parts["C"]))
        if "ST" in parts:
            name_attributes.append(
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, parts["ST"])
            )
        if "L" in parts:
            name_attributes.append(
                x509.NameAttribute(NameOID.LOCALITY_NAME, parts["L"])
            )

        return x509.Name(name_attributes)

    @staticmethod
    async def create_ca(
        db: AsyncSession,
        name: str,
        subject_dn: str,
        description: Optional[str] = None,
        key_size: Optional[int] = None,
        valid_days: Optional[int] = None,
    ) -> CertificateAuthority:
        """Create a new Certificate Authority."""
        key_size = key_size or settings.CA_KEY_SIZE
        valid_days = valid_days or settings.CA_CERT_DAYS

        # Generate key pair
        private_key, private_key_pem = CAService.generate_key_pair(key_size)

        # Parse subject DN
        subject = CAService.parse_subject_dn(subject_dn)

        # Create CA certificate
        now = datetime.now(UTC)
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(subject)  # Self-signed
        cert_builder = cert_builder.not_valid_before(now)
        cert_builder = cert_builder.not_valid_after(now + timedelta(days=valid_days))
        cert_builder = cert_builder.serial_number(x509.random_serial_number())
        cert_builder = cert_builder.public_key(private_key.public_key())

        # Add CA extensions
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True
        )
        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        cert_builder = cert_builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        )

        # Sign the certificate
        certificate = cert_builder.sign(
            private_key=private_key,
            algorithm=hashes.SHA256(),
            backend=default_backend(),
        )

        # Encode certificate to PEM
        certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)

        # Create CA database entry
        ca = CertificateAuthority(
            name=name,
            description=description,
            subject_dn=subject_dn,
            key_size=key_size,
            valid_days=valid_days,
            private_key=private_key_pem.decode("utf-8"),
            certificate=certificate_pem.decode("utf-8"),
        )

        db.add(ca)
        await db.commit()
        await db.refresh(ca)

        return ca

    @staticmethod
    async def get_ca(db: AsyncSession, ca_id: int) -> Optional[CertificateAuthority]:
        """Get a Certificate Authority by ID."""
        ca = await db.get(CertificateAuthority, ca_id)
        return ca

    @staticmethod
    async def list_cas(db: AsyncSession) -> list[CertificateAuthority]:
        """List all Certificate Authorities."""
        result = await db.execute(select(CertificateAuthority))
        return result.scalars().all()

    @staticmethod
    async def delete_ca(db: AsyncSession, ca_id: int) -> bool:
        """Delete a Certificate Authority by ID."""
        ca = await db.get(CertificateAuthority, ca_id)
        if ca:
            await db.delete(ca)
            await db.commit()
            return True
        return False
