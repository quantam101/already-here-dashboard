import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Import routers
from routes import (
    advisor,
    agents,
    analytics,
    approvals,
    audit,
    auth,
    books,
    builds,
    cash_command,
    content,
    content_factory,
    content_sync,
    cost,
    cycle,
    dasi,
    deployments,
    distillation,
    gmail_scanner,
    governance,
    growth_vault,
    health,
    hooks,
    lcac,
    ledger,
    payments,
    product_factory,
    proposals,
    publishing,
    revenue,
    revenue_equation,
    scout,
    secrets,
    sovereign,
    system,
    video,
    voicelab,
    work_orders,
)
from services.scheduler_service import start_scheduler, stop_scheduler

# Storage backend — Mongo (preview/dev) or SQLite (1GB-RAM production host)
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "mongodb").lower()
if STORAGE_BACKEND == "sqlite":
    from services.sqlite_db import SqliteClient
    sqlite_path = os.environ.get("SQLITE_PATH", str(ROOT_DIR / "data" / "command_os.db"))
    client = SqliteClient(sqlite_path)
    db = client[os.environ.get("DB_NAME", "command_os")]
    logging.info(f"Using SQLite backend at {sqlite_path}")
else:
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "command_os_prod")
    if not mongo_url:
        raise RuntimeError(
            "MONGO_URL environment variable is required when STORAGE_BACKEND=mongodb. "
            "Set it in .env or docker-compose.yml, or use STORAGE_BACKEND=sqlite."
        )
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    logging.info("Using MongoDB backend at %s / %s", mongo_url.split("@")[-1], db_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = db
    app.state.storage_backend = STORAGE_BACKEND
    logging.info(f"Database connected ({STORAGE_BACKEND})")
    start_scheduler(db)

    # Pre-warm heavy local generative models so first render isn't slow.
    # Default ON; disable with VIDEO_PREWARM=false (for tight-memory hosts).
    if os.environ.get("VIDEO_PREWARM", "true").lower() not in {"false", "0", "off"}:
        import asyncio as _aio
        _aio.create_task(_prewarm_local_models())

    yield
    stop_scheduler()
    client.close()
    logging.info("Database connection closed")



async def _prewarm_local_models() -> None:
    """Load Coqui XTTS-v2 + transformers MusicGen into memory at boot so the
    first render doesn't pay the 47-110s cold-start. Runs in a background
    task so the HTTP server is reachable while the models warm up.
    """
    import asyncio
    log = logging.getLogger("video.prewarm")
    try:
        from services.video import local_music, local_voice
        log.info("pre-warming Coqui XTTS-v2 …")
        await asyncio.get_running_loop().run_in_executor(None, local_voice._load_tts)
        log.info("Coqui XTTS-v2 loaded.")
    except Exception as e:
        log.warning("Coqui pre-warm skipped: %s", str(e)[:200])
    try:
        await asyncio.get_running_loop().run_in_executor(None, local_music._load)
        log.info("MusicGen loaded.")
    except Exception as e:
        log.warning("MusicGen pre-warm skipped: %s", str(e)[:200])

app = FastAPI(
    title="Already Here Command OS",
    description="ASI-governed, 24/7 autonomous revenue automation engine",
    version="2.0.0",
    lifespan=lifespan,
)

api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return {
        "message": "Already Here Command OS — ASI Revenue Automation Engine",
        "version": "2.0.0",
        "status": "operational",
        "governance": "sovereign-v1",
    }

# Include all module routers
api_router.include_router(revenue.router, prefix="/revenue", tags=["revenue"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
api_router.include_router(content_factory.router, prefix="/studio", tags=["content-factory"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(builds.router, prefix="/builds", tags=["builds"])
api_router.include_router(deployments.router, prefix="/deployments", tags=["deployments"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(ledger.router, prefix="/ledger", tags=["ledger"])
api_router.include_router(publishing.router, prefix="/publishing", tags=["publishing"])
api_router.include_router(scout.router, prefix="/scout", tags=["scout"])
api_router.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
api_router.include_router(cycle.router, prefix="/cycle", tags=["cycle"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(advisor.router, prefix="/advisor", tags=["advisor"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(books.router, prefix="/books", tags=["books"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(secrets.router, prefix="/secrets", tags=["secrets"])
api_router.include_router(cost.router, prefix="/cost", tags=["cost"])
api_router.include_router(lcac.router, prefix="/lifelong-catch-correct", tags=["lcac"])
api_router.include_router(distillation.router, prefix="/distillation", tags=["distillation"])
api_router.include_router(governance.router, prefix="/governance", tags=["governance"])
api_router.include_router(revenue_equation.router, prefix="/revenue-equation", tags=["revenue-equation"])
api_router.include_router(video.router, prefix="/video", tags=["video"])
api_router.include_router(hooks.router, prefix="/hooks", tags=["hooks"])
api_router.include_router(voicelab.router, prefix="/voicelab", tags=["voicelab"])
api_router.include_router(dasi.router, prefix="/dasi", tags=["dasi"])
api_router.include_router(sovereign.router, prefix="/sovereign", tags=["sovereign"])
api_router.include_router(work_orders.router, prefix="/work-orders", tags=["work-orders"])
api_router.include_router(cash_command.router, prefix="/cash-command", tags=["cash-command"])
api_router.include_router(gmail_scanner.router, prefix="/gmail", tags=["gmail"])
api_router.include_router(growth_vault.router, prefix="/growth-vault", tags=["growth-vault"])
api_router.include_router(product_factory.router, prefix="/products", tags=["products"])
api_router.include_router(content_sync.router, prefix="/content-sync", tags=["content-sync"])

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
