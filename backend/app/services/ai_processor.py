import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.models.models import Event

logger = logging.getLogger("ai_processor")

class AIProcessor:
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self.client = None
        self.model = "gpt-4o-mini"
        
        if self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.model = "gpt-4o-mini"
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}. Switching to mock provider.")
                self.provider = "mock"
        elif self.provider == "deepseek" and settings.DEEPSEEK_API_KEY:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url="https://api.deepseek.com"
                )
                self.model = "deepseek-chat"
            except Exception as e:
                logger.error(f"Failed to initialize DeepSeek client: {e}. Switching to mock provider.")
                self.provider = "mock"
        else:
            self.provider = "mock"
            
    async def extract_event(self, raw_text: str, source_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts event facts from raw text and formats them as a JSON structure.
        """
        if self.provider in ["openai", "deepseek"] and self.client:
            return await self._extract_via_openai(raw_text, source_url)
        else:
            return await self._extract_via_mock(raw_text, source_url)

    async def rewrite_event_card(self, event_data: Any) -> str:
        """
        Rewrites the event card into a concise Ukrainian Telegram post.
        """
        # Accept either dict or SQLAlchemy Event model
        event = event_data if isinstance(event_data, dict) else {
            "title": event_data.title,
            "full_description": event_data.full_description or event_data.short_description or "",
            "venue_name": event_data.venue_name or "",
            "date_text_original": event_data.date_text_original or "",
            "price_text_original": event_data.price_text_original or "",
            "category": event_data.category or ""
        }
        
        if self.provider in ["openai", "deepseek"] and self.client:
            return await self._rewrite_via_openai(event)
        else:
            return await self._rewrite_via_mock(event)

    async def score_event(self, event_data: Any) -> int:
        """
        Scores the event quality (0 to 100) based on completeness and appeal.
        """
        event = event_data if isinstance(event_data, dict) else {
            "title": event_data.title,
            "start_datetime": str(event_data.start_datetime) if event_data.start_datetime else "",
            "venue_name": event_data.venue_name or "",
            "price_min": str(event_data.price_min) if event_data.price_min else ""
        }
        
        if self.provider in ["openai", "deepseek"] and self.client:
            return await self._score_via_openai(event)
        else:
            return await self._score_via_mock(event)

    async def detect_duplicate(self, event: Any, candidates: List[Any]) -> Dict[str, Any]:
        """
        Compares an event against potential duplicates.
        Returns: {candidate_id: is_duplicate_bool}
        """
        if not candidates:
            return {}
            
        if self.provider in ["openai", "deepseek"] and self.client:
            return await self._detect_duplicate_via_openai(event, candidates)
        else:
            return await self._detect_duplicate_via_mock(event, candidates)

    # --- OPENAI API CALLS ---
    
    async def _extract_via_openai(self, raw_text: str, source_url: Optional[str]) -> Dict[str, Any]:
        prompt = (
            "You are an expert events editor in Kyiv. Extract event details from the raw text below and return a JSON object.\n"
            "Rules:\n"
            "1. If this text is NOT about a specific upcoming event in Kyiv (e.g. it is general news, policy updates, historical review, advertisement with no date), set is_event = false.\n"
            "2. DO NOT invent or make up details. If a detail is missing, set it to null.\n"
            "3. Format dates in ISO format (YYYY-MM-DDTHH:MM:SS) if found, otherwise keep original date text.\n"
            "4. Language: Translate descriptions and names to Ukrainian.\n\n"
            "Raw text:\n"
            f"{raw_text}\n"
        )
        
        system_instructions = (
            "Return JSON matching this schema:\n"
            "{\n"
            "  \"is_event\": boolean,\n"
            "  \"title\": string,\n"
            "  \"short_description\": string (1-2 sentences overview),\n"
            "  \"full_description\": string,\n"
            "  \"category\": string (one of: today, weekend, concert, theater, standup, exhibition, party, food, bar, restaurant, kids, family, date, free, sport, workshop, cinema, lecture, unusual, tourist, news, other),\n"
            "  \"city\": \"Київ\",\n"
            "  \"district\": string (e.g. Поділ, Шевченківський, etc.),\n"
            "  \"venue_name\": string (e.g. Клуб Атлас, ВДНГ),\n"
            "  \"address\": string,\n"
            "  \"start_datetime\": string or null,\n"
            "  \"end_datetime\": string or null,\n"
            "  \"date_text_original\": string (e.g. 5 червня о 19:00),\n"
            "  \"price_min\": number or null,\n"
            "  \"price_max\": number or null,\n"
            "  \"price_text_original\": string,\n"
            "  \"is_free\": boolean,\n"
            "  \"ticket_url\": string or null,\n"
            "  \"confidence\": number (0.0 to 1.0),\n"
            "  \"missing_fields\": string[]\n"
            "}"
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            data = json.loads(response.choices[0].message.content)
            # Inject source url if found and ticket url not extracted
            if data.get("is_event") and not data.get("ticket_url") and source_url:
                data["ticket_url"] = source_url
            return data
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}. Falling back to mock.", exc_info=True)
            return await self._extract_via_mock(raw_text, source_url)

    async def _rewrite_via_openai(self, event: Dict[str, Any]) -> str:
        prompt = (
            "Ти — редактор топового Telegram-каналу подій Києва у 2026 році. "
            "Твоє завдання: написати короткий вірусний опис події так, щоб людина ОДРАЗУ захотіла піти.\n\n"
            "ПРАВИЛА (суворо):\n"
            "1. Пиши ТІЛЬКИ опис — що там буде, чому це круто, який кайф отримає відвідувач.\n"
            "   НЕ вказуй дату, ціну, локацію — вони додаються автоматично окремо.\n"
            "2. Структура: 2-3 речення MAX. Кожне — удар. Без води.\n"
            "3. Стиль: розмовна українська, живо, як пишеш другу. Не казенно.\n"
            "4. Емодзі: 2-4 штуки, лише доречні (не спам). Ставити всередині речень, не на початку кожного.\n"
            "5. ЗАБОРОНЕНО вживати: 'неймовірна', 'приголомшливий', 'незабутній', 'поспішайте', "
            "'не пропусти', 'унікальна можливість', 'легендарний', 'найкращий у місті'.\n"
            "6. Фінал: короткий інтригуючий заклик або риторичне запитання.\n"
            "7. Мова: ТІЛЬКИ українська, грамотна.\n"
            "8. Обсяг: 180-320 символів.\n\n"
            f"Назва події: {event['title']}\n"
            f"Категорія: {event.get('category', 'other')}\n"
            f"Опис джерела: {str(event.get('full_description', ''))[:600]}\n"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.75,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI rewrite failed: {e}. Falling back to mock.")
            return await self._rewrite_via_mock(event)


    async def _score_via_openai(self, event: Dict[str, Any]) -> int:
        prompt = (
            "Оціни привабливість цієї події для широкої аудиторії в Києві від 0 до 100.\n"
            "Враховуй:\n"
            "- Чи є повна дата і назва локації (+15)\n"
            "- Чи зрозуміла ціна (+15)\n"
            "- Чи подія цікава та свіжа (+20)\n"
            "Поверни ТІЛЬКИ ціле число від 0 до 100.\n\n"
            f"Назва: {event['title']}\n"
            f"Локація: {event['venue_name']}\n"
            f"Дата: {event['start_datetime']}\n"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            num_match = re.search(r"\d+", response.choices[0].message.content)
            return int(num_match.group(0)) if num_match else 50
        except Exception as e:
            logger.error(f"OpenAI scoring failed: {e}. Falling back to mock.")
            return await self._score_via_mock(event)

    async def _detect_duplicate_via_openai(self, event: Any, candidates: List[Any]) -> Dict[str, Any]:
        # Formulate query comparing details
        prompt = (
            "You are comparing a newly parsed event with active database events to detect duplicates.\n"
            "Return a JSON object where keys are candidate IDs and values are booleans (true if it is a duplicate, false otherwise).\n\n"
            f"New Event: Title: '{event.title}', Date: '{event.start_datetime or event.date_text_original}', Venue: '{event.venue_name}'\n\n"
            "Candidates:\n"
        )
        for cand in candidates:
            prompt += f"ID: {cand.id}, Title: '{cand.title}', Date: '{cand.start_datetime or cand.date_text_original}', Venue: '{cand.venue_name}'\n"
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Return a JSON object like: { \"123\": true, \"124\": false }"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            res_dict = json.loads(response.choices[0].message.content)
            # Cast keys to integers
            return {int(k): bool(v) for k, v in res_dict.items()}
        except Exception as e:
            logger.error(f"OpenAI duplicate detection failed: {e}.")
            return await self._detect_duplicate_via_mock(event, candidates)


    # --- MOCK / REGEX FALLBACK PROVIDERS ---

    async def _extract_via_mock(self, raw_text: str, source_url: Optional[str]) -> Dict[str, Any]:
        """
        Fallback parsing logic utilizing string operations and regular expressions.
        """
        # Determine if it's an event
        text_lower = raw_text.lower()
        is_ev = any(kw in text_lower for kw in ["концерт", "вистава", "квитки", "шоу", "театр", "стендап", "фестиваль", "вхід", "початок", "відбудеться", "червня", "липня", "серпня", "мая"])
        
        # Simple Title extraction (first line or first sentence)
        lines = [l.strip() for l in raw_text.split("\n") if len(l.strip()) > 3]
        title = lines[0] if lines else "Подія в Києві"
        title = re.sub(r"[#*_~`]", "", title)[:80]
        
        # Determine Category
        category = "other"
        if "концерт" in text_lower:
            category = "concert"
        elif "театр" in text_lower or "вистава" in text_lower:
            category = "theater"
        elif "стендап" in text_lower or "standup" in text_lower:
            category = "standup"
        elif "дітя" in text_lower or "малеч" in text_lower:
            category = "kids"
        elif "безкоштовно" in text_lower or "вхід вільний" in text_lower:
            category = "free"
        elif "вечірк" in text_lower or "party" in text_lower or "диско" in text_lower:
            category = "party"
            
        # Try to parse date
        date_text = "Уточнюється"
        start_dt = None
        # Look for e.g. "12.06" or "12 червня"
        date_match = re.search(r"(\d{1,2})\s+(січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня)", text_lower)
        if date_match:
            date_text = f"{date_match.group(1)} {date_match.group(2)}"
            # Let's map month to number
            months = {"січ": 1, "лют": 2, "бер": 3, "кві": 4, "тра": 5, "чер": 6, "лип": 7, "сер": 8, "вер": 9, "жов": 10, "лис": 11, "гру": 12}
            m_num = 6 # Default June
            for k, v in months.items():
                if k in date_match.group(2):
                    m_num = v
                    break
            try:
                start_dt = datetime(datetime.utcnow().year, m_num, int(date_match.group(1)), 19, 0)
            except Exception:
                start_dt = datetime.utcnow() + timedelta(days=2) # Fallback to 2 days later
        else:
            # Fallback to date in future
            start_dt = datetime.utcnow() + timedelta(days=1)
            date_text = "Завтра о 19:00"

        # Price parsing
        price_min = None
        price_max = None
        price_text = "від 200 грн"
        is_free = "безкоштовно" in text_lower or "вхід вільний" in text_lower
        if is_free:
            price_text = "Безкоштовно"
            price_min = 0
        else:
            price_match = re.search(r"(від|ціна|вартість)?\s*(\d{3,4})\s*(грн)?", text_lower)
            if price_match:
                price_min = float(price_match.group(2))
                price_text = f"від {int(price_min)} грн"
                
        # Venue parsing
        venue = "Київ, Локація уточнюється"
        venue_match = re.search(r"(локація|місце|в|на|кінотеатр|клуб|театр)\s+([А-ЯІЄЇ][а-яієїa-z]+\s*[А-ЯІЄЇ]*[а-яієїa-z]*)", raw_text)
        if venue_match:
            venue = venue_match.group(2)
            
        return {
            "is_event": is_ev,
            "title": title,
            "short_description": raw_text[:120] + "...",
            "full_description": raw_text,
            "category": category,
            "city": "Київ",
            "district": "Шевченківський",
            "venue_name": venue,
            "address": None,
            "start_datetime": start_dt.isoformat() if isinstance(start_dt, datetime) else start_dt,
            "end_datetime": None,
            "date_text_original": date_text,
            "price_min": price_min,
            "price_max": price_max,
            "price_text_original": price_text,
            "is_free": is_free,
            "ticket_url": source_url,
            "confidence": 0.7 if is_ev else 0.2,
            "missing_fields": ["address"]
        }

    async def _rewrite_via_mock(self, event: Dict[str, Any]) -> str:
        desc = event["full_description"] or ""
        # Create a snappy 3-sentence summary with emojis
        snappy = (
            f"⚡️ Київ, це просто бомба! {event.get('title', 'Подія')} вже незабаром у столиці! "
            f"👀 Обіцяють неймовірну атмосферу, вибух емоцій та топових учасників. "
            f"🤫 Таке пропускати не можна — беріть друзів та бронюйте квитки вже зараз!"
        )
        return snappy

    async def _score_via_mock(self, event: Dict[str, Any]) -> int:
        score = 40
        if event.get("title"):
            score += 15
        if event.get("venue_name"):
            score += 15
        if event.get("start_datetime"):
            score += 15
        return min(score, 100)

    async def _detect_duplicate_via_mock(self, event: Any, candidates: List[Any]) -> Dict[str, Any]:
        """
        Basic regex matching on title and date closeness.
        """
        results = {}
        for cand in candidates:
            # Match 1: Title similarity
            t1 = event.title.lower()
            t2 = cand.title.lower()
            
            # Basic word overlap
            w1 = set(re.findall(r"\w+", t1))
            w2 = set(re.findall(r"\w+", t2))
            overlap = w1.intersection(w2)
            
            is_dup = False
            if len(w1) > 0 and (len(overlap) / len(w1)) > 0.6:
                # If titles overlap significantly, and dates are close
                if event.start_datetime and cand.start_datetime:
                    diff = abs((event.start_datetime - cand.start_datetime).days)
                    if diff <= 1:
                        is_dup = True
                else:
                    is_dup = True
                    
            results[cand.id] = is_dup
        return results

# Singleton instance
ai_processor = AIProcessor()
