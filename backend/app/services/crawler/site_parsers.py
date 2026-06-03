import logging
from typing import Optional, Dict, Any
from app.services.crawler.generic import GenericHtmlParser

logger = logging.getLogger("site_parsers")

class KyivmapsParser(GenericHtmlParser):
    """
    Parser for kyivmaps.com
    """
    async def parse(self, url: str) -> Optional[Dict[str, Any]]:
        # Site-specific logic can go here (e.g. parsing JSON-LD, specific div class names)
        # For MVP, fallback to Generic HTML Parser logic
        data = await super().parse(url)
        if data:
            data["source_name"] = "Kyivmaps"
        return data

class ConcertUaParser(GenericHtmlParser):
    """
    Parser for concert.ua
    """
    async def parse(self, url: str) -> Optional[Dict[str, Any]]:
        data = await super().parse(url)
        if data:
            data["source_name"] = "Concert.ua"
        return data

class PokuponParser(GenericHtmlParser):
    """
    Parser for pokupon.ua
    """
    async def parse(self, url: str) -> Optional[Dict[str, Any]]:
        data = await super().parse(url)
        if data:
            data["source_name"] = "Pokupon"
        return data

class KontramarkaParser(GenericHtmlParser):
    """
    Parser for kontramarka.ua
    """
    async def parse(self, url: str) -> Optional[Dict[str, Any]]:
        data = await super().parse(url)
        if data:
            data["source_name"] = "Kontramarka"
        return data

class TicketsBoxParser(GenericHtmlParser):
    """
    Parser for ticketsbox.com
    """
    async def parse(self, url: str) -> Optional[Dict[str, Any]]:
        data = await super().parse(url)
        if data:
            data["source_name"] = "TicketsBox"
        return data

class MoeMistoParser(GenericHtmlParser):
    """
    Parser for moemisto.ua
    """
    async def parse(self, url: str) -> Optional[Dict[str, Any]]:
        data = await super().parse(url)
        if data:
            data["source_name"] = "MoeMisto"
        return data

class VgorodeParser(GenericHtmlParser):
    """
    Parser for kiev.vgorode.ua
    """
    async def parse(self, url: str) -> Optional[Dict[str, Any]]:
        data = await super().parse(url)
        if data:
            data["source_name"] = "Vgorode"
        return data

def get_parser_for_url(url: str, source_id: int, source_name: str):
    """
    Factory function returning the corresponding parser depending on the URL domain.
    """
    url_lower = url.lower()
    if "kyivmaps.com" in url_lower:
        return KyivmapsParser(source_id, source_name, url)
    elif "concert.ua" in url_lower:
        return ConcertUaParser(source_id, source_name, url)
    elif "pokupon.ua" in url_lower:
        return PokuponParser(source_id, source_name, url)
    elif "kontramarka.ua" in url_lower:
        return KontramarkaParser(source_id, source_name, url)
    elif "ticketsbox.com" in url_lower:
        return TicketsBoxParser(source_id, source_name, url)
    elif "moemisto.ua" in url_lower:
        return MoeMistoParser(source_id, source_name, url)
    elif "vgorode.ua" in url_lower:
        return VgorodeParser(source_id, source_name, url)
    else:
        return GenericHtmlParser(source_id, source_name, url)
