import ipaddress
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import ExtendedKeyUsageOID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.models import (
    Certificate,
    CertificateAuthority,
    CertificateStatus,
    CertificateType,
    CRLEntry,
)
from app.services.ca import CAService
from app.services.encryption import EncryptionService
from app.services.exceptions import LeafCertNotAllowedError

UTC = ZoneInfo("UTC")


class CertificateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_certificate(
        self,
        ca_id: int,
        common_name: str,
        subject_dn: str,
        certificate_type: CertificateType,
        key_size: int | None = None,
        valid_days: int | None = None,
        include_private_key: bool = True,
        organization_id: int | None = None,
        created_by_user_id: int | None = None,
        base_url: str | None = None,
        san_dns_names: list[str] | None = None,
        san_ip_addresses: list[str] | None = None,
        san_email_addresses: list[str] | None = None,
        public_key: object | None = None,
    ) -> Certificate:
        """Create a new certificate signed by the specified CA."""
        key_size = key_size or settings.CERT_KEY_SIZE
        valid_days = valid_days or settings.CERT_DAYS

        # Get the CA
        ca = await self.db.get(CertificateAuthority, ca_id)
        if not ca:
            raise ValueError(f"No CA: {ca_id}")  # noqa: TRY003

        if not ca.allow_leaf_certs:
            raise LeafCertNotAllowedError(  # noqa: TRY003
                f"CA {ca_id} does not allow leaf certificate issuance"
            )

        # Load CA private key and certificate
        ca_key_pem = EncryptionService.decrypt_private_key(ca.private_key)
        ca_private_key = serialization.load_pem_private_key(
            ca_key_pem.encode("utf-8"),
            password=None,
        )
        ca_cert = x509.load_pem_x509_certificate(
            ca.certificate.encode("utf-8"),
        )

        # Get public key: from provided key (CSR case) or generate a new pair
        private_key_pem = None
        if public_key is not None:
            pub_key = public_key
        elif include_private_key:
            private_key_obj, private_key_pem = CAService.generate_key_pair(key_size)
            pub_key = private_key_obj.public_key()
        else:
            private_key_obj, _ = CAService.generate_key_pair(key_size)
            pub_key = private_key_obj.public_key()

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
        cert_builder = cert_builder.public_key(pub_key)

        # Add extensions based on certificate type
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(
                ca=(certificate_type == CertificateType.CA), path_length=None
            ),
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
        elif certificate_type == CertificateType.DUAL_PURPOSE:
            extended_key_usages.append(ExtendedKeyUsageOID.SERVER_AUTH)
            extended_key_usages.append(ExtendedKeyUsageOID.CLIENT_AUTH)

        if extended_key_usages:
            cert_builder = cert_builder.add_extension(
                x509.ExtendedKeyUsage(extended_key_usages),
                critical=False,
            )

        # Build Subject Alternative Name (SAN) extension
        if certificate_type != CertificateType.CA:
            san_names: list[x509.GeneralName] = []

            # Validate SAN type restrictions per cert type
            if certificate_type == CertificateType.SERVER:
                if san_email_addresses:
                    raise ValueError(  # noqa: TRY003
                        "Email SANs are not allowed for server certificates"
                    )
            elif certificate_type == CertificateType.CLIENT:
                if san_dns_names:
                    raise ValueError(  # noqa: TRY003
                        "DNS SANs are not allowed for client certificates"
                    )
                if san_ip_addresses:
                    raise ValueError(  # noqa: TRY003
                        "IP SANs are not allowed for client certificates"
                    )

            # Auto-populate from common_name if no explicit SANs provided
            if certificate_type in (
                CertificateType.SERVER,
                CertificateType.DUAL_PURPOSE,
            ):
                if not san_dns_names:
                    san_dns_names = [common_name]
            elif (
                certificate_type == CertificateType.CLIENT
                and not san_email_addresses
                and re.match(r"^[^@]+@[^@]+\.[^@]+$", common_name)
            ):
                san_email_addresses = [common_name]

            # Add DNS names
            if san_dns_names:
                for name in san_dns_names:
                    san_names.append(x509.DNSName(name))

            # Add IP addresses
            if san_ip_addresses:
                for addr in san_ip_addresses:
                    san_names.append(x509.IPAddress(ipaddress.ip_address(addr)))

            # Add email addresses
            if san_email_addresses:
                for email in san_email_addresses:
                    san_names.append(x509.RFC822Name(email))

            if san_names:
                cert_builder = cert_builder.add_extension(
                    x509.SubjectAlternativeName(san_names),
                    critical=False,
                )

        # Add Subject Key Identifier
        cert_builder = cert_builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(pub_key),
            critical=False,
        )

        # Add Authority Key Identifier
        ca_ski = ca_cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
        cert_builder = cert_builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                ca_ski.value
            ),
            critical=False,
        )

        # Add CDP and AIA extensions pointing to issuing CA's public URLs
        if base_url is not None:
            ca_urls = CAService.get_public_urls(ca, base_url)
            cert_builder = cert_builder.add_extension(
                x509.CRLDistributionPoints(
                    [
                        x509.DistributionPoint(
                            full_name=[x509.UniformResourceIdentifier(ca_urls["crl"])],
                            relative_name=None,
                            crl_issuer=None,
                            reasons=None,
                        )
                    ]
                ),
                critical=False,
            )
            cert_builder = cert_builder.add_extension(
                x509.AuthorityInformationAccess(
                    [
                        x509.AccessDescription(
                            x509.oid.AuthorityInformationAccessOID.CA_ISSUERS,
                            x509.UniformResourceIdentifier(ca_urls["ca_cert"]),
                        )
                    ]
                ),
                critical=False,
            )

        # Sign the certificate
        certificate = cert_builder.sign(
            private_key=ca_private_key,
            algorithm=hashes.SHA256(),
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
            private_key=EncryptionService.encrypt_private_key(
                private_key_pem.decode("utf-8")
            )
            if private_key_pem
            else None,
            certificate=certificate_pem.decode("utf-8"),
            serial_number=format(serial_number, "x"),
            not_before=not_before,
            not_after=not_after,
            issuer_id=ca_id,
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
        )

        self.db.add(cert)
        await self.db.commit()
        await self.db.refresh(cert)

        return cert

    @staticmethod
    def parse_csr(csr_pem: str) -> x509.CertificateSigningRequest:
        """Parse and verify a PEM-encoded CSR."""
        try:
            csr = x509.load_pem_x509_csr(csr_pem.encode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid CSR: {e}") from e  # noqa: TRY003
        if not csr.is_signature_valid:
            raise ValueError("CSR signature verification failed")  # noqa: TRY003
        return csr

    @staticmethod
    def extract_csr_san_names(
        csr: x509.CertificateSigningRequest,
    ) -> tuple[list[str], list[str], list[str]]:
        """Extract DNS names, IP addresses, and email addresses from a CSR's SAN."""
        dns_names: list[str] = []
        ip_addresses: list[str] = []
        email_addresses: list[str] = []
        try:
            san_ext = csr.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            )
            dns_names = san_ext.value.get_values_for_type(x509.DNSName)
            ip_addresses = [
                str(ip) for ip in san_ext.value.get_values_for_type(x509.IPAddress)
            ]
            email_addresses = san_ext.value.get_values_for_type(x509.RFC822Name)
        except x509.ExtensionNotFound:
            pass
        return dns_names, ip_addresses, email_addresses

    async def sign_csr(
        self,
        csr_pem: str,
        ca_id: int,
        certificate_type: CertificateType,
        valid_days: int | None = None,
        common_name: str | None = None,
        subject_dn: str | None = None,
        san_dns_names: list[str] | None = None,
        san_ip_addresses: list[str] | None = None,
        san_email_addresses: list[str] | None = None,
        organization_id: int | None = None,
        created_by_user_id: int | None = None,
        base_url: str | None = None,
    ) -> Certificate:
        """Sign a CSR. Extracts defaults from the CSR; explicit params override."""
        csr = self.parse_csr(csr_pem)

        # Extract defaults from CSR
        csr_cn_attrs = csr.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
        csr_cn = csr_cn_attrs[0].value if csr_cn_attrs else ""
        oid_to_short = {
            x509.oid.NameOID.COMMON_NAME: "CN",
            x509.oid.NameOID.ORGANIZATION_NAME: "O",
            x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME: "OU",
            x509.oid.NameOID.COUNTRY_NAME: "C",
            x509.oid.NameOID.STATE_OR_PROVINCE_NAME: "ST",
            x509.oid.NameOID.LOCALITY_NAME: "L",
        }
        csr_subject_parts = []
        for attr in csr.subject:
            short = oid_to_short.get(attr.oid, attr.oid.dotted_string)
            csr_subject_parts.append(f"{short}={attr.value}")
        csr_subject_dn = ",".join(csr_subject_parts)
        csr_dns, csr_ips, csr_emails = self.extract_csr_san_names(csr)

        # Apply overrides
        effective_cn = common_name or csr_cn
        effective_subject_dn = subject_dn or csr_subject_dn
        effective_dns = (
            san_dns_names if san_dns_names is not None else (csr_dns or None)
        )
        effective_ips = (
            san_ip_addresses if san_ip_addresses is not None else (csr_ips or None)
        )
        effective_emails = (
            san_email_addresses
            if san_email_addresses is not None
            else (csr_emails or None)
        )

        if not effective_cn:
            raise ValueError("No common name in CSR or request")  # noqa: TRY003

        return await self.create_certificate(
            ca_id=ca_id,
            common_name=effective_cn,
            subject_dn=effective_subject_dn,
            certificate_type=certificate_type,
            valid_days=valid_days,
            include_private_key=False,
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            base_url=base_url,
            san_dns_names=effective_dns,
            san_ip_addresses=effective_ips,
            san_email_addresses=effective_emails,
            public_key=csr.public_key(),
        )

    async def get_certificate(self, cert_id: int) -> Certificate | None:
        """Get a certificate by ID."""
        cert = await self.db.get(Certificate, cert_id)
        return cert

    async def list_certificates(
        self,
        ca_id: int | None = None,
        organization_id: int | None = None,
    ) -> list[Certificate]:
        """List certificates, optionally filtered by CA ID and/or organization."""
        query = select(Certificate)
        if ca_id:
            query = query.where(Certificate.issuer_id == ca_id)
        if organization_id is not None:
            query = query.where(Certificate.organization_id == organization_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def revoke_certificate(
        self, cert_id: int, reason: str | None = None
    ) -> Certificate | None:
        """Revoke a certificate by ID."""
        cert = await self.db.get(Certificate, cert_id)

        if not cert:
            return None

        if cert.status == CertificateStatus.REVOKED:
            raise ValueError("Certificate is already revoked")  # noqa: TRY003

        if cert.issuer_id is None:
            raise ValueError("Certificate has no issuer and cannot be revoked")  # noqa: TRY003

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

        self.db.add(crl_entry)
        await self.db.commit()
        await self.db.refresh(cert)

        return cert
