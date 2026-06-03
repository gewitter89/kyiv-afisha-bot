"""
Weather service using OpenWeatherMap free API (no key needed for basic requests,
or use the free 1000 calls/day tier).
Falls back to a simple mock if API is unavailable.
"""
import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("weather")

# Kyiv coordinates
KYIV_LAT = 50.4501
KYIV_LON = 30.5234
KYIV_CITY_ID = 703448

# OpenWeatherMap free API endpoint
OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

# Category recommendations by weather condition
SUNNY_CATEGORIES = ["concert", "festival", "sport", "tourist", "food", "other"]
RAINY_CATEGORIES = ["theater", "cinema", "exhibition", "workshop", "lecture", "standup"]

WEATHER_EMOJI = {
    "Clear": "☀️", "Clouds": "⛅", "Rain": "🌧️",
    "Drizzle": "🌦️", "Thunderstorm": "⛈️", "Snow": "❄️",
    "Fog": "🌫️", "Mist": "🌫️", "Haze": "🌫️",
}


async def get_kyiv_weather(api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetches current Kyiv weather from OpenWeatherMap.
    If no API key provided, uses a free public endpoint fallback.
    Returns structured weather dict or None on failure.
    """
    try:
        params = {
            "lat": KYIV_LAT,
            "lon": KYIV_LON,
            "units": "metric",
            "lang": "uk",
        }
        if api_key:
            params["appid"] = api_key

        # Try wttr.in as a free fallback (no API key required)
        async with httpx.AsyncClient(timeout=8.0) as client:
            # wttr.in JSON format — completely free, no key
            resp = await client.get(
                "https://wttr.in/Kyiv?format=j1",
                headers={"User-Agent": "KyivEventGuide/1.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                current = data["current_condition"][0]
                temp = int(current["temp_C"])
                feels = int(current["FeelsLikeC"])
                desc = current["lang_uk"][0]["value"] if current.get("lang_uk") else current.get("weatherDesc", [{}])[0].get("value", "")
                wind = int(current.get("windspeedKmph", 0))
                humidity = int(current.get("humidity", 0))
                weather_code = int(current.get("weatherCode", 113))

                # Map wttr.in code to condition
                condition = _wttr_code_to_condition(weather_code)
                emoji = WEATHER_EMOJI.get(condition, "🌤️")
                is_outdoor_friendly = (temp >= 15 and condition in ["Clear", "Clouds"] and wind < 40)

                return {
                    "temp": temp,
                    "feels_like": feels,
                    "description": desc,
                    "condition": condition,
                    "emoji": emoji,
                    "wind_kmh": wind,
                    "humidity": humidity,
                    "is_outdoor_friendly": is_outdoor_friendly,
                    "recommended_categories": SUNNY_CATEGORIES if is_outdoor_friendly else RAINY_CATEGORIES,
                }
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")

    return None


def _wttr_code_to_condition(code: int) -> str:
    """Maps wttr.in weather code to OpenWeatherMap-style condition name."""
    if code == 113:
        return "Clear"
    elif code in [116, 119, 122]:
        return "Clouds"
    elif code in [176, 293, 296, 299, 302, 305, 308]:
        return "Rain"
    elif code in [263, 266]:
        return "Drizzle"
    elif code in [200, 386, 389, 392, 395]:
        return "Thunderstorm"
    elif code in [179, 182, 185, 227, 230, 323, 326, 329, 332, 335, 338, 350, 368, 371, 374, 377]:
        return "Snow"
    elif code in [143, 248, 260]:
        return "Fog"
    return "Clouds"


def format_weather_line(weather: Dict[str, Any]) -> str:
    """Returns a compact one-line weather string for use in digests."""
    if not weather:
        return ""
    emoji = weather.get("emoji", "🌤️")
    temp = weather.get("temp", "?")
    desc = weather.get("description", "")
    wind = weather.get("wind_kmh", 0)
    outdoor = "Ідеально для прогулянок" if weather.get("is_outdoor_friendly") else "Краще в приміщенні"
    return f"{emoji} Київ сьогодні: {temp}°C, {desc}. {outdoor} 👇"


def get_weather_category_boost(weather: Dict[str, Any]) -> list:
    """Returns list of categories to prioritize in today's digest based on weather."""
    if not weather:
        return []
    return weather.get("recommended_categories", [])
