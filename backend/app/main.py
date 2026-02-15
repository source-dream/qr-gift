import time
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.gift import router as gift_router
from app.api.logs import router as logs_router
from app.api.red_packet import router as red_packet_router
from app.api.redirect import router as redirect_router
from app.api.security import router as security_router
from app.api.system_config import router as system_config_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.response import ok
from app.models.log import AccessLog

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    latency = int((time.perf_counter() - start) * 1000)

    user_id = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            sub = payload.get("sub")
            user_id = int(sub) if sub else None
        except (JWTError, ValueError):
            user_id = None

    source = "scan" if request.url.path.startswith("/r/") else "admin"

    db = SessionLocal()
    try:
        db.add(
            AccessLog(
                user_id=user_id,
                source=source,
                path=request.url.path,
                method=request.method,
                ip=request.client.host if request.client else "",
                ua=request.headers.get("user-agent", "")[:255],
                status_code=response.status_code,
                latency_ms=latency,
            )
        )
        db.commit()
    finally:
        db.close()

    return response


@app.get("/healthz", tags=["system"])
def healthz() -> dict:
    return ok({"status": "up"})


app.include_router(auth_router)
app.include_router(gift_router)
app.include_router(red_packet_router)
app.include_router(security_router)
app.include_router(system_config_router)
app.include_router(logs_router)
app.include_router(dashboard_router)
app.include_router(redirect_router)


frontend_dist_dir = Path(__file__).resolve().parents[1] / "frontend_dist"


if frontend_dist_dir.exists():
    assets_dir = frontend_dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/favicon.ico", include_in_schema=False)
    def frontend_favicon() -> FileResponse:
        png_path = frontend_dist_dir / "favicon.png"
        ico_path = frontend_dist_dir / "favicon.ico"
        if png_path.exists():
            return FileResponse(png_path)
        if ico_path.exists():
            return FileResponse(ico_path)
        raise HTTPException(status_code=404, detail="Not Found")

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend_spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith(("api/", "r/", "claim/")):
            raise HTTPException(status_code=404, detail="Not Found")

        if not full_path:
            return FileResponse(frontend_dist_dir / "index.html")

        target = frontend_dist_dir / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(frontend_dist_dir / "index.html")
