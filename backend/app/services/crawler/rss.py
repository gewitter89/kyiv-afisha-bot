import feedparser
import logging
import traceback
from datetime import datetime
import time
from sqlalchemy import select
from app.services.crawler.base import BaseParser
from app.core.database import AsyncSessionLocal
from app.models.models import RawItem
from app.core.security import compute_raw_item_hash

logger = logging.getLogger("rss_parser")

class RssParser(BaseParser):
    async def parse_feed(self) -> int:
        """
        Fetches and parses the RSS feed URL.
        Returns: count of new raw items added.
        """
        if not self.source_url:
            logger.warning(f"No RSS URL defined for source {self.source_name}")
            return 0
            
        xml_data = await self.fetch_html(self.source_url)
        if not xml_data:
            return 0
            
        try:
            feed = feedparser.parse(xml_data)
            new_items_count = 0
            
            async with AsyncSessionLocal() as session:
                for entry in feed.entries:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    
                    # Try to fetch summary, content, or description
                    summary = entry.get("summary", "")
                    if not summary and entry.get("description"):
                        summary = entry.get("description", "")
                    if not summary and entry.get("content"):
                        summary = entry.get("content")[0].value
                        
                    ext_id = entry.get("id", link)
                    
                    # Normalize publish time
                    published_dt = None
                    published_parsed = entry.get("published_parsed")
                    if published_parsed:
                        try:
                            published_dt = datetime.fromtimestamp(time.mktime(published_parsed))
                        except Exception:
                            pass
                    
                    if not published_dt:
                        published_dt = datetime.utcnow()
                        
                    # Compute unique hash
                    item_hash = compute_raw_item_hash(summary, link)
                    
                    # Check if hash already exists in DB
                    q = await session.execute(select(RawItem).where(RawItem.hash == item_hash))
                    exists = q.scalar_one_or_none()
                    if exists:
                        continue
                        
                    # Also double check link
                    if link:
                        q_link = await session.execute(select(RawItem).where(RawItem.url == link))
                        if q_link.scalar_one_or_none():
                            continue
                            
                    # Add RawItem
                    raw_item = RawItem(
                        source_id=self.source_id,
                        external_id=ext_id,
                        url=link,
                        title=title,
                        raw_text=summary,
                        image_url=entry.get("media_content", [{}])[0].get("url") if entry.get("media_content") else None,
                        published_at=published_dt,
                        fetched_at=datetime.utcnow(),
                        hash=item_hash,
                        processing_status="new"
                    )
                    session.add(raw_item)
                    new_items_count += 1
                    
                await session.commit()
                
                # If we saved new items, trigger background AI processing for each
                if new_items_count > 0:
                    # Fetch added items to get their IDs
                    # To avoid complex mapping, we'll fetch 'new' raw items for this source
                    q_new = await session.execute(
                        select(RawItem.id).where(
                            (RawItem.source_id == self.source_id) & 
                            (RawItem.processing_status == "new")
                        )
                    )
                    new_ids = q_new.scalars().all()
                    
                    from app.tasks.worker import process_raw_item_task
                    for item_id in new_ids:
                        process_raw_item_task.delay(item_id)
                        
            logger.info(f"Source {self.source_name}: Parsed RSS. Added {new_items_count} new raw items.")
            return new_items_count
        except Exception as e:
            await self.log_error(
                "RSSParseError",
                f"Failed to parse RSS feed: {str(e)}",
                traceback.format_exc()
            )
            return 0
