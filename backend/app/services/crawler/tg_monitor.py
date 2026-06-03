import logging
import traceback
import re
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy import select
import httpx

from app.services.crawler.base import BaseParser
from app.core.database import AsyncSessionLocal
from app.models.models import RawItem
from app.core.security import compute_raw_item_hash
from app.core.config import settings

logger = logging.getLogger("tg_monitor")

class TelegramMonitor(BaseParser):
    async def monitor_channel(self) -> int:
        """
        Monitors public channel and returns count of new raw items added.
        """
        if not self.source_url and not self.source_name:
            return 0
            
        username = self.source_url # URL or username of the channel
        if not username:
            return 0
            
        # Extract username if URL is provided
        if "t.me/" in username:
            username = username.split("t.me/")[-1].split("?")[0].split("/")[0]
            
        # Clean username
        username = username.replace("@", "").strip()
        
        # Decide monitoring method
        if settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH:
            return await self._monitor_via_telethon(username)
        else:
            return await self._monitor_via_web_fallback(username)

    async def _monitor_via_telethon(self, username: str) -> int:
        """
        Monitors using Telethon client (requires API_ID and API_HASH).
        """
        logger.info(f"Monitoring Telegram channel @{username} via Telethon client...")
        try:
            from telethon import TelegramClient
            # Since Telethon session creation might block or require interaction, 
            # we write a non-interactive fetch for public channels.
            # For public channels, Telethon can connect as bot or user session.
            # Using bot session or user session. Let's do a quick client startup.
            # To avoid locking on local run, we construct the client and fetch history.
            client = TelegramClient(
                f"session_{username}",
                settings.TELEGRAM_API_ID,
                settings.TELEGRAM_API_HASH
            )
            await client.connect()
            
            # If not authorized, we cannot download messages in user mode.
            # For MVP, if not authorized, log warning and use web fallback instead.
            if not await client.is_user_authorized():
                logger.warning(f"Telethon client not authorized. Falling back to Web Scraper for @{username}.")
                await client.disconnect()
                return await self._monitor_via_web_fallback(username)
                
            new_items_count = 0
            async with AsyncSessionLocal() as session:
                # Fetch last 15 messages
                messages = await client.get_messages(username, limit=15)
                for msg in messages:
                    if not msg.text:
                        continue
                        
                    ext_id = str(msg.id)
                    post_url = f"https://t.me/{username}/{msg.id}"
                    
                    # Compute unique hash
                    item_hash = compute_raw_item_hash(msg.text, post_url)
                    
                    # Check if exists
                    q = await session.execute(select(RawItem).where(RawItem.hash == item_hash))
                    if q.scalar_one_or_none():
                        continue
                        
                    raw_item = RawItem(
                        source_id=self.source_id,
                        external_id=ext_id,
                        url=post_url,
                        title=f"Пост у Telegram-каналі @{username}",
                        raw_text=msg.text,
                        image_url=None, # Media downloading can be added if needed
                        published_at=msg.date.replace(tzinfo=None) if msg.date else datetime.utcnow(),
                        fetched_at=datetime.utcnow(),
                        hash=item_hash,
                        processing_status="new"
                    )
                    session.add(raw_item)
                    new_items_count += 1
                    
                await session.commit()
                
                if new_items_count > 0:
                    await self._trigger_ai_pipeline(session)
                    
            await client.disconnect()
            return new_items_count
        except Exception as e:
            logger.error(f"Telethon monitor failed: {e}. Falling back to Web Scraper.", exc_info=True)
            return await self._monitor_via_web_fallback(username)

    async def _monitor_via_web_fallback(self, username: str) -> int:
        """
        Parses the public web preview at https://t.me/s/{username}
        Does not require any credentials. Complies with public terms.
        """
        logger.info(f"Monitoring Telegram channel @{username} via Web view fallback scraper...")
        url = f"https://t.me/s/{username}"
        html = await self.fetch_html(url)
        if not html:
            return 0
            
        try:
            soup = BeautifulSoup(html, "html.parser")
            new_items_count = 0
            
            async with AsyncSessionLocal() as session:
                # Find all message widgets
                message_widgets = soup.find_all("div", class_="tgme_widget_message")
                for widget in message_widgets:
                    # 1. Extract link & ID
                    link_tag = widget.find("a", class_="tgme_widget_message_date")
                    if not link_tag or not link_tag.get("href"):
                        continue
                    post_url = link_tag["href"]
                    # Extract external ID (message number) from URL
                    ext_id = post_url.split("/")[-1].split("?")[0]
                    
                    # 2. Extract Text
                    text_div = widget.find("div", class_="tgme_widget_message_text")
                    if not text_div:
                        continue
                    raw_text = text_div.text.strip()
                    
                    # 3. Extract Image
                    image_url = None
                    photo_wrap = widget.find("a", class_="tgme_widget_message_photo_wrap")
                    if photo_wrap and photo_wrap.get("style"):
                        style = photo_wrap["style"]
                        bg_img_match = re.search(r"background-image:url\('(.+?)'\)", style)
                        if bg_img_match:
                            image_url = bg_img_match.group(1)
                            
                    # 4. Normalize publish date
                    pub_date = datetime.utcnow()
                    time_tag = widget.find("time")
                    if time_tag and time_tag.get("datetime"):
                        try:
                            # e.g. 2026-06-01T15:30:00+00:00
                            date_str = time_tag["datetime"]
                            pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        except Exception:
                            pass
                            
                    item_hash = compute_raw_item_hash(raw_text, post_url)
                    
                    # Check if exists in DB
                    q = await session.execute(select(RawItem).where(RawItem.hash == item_hash))
                    if q.scalar_one_or_none():
                        continue
                        
                    # Save
                    raw_item = RawItem(
                        source_id=self.source_id,
                        external_id=ext_id,
                        url=post_url,
                        title=f"Пост у Telegram-каналі @{username}",
                        raw_text=raw_text,
                        image_url=image_url,
                        published_at=pub_date,
                        fetched_at=datetime.utcnow(),
                        hash=item_hash,
                        processing_status="new"
                    )
                    session.add(raw_item)
                    new_items_count += 1
                    
                await session.commit()
                
                # Trigger Celery tasks
                if new_items_count > 0:
                    await self._trigger_ai_pipeline(session)
                    
            logger.info(f"Source {self.source_name}: Parsed Web TG channel @{username}. Added {new_items_count} new raw items.")
            return new_items_count
        except Exception as e:
            await self.log_error(
                "TelegramMonitorError",
                f"Failed to scrape public web preview for @{username}: {str(e)}",
                traceback.format_exc()
            )
            return 0

    async def _trigger_ai_pipeline(self, session):
        """
        Triggers AI processing for new raw items.
        """
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
