import asyncio
import logging
import httpx
import feedparser
from bs4 import BeautifulSoup
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_sources")

# Custom headers replicating Google Chrome on Windows
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

async def test_single_source(source: Source):
    url = source.url or ""
    if source.type == "telegram":
        url = f"https://t.me/s/{source.telegram_channel_username}"
        
    print(f"\n==================================================")
    print(f"TESTING SOURCE: {source.name} (Type: {source.type})")
    print(f"URL: {url}")
    print(f"==================================================")
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
        try:
            response = await client.get(url)
            print(f"HTTP STATUS: {response.status_code}")
            print(f"RESPONSE LENGTH: {len(response.text)} characters")
            
            if response.status_code == 200:
                if source.type == "rss":
                    feed = feedparser.parse(response.text)
                    print(f"RSS STATUS: parsed successfully")
                    print(f"FEED ENTRIES FOUND: {len(feed.entries)}")
                    if feed.entries:
                        print(f"FIRST ENTRY TITLE: {feed.entries[0].get('title', 'No title')}")
                        print(f"FIRST ENTRY LINK: {feed.entries[0].get('link', 'No link')}")
                else:
                    soup = BeautifulSoup(response.text, "html.parser")
                    title = soup.find("title")
                    print(f"PAGE TITLE: {title.text.strip() if title else 'No title tag'}")
                    
                    # Check for keywords
                    a_tags = soup.find_all("a", href=True)
                    print(f"LINKS FOUND: {len(a_tags)}")
            else:
                print(f"ERROR: Non-200 HTTP status code returned.")
        except Exception as e:
            print(f"CONNECTION ERROR: {str(e)}")

async def main():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        q = await session.execute(select(Source))
        sources = q.scalars().all()
        
    target_names = [
        "Gastroli.ua", "Karabas", "TicketsBox", "Kontramarka", 
        "Kyiv Post RSS", "RestOn RSS", "БЖ RSS", "The Village", 
        "Наш Київ", "Gloss.ua", "Vgorode", "Moe Misto"
    ]
    
    for source in sources:
        if any(name.lower() in source.name.lower() for name in target_names):
            await test_single_source(source)

if __name__ == "__main__":
    asyncio.run(main())
