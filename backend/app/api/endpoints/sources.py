from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.schemas.schemas import Source, SourceCreate, SourceUpdate
from app.models.models import Source as DB_Source, AdminUser
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[Source])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Source).order_by(DB_Source.id.desc()))
    return q.scalars().all()

@router.post("", response_model=Source)
async def create_source(
    source_in: SourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    source = DB_Source(**source_in.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source

@router.patch("/{source_id}", response_model=Source)
async def update_source(
    source_id: int,
    source_in: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Source).where(DB_Source.id == source_id))
    source = q.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    update_data = source_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)
    
    await db.commit()
    await db.refresh(source)
    return source

@router.delete("/{source_id}")
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Source).where(DB_Source.id == source_id))
    source = q.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    await db.delete(source)
    await db.commit()
    return {"status": "ok"}

@router.post("/{source_id}/crawl")
async def trigger_crawl(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Source).where(DB_Source.id == source_id))
    source = q.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Import Celery task dynamically to avoid circular import issues
    from app.tasks.worker import crawl_source_task
    crawl_source_task.delay(source_id)
    return {"status": "triggered"}
