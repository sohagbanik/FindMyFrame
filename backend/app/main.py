from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.collections import router as collections_router
from app.config import settings


app = FastAPI(title="FindMyFrame API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(collections_router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "service": "findmyframe-api"}
