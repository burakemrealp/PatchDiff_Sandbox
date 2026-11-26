import asyncio
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import parse_cors_origins, settings
from app.core.database import SessionLocal, get_db
from app.core.redis_client import check_redis_health
from app.core.versioning import build_item_icon_url
from app.models.entities import Champion, Item, ItemSnapshot, PatchVersion
from app.api.routes import router as api_router
from app.services.locale_service import get_ddragon_localization, normalize_locale
from app.services.patch_sync_orchestrator import PatchSyncOrchestrator

logger = logging.getLogger(__name__)


async def _periodic_patch_sync_loop() -> None:
    """Periodically checks Riot Data Dragon in the background for new LoL patches."""
    interval_sec = max(60, settings.AUTO_SYNC_INTERVAL_MINUTES * 60)
    while True:
        try:
            def _run_once():
                db = SessionLocal()
                try:
                    return PatchSyncOrchestrator.sync_if_needed(db, force=False)
                finally:
                    db.close()

            res = await asyncio.to_thread(_run_once)
            logger.info("Automatic background patch check completed: %s", res.get("status"))
        except Exception:
            logger.exception("Error occurred during automatic patch check.")
        await asyncio.sleep(interval_sec)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if settings.AUTO_SYNC_ENABLED:
        task = asyncio.create_task(_periodic_patch_sync_loop())
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="PatchDiff Sandbox API",
    description="Semantic League of Legends patch note parser, deterministic combat simulator, and AI build & rune optimizer.",
    version="2.0.0",
    lifespan=lifespan,
)

cors_origins = parse_cors_origins(settings.CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=(cors_origins != ["*"]),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount v1 API endpoints (/parse-patch, /simulate, /recommend-builds, /patches/*, /feedback)
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Logs unexpected server errors internally and returns a safe JSON response to clients."""
    logger.exception("Unhandled server error (%s %s)", request.method, request.url.path)
    content = {
        "status": "error",
        "message": "An unexpected internal server error occurred.",
    }
    if settings.DEBUG:
        content["detail"] = str(exc)
    return JSONResponse(status_code=500, content=content)


@app.get("/", tags=["System"])
def root():
    return {
        "service": "PatchDiff Sandbox API",
        "version": "2.0.0",
        "status": "online",
        "docs_url": "/docs",
        "llm_provider": settings.LLM_PROVIDER,
    }


@app.get("/api/v1/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """Reports health status for PostgreSQL and Redis connections."""
    pg_ok = False
    try:
        db.execute(text("SELECT 1"))
        pg_ok = True
    except Exception:
        pg_ok = False

    redis_ok = check_redis_health()

    overall_status = "healthy" if (pg_ok and redis_ok) else "degraded"
    return {
        "status": overall_status,
        "services": {
            "postgresql": "connected" if pg_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected",
        },
        "active_llm_provider": settings.LLM_PROVIDER,
    }


@app.get("/api/v1/champions", tags=["Catalog"])
def list_champions(
    lang: str = Query(default="tr_TR", description="Official League of Legends locale code (e.g., tr_TR, en_US, de_DE)"),
    db: Session = Depends(get_db),
):
    """Lists all database champions localized to the requested official LoL locale."""
    champs = db.query(Champion).order_by(Champion.key.asc()).all()
    latest_patch = db.query(PatchVersion).filter_by(is_latest=True).first()
    latest_ver = latest_patch.version if latest_patch else None
    riot_locale, _, _ = normalize_locale(lang)
    loc = get_ddragon_localization(latest_ver, riot_locale) or {}
    champ_loc = loc.get("champions") or {}

    return [
        {
            "key": c.key,
            "name": (champ_loc.get(c.key) or {}).get("name") or c.name,
            "title": (champ_loc.get(c.key) or {}).get("title") or c.title,
            "patch_version": c.patch_version,
            "base_stats": c.base_stats,
        }
        for c in champs
    ]


@app.get("/api/v1/items", tags=["Catalog"])
def list_items(
    lang: str = Query(default="tr_TR", description="Official League of Legends locale code (e.g., tr_TR, en_US, de_DE)"),
    db: Session = Depends(get_db),
):
    """Lists all reference items with official Riot Data Dragon icons and localized names."""
    items = db.query(Item).order_by(Item.gold_total.desc()).all()
    latest_patch = db.query(PatchVersion).filter_by(is_latest=True).first()
    latest_ver = latest_patch.version if latest_patch else None
    riot_locale, _, _ = normalize_locale(lang)
    loc = get_ddragon_localization(latest_ver, riot_locale) or {}
    item_loc = loc.get("items") or {}

    icon_map: dict[str, str] = {}
    if latest_ver:
        snaps = (
            db.query(ItemSnapshot.item_id, ItemSnapshot.icon_url)
            .filter(ItemSnapshot.patch_version == latest_ver)
            .all()
        )
        icon_map = {iid: url for iid, url in snaps if url}

    return [
        {
            "item_id": i.item_id,
            "name": item_loc.get(i.item_id) or i.name,
            "gold_total": i.gold_total,
            "stats": i.stats,
            "icon_url": icon_map.get(i.item_id) or build_item_icon_url(latest_ver, i.item_id),
        }
        for i in items
    ]
