from fastapi import APIRouter
from app.api.endpoints import auth, sources, raw_items, events, submissions, posts, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(raw_items.router, prefix="/raw-items", tags=["raw-items"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
