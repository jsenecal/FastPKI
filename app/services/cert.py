from datetime import UTC, datetime, timedelta
from typing import Optional, Tuple, Union

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.models import (
    Certificate, 
    CertificateAuthority,
    CertificateStatus,
    CertificateType,
    CRLEntry
)
from app.services.ca import CAService


class CertificateService:
    @staticmethod
    async def create_certificate(
        db: AsyncSession,
        ca_id: int,
        common_name: str,
        subject_dn: str,
        certificate_type: CertificateType,
        key_size: Optional[int] = None,
        valid_days: Optional[int] = None,
        include_private_key: bool = True,
    ) -> Certificate:
        """Create a new certificate signed by the specified CA."""
        key_size = key_size or settings.CERT_KEY_SIZE
        valid_days = valid_days or settings.CERT_DAYS
        
        # Get the CA
        ca = await db.get(CertificateAuthority, ca_id)
        if not ca:
            raise ValueError(f"Certificate Authority with ID {ca_id} not found")
        
        # Load CA private key and certificate
        ca_private_key = serialization.load_pem_private_key(
            ca.private_key.encode('utf-8'),
            password=None,
            backend=default_backend(),
        )
        ca_cert = x509.load_pem_x509_certificate(
            ca.certificate.encode('utf-8'),
            backend=default_backend(),
        )
        
        # Generate key pair for the new certificate if needed
        private_key_obj = None
        private_key_pem = None
        
        if include_private_key:
            private_key_obj, private_key_pem = CAService.generate_key_pair(key_size)
        else:
            # If no private key is needed, just generate a temporary one for the CSR
            private_key_obj, _ = CAService.generate_key_pair(key_size)
        
        # Parse subject DN
        subject = CAService.parse_subject_dn(subject_dn)
        
        # Create certificate
        now = datetime.now(UTC)
        not_before = now
        not_after = now + timedelta(days=valid_days)
        
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(ca_cert.subject)
        cert_builder = cert_builder.not_valid_before(not_before)
        cert_builder = cert_builder.not_valid_after(not_after)
        
        serial_number = x509.random_serial_number()
        cert_builder = cert_builder.serial_number(serial_number)
        cert_builder = cert_builder.public_key(private_key_obj.public_key())
        
        # Add extensions based on certificate type
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=(certificate_type == CertificateType.CA), path_length=None),
            critical=True,
        )
        
        key_usage = x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=(certificate_type == CertificateType.CA),
            crl_sign=(certificate_type == CertificateType.CA),
            encipher_only=False,
            decipher_only=False,
        )
        cert_builder = cert_builder.add_extension(key_usage, critical=True)
        
        # Add appropriate extended key usage based on type
        extended_key_usages = []
        if certificate_type == CertificateType.SERVER:
            extended_key_usages.append(ExtendedKeyUsageOID.SERVER_AUTH)
        elif certificate_type == CertificateType.CLIENT:
            extended_key_usages.append(ExtendedKeyUsageOID.CLIENT_AUTH)
        
        if extended_key_usages:
            cert_builder = cert_builder.add_extension(
                x509.ExtendedKeyUsage(extended_key_usages),
                critical=False,
            )
        
        # Add Subject Key Identifier
        cert_builder = cert_builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key_obj.public_key()),
            critical=False,
        )
        
        # Add Authority Key Identifier
        ca_ski = ca_cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
        cert_builder = cert_builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(ca_ski.value),
            critical=False,
        )
        
        # Sign the certificate
        certificate = cert_builder.sign(
            private_key=ca_private_key,
            algorithm=hashes.SHA256(),
            backend=default_backend(),
        )
        
        # Encode certificate to PEM
        certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
        
        # Create certificate database entry
        cert = Certificate(
            common_name=common_name,
            subject_dn=subject_dn,
            certificate_type=certificate_type,
            key_size=key_size,
            valid_days=valid_days,
            status=CertificateStatus.VALID,
            private_key=private_key_pem.decode('utf-8') if private_key_pem else None,
            certificate=certificate_pem.decode('utf-8'),
            serial_number=format(serial_number, 'x'),
            not_before=not_before,
            not_after=not_after,
            issuer_id=ca_id,
        )
        
        db.add(cert)
        await db.commit()
        await db.refresh(cert)
        
        return cert
    
    @staticmethod
    async def get_certificate(db: AsyncSession, cert_id: int) -> Optional[Certificate]:
        """Get a certificate by ID."""
        cert = await db.get(Certificate, cert_id)
        return cert
    
    @staticmethod
    async def list_certificates(
        db: AsyncSession, 
        ca_id: Optional[int] = None
    ) -> list[Certificate]:
        """List certificates, optionally filtered by CA ID."""
        if ca_id:
            query = select(Certificate).where(Certificate.issuer_id == ca_id)
        else:
            query = select(Certificate)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def revoke_certificate(
        db: AsyncSession, 
        cert_id: int, 
        reason: Optional[str] = None
    ) -> Optional[Certificate]:
        """Revoke a certificate by ID."""
        cert = await db.get(Certificate, cert_id)
        
        if not cert:
            return None
        
        # Update certificate status
        cert.status = CertificateStatus.REVOKED
        cert.revoked_at = datetime.now(UTC)
        
        # Add CRL entry
        crl_entry = CRLEntry(
            serial_number=cert.serial_number,
            revocation_date=cert.revoked_at,
            reason=reason,
            ca_id=cert.issuer_id,
        )
        
        db.add(crl_entry)
        await db.commit()
        await db.refresh(cert)
        
        return cert