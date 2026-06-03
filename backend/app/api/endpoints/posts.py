from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.schemas.schemas import Post
from app.models.models import Post as DB_Post, AdminUser
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[Post])
async def list_posts(
    status: Optional[str] = Query(None, description="Filter by status (scheduled, published, failed)"),
    post_type: Optional[str] = Query(None, description="Filter by type (single_event, daily_digest, weekend_digest, ad)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    stmt = select(DB_Post)
    if status:
        stmt = stmt.where(DB_Post.status == status)
    if post_type:
        stmt = stmt.where(DB_Post.post_type == post_type)
        
    stmt = stmt.order_by(DB_Post.scheduled_at.desc()).offset(skip).limit(limit)
    q = await db.execute(stmt)
    return q.scalars().all()

@router.post("/daily-digest")
async def trigger_daily_digest(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    from app.services.publisher import generate_and_publish_daily_digest
    # Generate and publish today's digest immediately
    post, error = await generate_and_publish_daily_digest(db)
    if not post:
        raise HTTPException(status_code=400, detail=f"Could not generate digest: {error}")
    
    return {"status": "success", "post_id": post.id, "text": post.text}

@router.post("/weekend-digest")
async def trigger_weekend_digest(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    from app.services.publisher import generate_and_publish_weekend_digest
    # Generate and publish weekend digest immediately
    post, error = await generate_and_publish_weekend_digest(db)
    if not post:
        raise HTTPException(status_code=400, detail=f"Could not generate digest: {error}")
        
    return {"status": "success", "post_id": post.id, "text": post.text}

@router.post("/tomorrow-digest")
async def trigger_tomorrow_digest(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    from app.services.publisher import generate_and_publish_daily_digest
    # Generate and publish tomorrow's digest immediately
    post, error = await generate_and_publish_daily_digest(db, for_tomorrow=True)
    if not post:
        raise HTTPException(status_code=400, detail=f"Could not generate digest: {error}")
        
    return {"status": "success", "post_id": post.id, "text": post.text}
