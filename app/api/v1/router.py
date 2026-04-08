"""
Central API Router (v1)
=======================
Aggregates all domain routers under the /api/v1 prefix.
"""

from fastapi import APIRouter
from app.api.v1 import auth, users, financial_records, dashboard

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(financial_records.router)
api_router.include_router(dashboard.router)
