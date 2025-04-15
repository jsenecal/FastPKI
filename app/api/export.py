from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models import Certificate, CertificateAuthority
from app.services.ca import CAService
from app.services.cert import CertificateService

router = APIRouter()


@router.get("/ca/{ca_id}/certificate")
async def export_ca_certificate(
    ca_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export a CA certificate in PEM format.
    """
    ca = await CAService.get_ca(db, ca_id)
    if not ca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate Authority with ID {ca_id} not found",
        )
    
    return Response(
        content=ca.certificate,
        media_type="application/x-pem-file",
        headers={
            "Content-Disposition": f"attachment; filename=ca_{ca_id}_certificate.pem"
        }
    )


@router.get("/ca/{ca_id}/private-key")
async def export_ca_private_key(
    ca_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export a CA private key in PEM format.
    """
    ca = await CAService.get_ca(db, ca_id)
    if not ca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate Authority with ID {ca_id} not found",
        )
    
    return Response(
        content=ca.private_key,
        media_type="application/x-pem-file",
        headers={
            "Content-Disposition": f"attachment; filename=ca_{ca_id}_private_key.pem"
        }
    )


@router.get("/certificate/{cert_id}")
async def export_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export a certificate in PEM format.
    """
    cert = await CertificateService.get_certificate(db, cert_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {cert_id} not found",
        )
    
    return Response(
        content=cert.certificate,
        media_type="application/x-pem-file",
        headers={
            "Content-Disposition": f"attachment; filename=certificate_{cert_id}.pem"
        }
    )


@router.get("/certificate/{cert_id}/private-key")
async def export_certificate_private_key(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export a certificate's private key in PEM format.
    """
    cert = await CertificateService.get_certificate(db, cert_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {cert_id} not found",
        )
    
    if not cert.private_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {cert_id} does not have a private key",
        )
    
    return Response(
        content=cert.private_key,
        media_type="application/x-pem-file",
        headers={
            "Content-Disposition": f"attachment; filename=certificate_{cert_id}_private_key.pem"
        }
    )


@router.get("/certificate/{cert_id}/chain")
async def export_certificate_chain(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export a certificate with its complete certificate chain in PEM format.
    """
    cert = await CertificateService.get_certificate(db, cert_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {cert_id} not found",
        )
    
    # Get the certificate chain
    chain = []
    chain.append(cert.certificate)
    
    # Add issuer certificates
    current_issuer_id = cert.issuer_id
    while current_issuer_id is not None:
        issuer = await CAService.get_ca(db, current_issuer_id)
        if not issuer:
            # If issuer is a certificate (not a CA)
            issuer_cert = await CertificateService.get_certificate(db, current_issuer_id)
            if issuer_cert:
                chain.append(issuer_cert.certificate)
                current_issuer_id = issuer_cert.issuer_id
            else:
                break
        else:
            # If issuer is a CA
            chain.append(issuer.certificate)
            # CA doesn't have an issuer field, so we're done
            break
    
    # Join the chain
    chain_pem = "\n".join(chain)
    
    return Response(
        content=chain_pem,
        media_type="application/x-pem-file",
        headers={
            "Content-Disposition": f"attachment; filename=certificate_{cert_id}_chain.pem"
        }
    )