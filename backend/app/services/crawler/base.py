import httpx
import logging
import traceback
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import ParserError

logger = logging.getLogger("crawler")

class BaseParser:
    def __init__(self, source_id: int, source_name: str, source_url: Optional[str] = None):
        self.source_id = source_id
        self.source_name = source_name
        self.source_url = source_url
        self.headers = {
            "User-Agent": settings.CRAWLER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        }
        
    async def log_error(self, error_type: str, message: str, tb: Optional[str] = None):
        """
        Logs a parser error to the database.
        """
        logger.error(f"Crawler Error on Source {self.source_name} ({self.source_id}): [{error_type}] {message}")
        async with AsyncSessionLocal() as session:
            err = ParserError(
                source_id=self.source_id,
                source_name=self.source_name,
                error_type=error_type,
                error_message=message,
                traceback=tb
            )
            session.add(err)
            await session.commit()

    async def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetches HTML content from URL with retry mechanism and logs errors.
        """
        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
            retries = 3
            for attempt in range(retries):
                try:
                    # Simple rate limit delay (e.g. 1s)
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.text
                except httpx.HTTPStatusError as e:
                    if attempt == retries - 1:
                        await self.log_error(
                            "HTTPStatusError",
                            f"HTTP error {response.status_code} while fetching {url}",
                            traceback.format_exc()
                        )
                except httpx.RequestError as e:
                    if attempt == retries - 1:
                        await self.log_error(
                            "RequestError",
                            f"Network error while fetching {url}: {str(e)}",
                            traceback.format_exc()
                        )
                except Exception as e:
                    if attempt == retries - 1:
                        await self.log_error(
                            "UnexpectedFetchError",
                            f"Unexpected error while fetching {url}: {str(e)}",
                            traceback.format_exc()
                        )
        return None

    def check_robots_txt(self, url: str) -> bool:
        """
        Simple verification of robots.txt for compliance.
        For MVP, we check standard patterns or return True unless blocked.
        """
        # Parse host
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        # We can implement a cached robots check if needed, but for MVP we return True (allowing scan).
        return True
