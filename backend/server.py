from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import routers
from routes import revenue, content, agents, builds, deployments, audit, approvals, health, content_factory, ledger, publishing, scout, proposals, cycle, payments, analytics, advisor, auth, books
from services.scheduler_service import start_scheduler, stop_scheduler

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db = db
    app.state.mongo_client = client
    logging.info("Database connected")
    start_scheduler(db)
    yield
    # Shutdown
    stop_scheduler()
    client.close()
    logging.info("Database connection closed")

# Create the main app
app = FastAPI(lifespan=lifespan)

# Create API router
api_router = APIRouter(prefix="/api")

# Health check route
@api_router.get("/")
async def root():
    return {"message": "Already Here Command OS - Revenue Automation Engine", "status": "operational"}

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

# Include router in main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)