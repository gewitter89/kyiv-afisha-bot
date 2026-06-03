import logging
import json
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from app.services.crawler.base import BaseParser

logger = logging.getLogger("generic_parser")

# Image extensions to consider valid
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
# Substrings to skip in image URLs (logos, icons, spinners, placeholders)
IMAGE_SKIP_KEYWORDS = ["logo", "icon", "sprite", "favicon", "placeholder", "blank", "pixel", "tracking", "1x1", "spacer", "avatar"]

def _is_valid_image_url(src: str) -> bool:
    """Checks if a URL looks like a real event/poster image (not an icon/logo)."""
    if not src or len(src) < 10:
        return False
    src_lower = src.lower()
    # Skip data URIs
    if src_lower.startswith("data:"):
        return False
    # Skip if any blacklisted keyword found in URL
    for skip in IMAGE_SKIP_KEYWORDS:
        if skip in src_lower:
            return False
    # Accept if it ends with a known image extension OR has no extension at all (CDN URLs)
    parsed = urlparse(src)
    path = parsed.path.lower()
    ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
    if ext and ext not in IMAGE_EXTENSIONS and len(ext) <= 5:
        return False  # Has extension but it's not an image extension
    return True


def _extract_best_image(soup: BeautifulSoup, page_url: str) -> Optional[str]:
    """
    Multi-strategy image extraction in priority order:
    1. og:image meta tag (most reliable for events)
    2. twitter:image meta tag
    3. JSON-LD Event schema image
    4. <picture> / <source srcset> tags (responsive images)
    5. First large <img> with data-src (lazy load) or src
    """
    base = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}"

    # ── Strategy 1: og:image ──────────────────────────────────────────────────
    for og in soup.find_all("meta", property="og:image"):
        url = og.get("content", "").strip()
        if url and _is_valid_image_url(url):
            return urljoin(base, url)

    # ── Strategy 2: twitter:image ─────────────────────────────────────────────
    for tw in soup.find_all("meta", attrs={"name": re.compile(r"twitter:image", re.I)}):
        url = tw.get("content", "").strip()
        if url and _is_valid_image_url(url):
            return urljoin(base, url)

    # ── Strategy 3: JSON-LD Event schema ──────────────────────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(script.string or "")
            # May be a list or a single object
            items = ld if isinstance(ld, list) else [ld]
            for item in items:
                # Handle @graph array
                if "@graph" in item:
                    items.extend(item["@graph"])
                img = item.get("image")
                if isinstance(img, str) and _is_valid_image_url(img):
                    return urljoin(base, img)
                if isinstance(img, dict):
                    url = img.get("url") or img.get("contentUrl") or ""
                    if url and _is_valid_image_url(url):
                        return urljoin(base, url)
                if isinstance(img, list) and img:
                    first = img[0]
                    url = first if isinstance(first, str) else (first.get("url") or "")
                    if url and _is_valid_image_url(url):
                        return urljoin(base, url)
        except Exception:
            pass

    # ── Strategy 4: <picture> / <source srcset> ───────────────────────────────
    for source in soup.find_all("source"):
        srcset = source.get("srcset") or source.get("data-srcset") or ""
        if srcset:
            # Take the last (highest-res) candidate from srcset
            candidates = [s.strip().split()[0] for s in srcset.split(",") if s.strip()]
            for cand in reversed(candidates):
                if cand and _is_valid_image_url(cand):
                    return urljoin(base, cand)

    # ── Strategy 5: <img> tags ─────────────────────────────────────────────────
    # Look at common event-poster class names first
    poster_classes = ["event-poster", "event-cover", "event-image", "hero-image",
                      "poster", "cover", "thumbnail", "card-image", "event-img",
                      "show-poster", "concert-image", "main-image"]
    for cls in poster_classes:
        for img in soup.find_all("img", class_=re.compile(cls, re.I)):
            for attr in ["src", "data-src", "data-lazy", "data-original"]:
                url = img.get(attr, "").strip()
                if url and _is_valid_image_url(url):
                    return urljoin(base, url)

    # Fall back to scanning ALL img tags by area/order
    for img in soup.find_all("img"):
        for attr in ["src", "data-src", "data-lazy", "data-original"]:
            url = img.get(attr, "").strip()
            if url and _is_valid_image_url(url):
                full_url = urljoin(base, url)
                if full_url.startswith("http"):
                    return full_url

    return None


class GenericHtmlParser(BaseParser):
    async def parse(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parses generic HTML pages and extracts core fields including rich media.
        """
        html = await self.fetch_html(url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")

            # ── 1. Title ──────────────────────────────────────────────────────
            title = ""
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()

            if not title:
                # Try JSON-LD first
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        ld = json.loads(script.string or "")
                        items = ld if isinstance(ld, list) else [ld]
                        for item in items:
                            if item.get("name"):
                                title = item["name"]
                                break
                    except Exception:
                        pass
                    if title:
                        break

            if not title:
                title_tag = soup.find("title")
                if title_tag:
                    title = title_tag.text.strip()

            # ── 2. Description / Main Text ────────────────────────────────────
            description = ""
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                description = og_desc["content"].strip()

            if not description:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    description = meta_desc["content"].strip()

            # Try JSON-LD description
            if not description:
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        ld = json.loads(script.string or "")
                        items = ld if isinstance(ld, list) else [ld]
                        for item in items:
                            if item.get("description"):
                                description = item["description"]
                                break
                    except Exception:
                        pass
                    if description:
                        break

            # Main body text
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                element.decompose()

            paragraphs = [p.text.strip() for p in soup.find_all("p") if len(p.text.strip()) > 20]
            main_text = "\n\n".join(paragraphs[:15])

            if not description and paragraphs:
                description = paragraphs[0]

            # ── 3. Image ──────────────────────────────────────────────────────
            image_url = _extract_best_image(soup, url)

            return {
                "title": title or "Подія в Києві",
                "description": description or main_text[:300],
                "raw_text": f"Title: {title}\n\nContent:\n{main_text}",
                "image_url": image_url,
                "url": url
            }
        except Exception as e:
            import traceback
            await self.log_error(
                "HTMLParseError",
                f"Failed to parse HTML from {url}: {str(e)}",
                traceback.format_exc()
            )
            return None
