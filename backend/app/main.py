from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

app = FastAPI(
    title="Kyiv Event Guide API",
    description="Backend API for managing sources, raw items, events moderation, bot submissions, and posting to Telegram.",
    version="1.0.0"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def on_startup():
    logger.info("Starting Kyiv Event Guide backend...")
    try:
        from app.db_seed import seed_data
        await seed_data()
    except Exception as e:
        logger.error(f"Error executing startup database seeder: {e}", exc_info=True)

@app.get("/")
def read_root():
    return {
        "app": "Kyiv Event Guide Aggregator API",
        "status": "healthy",
        "version": "1.0.0"
    }
