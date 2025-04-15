from fastapi import APIRouter

from app.api import ca, certs, export

api_router = APIRouter()
api_router.include_router(ca.router, prefix="/cas", tags=["certificate-authorities"])
api_router.include_router(certs.router, prefix="/certificates", tags=["certificates"])
api_router.include_router(export.router, prefix="/export", tags=["export"])