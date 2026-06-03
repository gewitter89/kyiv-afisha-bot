from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, time

from app.core.database import get_db
from app.schemas.schemas import DashboardStats
from app.models.models import Source, RawItem, Event, Post, ParserError, AdminUser
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    # 1. Active sources count
    active_sources_q = await db.execute(
        select(func.count()).select_from(Source).where(Source.enabled == True)
    )
    active_sources_count = active_sources_q.scalar() or 0

    # 2. New/Error raw items count
    new_raw_q = await db.execute(
        select(func.count()).select_from(RawItem).where(RawItem.processing_status == "new")
    )
    new_raw_items_count = new_raw_q.scalar() or 0

    # 3. Events needing review count
    review_events_q = await db.execute(
        select(func.count()).select_from(Event).where(Event.status == "needs_review")
    )
    review_events_count = review_events_q.scalar() or 0

    # 4. Published today count
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    published_today_q = await db.execute(
        select(func.count()).select_from(Post).where(
            and_(Post.status == "published", Post.published_at >= today_start)
        )
    )
    published_today_count = published_today_q.scalar() or 0

    # 5. Parser errors count
    errors_count_q = await db.execute(
        select(func.count()).select_from(ParserError)
    )
    parser_errors_count = errors_count_q.scalar() or 0

    # 6. Recent parser errors
    recent_errors_q = await db.execute(
        select(ParserError).order_by(ParserError.created_at.desc()).limit(10)
    )
    recent_errors = recent_errors_q.scalars().all()

    return {
        "active_sources_count": active_sources_count,
        "new_raw_items_count": new_raw_items_count,
        "review_events_count": review_events_count,
        "published_today_count": published_today_count,
        "parser_errors_count": parser_errors_count,
        "recent_errors": recent_errors
    }
