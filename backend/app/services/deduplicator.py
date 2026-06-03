import logging
import re
from datetime import timedelta
from typing import Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Event
from app.services.ai_processor import ai_processor

logger = logging.getLogger("deduplicator")

def normalize_text(text: str) -> str:
    """
    Cleans and normalizes text for basic string comparisons.
    """
    if not text:
        return ""
    # Lowercase, remove punctuation, spaces
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())

async def find_potential_duplicates(event: Event, db: AsyncSession) -> list[Event]:
    """
    Finds potential duplicates for an event within a ±3 day window.
    """
    if not event.start_datetime:
        # If no date, duplicate check is hard. We could query other events with no date.
        return []
        
    start_window = event.start_datetime - timedelta(days=3)
    end_window = event.start_datetime + timedelta(days=3)
    
    # Query events in time window
    q = await db.execute(
        select(Event).where(
            and_(
                Event.id != event.id,
                Event.status != "rejected",
                Event.start_datetime >= start_window,
                Event.start_datetime <= end_window
            )
        )
    )
    candidates = q.scalars().all()
    if not candidates:
        return []
        
    # Basic field check & AI duplicate confirmation
    # Run the AI/Mock duplicate detector
    ai_results = await ai_processor.detect_duplicate(event, candidates)
    
    potential_duplicates = []
    
    for cand in candidates:
        is_dup = False
        
        # 1. Exact match normalized titles + venue (heuristic)
        norm_t1 = normalize_text(event.title)
        norm_t2 = normalize_text(cand.title)
        
        norm_v1 = normalize_text(event.venue_name)
        norm_v2 = normalize_text(cand.venue_name)
        
        # Exact title and venue
        if norm_t1 == norm_t2 and norm_v1 == norm_v2:
            is_dup = True
            
        # 2. AI Duplicate prediction match
        elif ai_results.get(cand.id):
            is_dup = True
            
        if is_dup:
            potential_duplicates.append(cand)
            
    return potential_duplicates

async def process_event_deduplication(event: Event, db: AsyncSession) -> Optional[int]:
    """
    Detects and merges event into a duplicate group.
    Returns: duplicate_group_id if assigned, else None.
    """
    duplicates = await find_potential_duplicates(event, db)
    if not duplicates:
        return None
        
    # Find if any duplicate already has a group
    group_id = None
    for dup in duplicates:
        if dup.duplicate_group_id:
            group_id = dup.duplicate_group_id
            break
            
    if not group_id:
        # Create a new group using the earliest event's ID
        # Let's collect all candidate IDs
        all_ids = [event.id] + [d.id for d in duplicates]
        group_id = min(all_ids)
        
        # Update duplicates
        for dup in duplicates:
            dup.duplicate_group_id = group_id
            
    event.duplicate_group_id = group_id
    await db.commit()
    logger.info(f"Event '{event.title}' ({event.id}) assigned to duplicate group {group_id}")
    return group_id
