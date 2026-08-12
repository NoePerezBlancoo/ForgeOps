from fastapi import APIRouter

from app.ai.routes import router as ai_router
from app.assets.routes import router as assets_router
from app.audit.routes import router as audit_router
from app.auth.routes import router as auth_router
from app.companies.routes import router as companies_router
from app.dashboard.routes import router as dashboard_router
from app.documents.routes import router as documents_router
from app.incidents.routes import router as incidents_router
from app.inventory.routes import router as inventory_router
from app.maintenance.routes import router as maintenance_router
from app.plants.routes import router as plants_router
from app.users.routes import router as users_router
from app.work_orders.routes import router as work_orders_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(companies_router)
api_router.include_router(plants_router)
api_router.include_router(assets_router)
api_router.include_router(incidents_router)
api_router.include_router(work_orders_router)
api_router.include_router(maintenance_router)
api_router.include_router(inventory_router)
api_router.include_router(documents_router)
api_router.include_router(ai_router)
api_router.include_router(audit_router)
api_router.include_router(dashboard_router)
