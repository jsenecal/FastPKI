from fastapi import APIRouter

from app.api import auth, ca, certs, export, organizations, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(ca.router, prefix="/cas", tags=["certificate-authorities"])
api_router.include_router(certs.router, prefix="/certificates", tags=["certificates"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
