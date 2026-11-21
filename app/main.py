from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import BASE_DIR, settings
from app import models  # noqa: F401

FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="CompEdu API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Em desenvolvimento local o próprio FastAPI serve o frontend; na Vercel ele é servido pela CDN.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
