from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.schemas.schemas import Submission, Event
from app.models.models import Submission as DB_Submission, Event as DB_Event, AdminUser
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[Submission])
async def list_submissions(
    status: Optional[str] = Query(None, description="Filter by status (new, accepted, rejected)"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    stmt = select(DB_Submission)
    if status:
        stmt = stmt.where(DB_Submission.status == status)
    stmt = stmt.order_by(DB_Submission.created_at.desc())
    
    q = await db.execute(stmt)
    return q.scalars().all()

@router.post("/{submission_id}/accept", response_model=Event)
async def accept_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Submission).where(DB_Submission.id == submission_id))
    submission = q.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.status != "new":
        raise HTTPException(status_code=400, detail="Submission already processed")
        
    submission.status = "accepted"
    
    # Create event from submission
    event = DB_Event(
        title=submission.title,
        full_description=submission.description,
        short_description=submission.description[:150], # temporary short description
        date_text_original=submission.date_text,
        venue_name=submission.venue,
        address=submission.address,
        price_text_original=submission.price_text,
        ticket_url=submission.link,
        source_name=f"Telegram User: {submission.username or submission.user_id}",
        source_url=None,
        status="needs_review",
        image_url=None # We will map the image if needed, or upload it
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    return event

@router.post("/{submission_id}/reject", response_model=Submission)
async def reject_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    q = await db.execute(select(DB_Submission).where(DB_Submission.id == submission_id))
    submission = q.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    if submission.status != "new":
        raise HTTPException(status_code=400, detail="Submission already processed")
        
    submission.status = "rejected"
    await db.commit()
    await db.refresh(submission)
    return submission
