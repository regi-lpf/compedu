from fastapi import APIRouter

from app.routers import announcements, auth, classes, dashboard, records, students, users

router = APIRouter(prefix="/api")
for module in (auth, users, classes, students, records, announcements, dashboard):
    router.include_router(module.router)
