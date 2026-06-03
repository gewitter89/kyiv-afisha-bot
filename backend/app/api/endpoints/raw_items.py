from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.schemas.schemas import RawItem
from app.models.models import RawItem as DB_RawItem, AdminUser
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[RawItem])
async def list_raw_items(
    status: Optional[str] = Query(None, description="Filter by processing status"),
    source_id: Optional[int] = Query(None, description="Filter by source ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    stmt = select(DB_RawItem)
    if status:
        stmt = stmt.where(DB_RawItem.processing_status == status)
    if source_id:
        stmt = stmt.where(DB_RawItem.source_id == source_id)
    
    stmt = stmt.order_by(DB_RawItem.fetched_at.desc()).offset(skip).limit(limit)
    q = await db.execute(stmt)
    return q.scalars().all()

@router.post("/{raw_item_id}/reprocess")
async def reprocess_raw_item(
    raw_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_RawItem).where(DB_RawItem.id == raw_item_id))
    raw_item = q.scalar_one_or_none()
    if not raw_item:
        raise HTTPException(status_code=404, detail="Raw item not found")
    
    # Reset processing status
    raw_item.processing_status = "new"
    raw_item.error_message = None
    await db.commit()
    
    # Trigger Celery task to reprocess
    from app.tasks.worker import process_raw_item_task
    process_raw_item_task.delay(raw_item_id)
    return {"status": "reprocessing_triggered"}
