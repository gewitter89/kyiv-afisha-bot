from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from decimal import Decimal

from app.core.database import get_db
from app.schemas.schemas import Event, EventUpdate, EventScheduleRequest, EventMergeRequest
from app.models.models import Event as DB_Event, EventSource as DB_EventSource, AdminUser
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[Event])
async def list_events(
    status: Optional[str] = Query(None, description="Filter by status (draft, needs_review, approved, rejected, published, archived)"),
    category: Optional[str] = Query(None, description="Filter by category slug"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date after"),
    end_date: Optional[datetime] = Query(None, description="Filter by start date before"),
    min_quality: Optional[int] = Query(None, description="Minimum quality score"),
    has_duplicates: Optional[bool] = Query(None, description="If true, only show events with a duplicate_group_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    stmt = select(DB_Event)
    
    if status:
        stmt = stmt.where(DB_Event.status == status)
    if category:
        stmt = stmt.where(DB_Event.category == category)
    if start_date:
        stmt = stmt.where(DB_Event.start_datetime >= start_date)
    if end_date:
        stmt = stmt.where(DB_Event.start_datetime <= end_date)
    if min_quality is not None:
        stmt = stmt.where(DB_Event.quality_score >= min_quality)
    if has_duplicates is not None:
        if has_duplicates:
            stmt = stmt.where(DB_Event.duplicate_group_id.isnot(None))
        else:
            stmt = stmt.where(DB_Event.duplicate_group_id.is_(None))
            
    stmt = stmt.order_by(DB_Event.start_datetime.asc()).offset(skip).limit(limit)
    q = await db.execute(stmt)
    return q.scalars().all()

@router.get("/{event_id}", response_model=Event)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Event).where(DB_Event.id == event_id))
    event = q.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # We also want to load the sources mapping
    q_src = await db.execute(select(DB_EventSource).where(DB_EventSource.event_id == event_id))
    event.event_sources = q_src.scalars().all()
    
    return event

@router.get("/{event_id}/possible-duplicates", response_model=List[Event])
async def get_possible_duplicates(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Event).where(DB_Event.id == event_id))
    event = q.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    from app.services.deduplicator import find_potential_duplicates
    duplicates = await find_potential_duplicates(event, db)
    return duplicates

@router.patch("/{event_id}", response_model=Event)
async def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Event).where(DB_Event.id == event_id))
    event = q.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    await db.commit()
    await db.refresh(event)
    return event

@router.post("/{event_id}/approve", response_model=Event)
async def approve_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Event).where(DB_Event.id == event_id))
    event = q.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.status = "approved"
    await db.commit()
    await db.refresh(event)
    return event

@router.post("/{event_id}/reject", response_model=Event)
async def reject_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Event).where(DB_Event.id == event_id))
    event = q.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.status = "rejected"
    await db.commit()
    await db.refresh(event)
    return event

@router.post("/{event_id}/publish")
async def publish_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Event).where(DB_Event.id == event_id))
    event = q.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    from app.services.publisher import publish_single_event
    success, error = await publish_single_event(event, db)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to publish: {error}")
    
    return {"status": "published", "message_id": event.published_to_telegram_at}

@router.post("/{event_id}/schedule")
async def schedule_event(
    event_id: int,
    schedule_in: EventScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Event).where(DB_Event.id == event_id))
    event = q.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create or update Post publication queue
    from app.models.models import Post as DB_Post
    
    # Check if a post is already scheduled
    q_post = await db.execute(
        select(DB_Post).where(and_(DB_Post.event_id == event_id, DB_Post.status == "scheduled"))
    )
    post = q_post.scalar_one_or_none()
    
    if not post:
        post = DB_Post(
            event_id=event_id,
            post_type="single_event",
            telegram_channel_id=settings.TELEGRAM_CHANNEL_ID,
            text=event.short_description or event.title,
            status="scheduled",
            scheduled_at=schedule_in.scheduled_at
        )
        db.add(post)
    else:
        post.scheduled_at = schedule_in.scheduled_at
        post.text = event.short_description or event.title
        
    event.status = "approved"
    await db.commit()
    return {"status": "scheduled", "scheduled_at": schedule_in.scheduled_at}

@router.post("/{event_id}/regenerate")
async def regenerate_event_text(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Event).where(DB_Event.id == event_id))
    event = q.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    from app.services.ai_processor import rewrite_event_card
    new_text = await rewrite_event_card(event)
    event.short_description = new_text
    await db.commit()
    await db.refresh(event)
    return {"status": "regenerated", "short_description": new_text}

@router.post("/{event_id}/merge-duplicate")
async def merge_duplicate_event(
    event_id: int,
    merge_in: EventMergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    # event_id is the duplicate event we want to merge INTO merge_in.target_event_id
    q1 = await db.execute(select(DB_Event).where(DB_Event.id == event_id))
    duplicate_event = q1.scalar_one_or_none()
    
    q2 = await db.execute(select(DB_Event).where(DB_Event.id == merge_in.target_event_id))
    target_event = q2.scalar_one_or_none()
    
    if not duplicate_event or not target_event:
        raise HTTPException(status_code=404, detail="One of the events was not found")
        
    # Re-link any event sources
    q_src = await db.execute(select(DB_EventSource).where(DB_EventSource.event_id == event_id))
    event_sources = q_src.scalars().all()
    
    for src in event_sources:
        # Check if target event already has this source
        q_target_src = await db.execute(
            select(DB_EventSource).where(
                and_(DB_EventSource.event_id == target_event.id, DB_EventSource.source_id == src.source_id)
            )
        )
        t_src = q_target_src.scalar_one_or_none()
        if not t_src:
            src.event_id = target_event.id
        else:
            await db.delete(src) # Delete duplicates in relations
            
    # Set duplicate status
    duplicate_event.status = "rejected"
    
    # Setup duplicate group
    group_id = target_event.duplicate_group_id or target_event.id
    target_event.duplicate_group_id = group_id
    duplicate_event.duplicate_group_id = group_id
    
    await db.commit()
    return {"status": "merged", "target_event_id": target_event.id}
