import re
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.models import CertificateAuthority
from app.services.encryption import EncryptionService
from app.services.exceptions import HasDependentsError

UTC = ZoneInfo("UTC")


class CAService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_key_pair(key_size: int = 2048) -> tuple[rsa.RSAPrivateKey, bytes]:
        """Generate RSA key pair with key object and PEM-encoded private key."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
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
        for part in re.split(r"(?<!\\),", subject_dn):
            key, value = part.strip().split("=", 1)
            parts[key.strip()] = value.strip().replace("\\,", ",")

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

    async def create_ca(
        self,
        name: str,
        subject_dn: str,
        description: Optional[str] = None,
        key_size: Optional[int] = None,
        valid_days: Optional[int] = None,
        organization_id: Optional[int] = None,
        created_by_user_id: Optional[int] = None,
        parent_ca_id: Optional[int] = None,
        path_length: Optional[int] = None,
        allow_leaf_certs: Optional[bool] = None,
    ) -> CertificateAuthority:
        """Create a new Certificate Authority (root or intermediate)."""
        key_size = key_size or settings.CA_KEY_SIZE
        valid_days = valid_days or settings.CA_CERT_DAYS

        # Generate key pair
        private_key, private_key_pem = CAService.generate_key_pair(key_size)

        # Parse subject DN
        subject = CAService.parse_subject_dn(subject_dn)

        now = datetime.now(UTC)
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.not_valid_before(now)
        cert_builder = cert_builder.not_valid_after(now + timedelta(days=valid_days))
        cert_builder = cert_builder.serial_number(x509.random_serial_number())
        cert_builder = cert_builder.public_key(private_key.public_key())

        parent_ca: Optional[CertificateAuthority] = None
        if parent_ca_id is not None:
            # Intermediate CA: signed by parent
            parent_ca = await self.db.get(CertificateAuthority, parent_ca_id)
            if not parent_ca:
                raise ValueError(f"Parent CA with ID {parent_ca_id} not found")  # noqa: TRY003

            # Load parent private key and certificate
            parent_key_pem = EncryptionService.decrypt_private_key(
                parent_ca.private_key
            )
            parent_private_key = serialization.load_pem_private_key(
                parent_key_pem.encode("utf-8"),
                password=None,
            )
            parent_cert = x509.load_pem_x509_certificate(
                parent_ca.certificate.encode("utf-8"),
            )

            # Validate parent's BasicConstraints
            try:
                bc_ext = parent_cert.extensions.get_extension_for_class(
                    x509.BasicConstraints
                )
                bc = bc_ext.value
            except x509.ExtensionNotFound:
                raise ValueError("Parent CA certificate does not have BasicConstraints")  # noqa: B904, TRY003

            if not bc.ca:
                raise ValueError("Parent certificate is not a CA")  # noqa: TRY003

            if bc.path_length is not None and bc.path_length < 1:
                raise ValueError(  # noqa: TRY003
                    f"Parent CA path_length ({bc.path_length}) does not allow sub-CAs"
                )

            # Calculate effective path_length for the new intermediate
            effective_path_length: Optional[int]
            if bc.path_length is not None:
                max_child_path_length = bc.path_length - 1
                if path_length is not None:
                    if path_length > max_child_path_length:
                        raise ValueError(  # noqa: TRY003
                            f"Requested path_length ({path_length}) exceeds maximum "
                            f"allowed by parent ({max_child_path_length})"
                        )
                    effective_path_length = path_length
                else:
                    effective_path_length = max_child_path_length
            else:
                effective_path_length = path_length

            # Set issuer from parent
            cert_builder = cert_builder.issuer_name(parent_cert.subject)
            signing_key = parent_private_key
        else:
            # Root CA: self-signed
            cert_builder = cert_builder.issuer_name(subject)
            signing_key = private_key
            effective_path_length = path_length

        # Add CA extensions
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=effective_path_length),
            critical=True,
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

        # Add AuthorityKeyIdentifier for intermediate CAs
        if parent_ca_id is not None:
            parent_ski = parent_cert.extensions.get_extension_for_class(
                x509.SubjectKeyIdentifier
            )
            cert_builder = cert_builder.add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                    parent_ski.value
                ),
                critical=False,
            )

        # Sign the certificate
        certificate = cert_builder.sign(
            private_key=signing_key,
            algorithm=hashes.SHA256(),
        )

        # Encode certificate to PEM
        certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)

        # Determine allow_leaf_certs value
        effective_allow_leaf_certs = (
            allow_leaf_certs if allow_leaf_certs is not None else True
        )

        # Create CA database entry
        ca = CertificateAuthority(
            name=name,
            description=description,
            subject_dn=subject_dn,
            key_size=key_size,
            valid_days=valid_days,
            private_key=EncryptionService.encrypt_private_key(
                private_key_pem.decode("utf-8")
            ),
            certificate=certificate_pem.decode("utf-8"),
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            parent_ca_id=parent_ca_id,
            path_length=effective_path_length,
            allow_leaf_certs=effective_allow_leaf_certs,
        )

        self.db.add(ca)

        # Auto-set parent's allow_leaf_certs to False when creating an intermediate CA
        if parent_ca is not None:
            parent_ca.allow_leaf_certs = False

        await self.db.commit()
        await self.db.refresh(ca)

        return ca

    async def get_ca(self, ca_id: int) -> Optional[CertificateAuthority]:
        """Get a Certificate Authority by ID."""
        ca = await self.db.get(CertificateAuthority, ca_id)
        return ca

    async def list_cas(
        self, organization_id: Optional[int] = None
    ) -> list[CertificateAuthority]:
        """List Certificate Authorities, optionally filtered by organization."""
        query = select(CertificateAuthority)
        if organization_id is not None:
            query = query.where(CertificateAuthority.organization_id == organization_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_ca(self, ca_id: int) -> bool:
        """Delete a Certificate Authority by ID.

        Raises HasDependentsError if the CA has child CAs.
        """
        ca = await self.db.get(CertificateAuthority, ca_id)
        if not ca:
            return False

        # Check for child CAs
        children = await self.get_child_cas(ca_id)
        if children:
            raise HasDependentsError(  # noqa: TRY003
                f"CA {ca_id} has {len(children)} child CA(s) and cannot be deleted"
            )

        await self.db.delete(ca)
        await self.db.commit()
        return True

    async def get_ca_chain(self, ca_id: int) -> list[CertificateAuthority]:
        """Get the CA chain from the given CA up to the root.

        Returns an ordered list starting with the given CA and ending at the root.
        """
        chain: list[CertificateAuthority] = []
        current_id: Optional[int] = ca_id
        while current_id is not None:
            ca = await self.db.get(CertificateAuthority, current_id)
            if not ca:
                break
            chain.append(ca)
            current_id = ca.parent_ca_id
        return chain

    async def get_child_cas(self, ca_id: int) -> list[CertificateAuthority]:
        """Get direct child CAs of the given CA."""
        query = select(CertificateAuthority).where(
            CertificateAuthority.parent_ca_id == ca_id
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
