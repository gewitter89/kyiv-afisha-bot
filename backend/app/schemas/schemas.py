from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from decimal import Decimal

# --- AUTH SCHEMAS ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None


# --- CATEGORY SCHEMAS ---
class CategoryBase(BaseModel):
    slug: str
    name: str

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True


# --- SOURCE SCHEMAS ---
class SourceBase(BaseModel):
    name: str
    type: str # website, rss, telegram, manual
    url: Optional[str] = None
    telegram_channel_username: Optional[str] = None
    enabled: bool = True
    crawl_interval_minutes: int = 60

class SourceCreate(SourceBase):
    pass

class SourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    telegram_channel_username: Optional[str] = None
    enabled: Optional[bool] = None
    crawl_interval_minutes: Optional[int] = None

class Source(SourceBase):
    id: int
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- RAW ITEM SCHEMAS ---
class RawItemBase(BaseModel):
    source_id: int
    external_id: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    raw_text: str
    raw_html: Optional[str] = None
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None

class RawItemCreate(RawItemBase):
    pass

class RawItem(RawItemBase):
    id: int
    fetched_at: datetime
    hash: str
    processing_status: str # new, processed, error, ignored
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# --- EVENT SOURCE SCHEMAS ---
class EventSourceBase(BaseModel):
    source_id: Optional[int] = None
    raw_item_id: Optional[int] = None
    url: Optional[str] = None
    confidence: float = 1.0

class EventSource(EventSourceBase):
    id: int
    event_id: int

    class Config:
        from_attributes = True


# --- EVENT SCHEMAS ---
class EventBase(BaseModel):
    title: str
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    city: str = "Київ"
    district: Optional[str] = None
    venue_name: Optional[str] = None
    address: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    date_text_original: Optional[str] = None
    price_min: Optional[Decimal] = None
    price_max: Optional[Decimal] = None
    price_text_original: Optional[str] = None
    is_free: bool = False
    ticket_url: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    image_url: Optional[str] = None
    status: str = "draft" # draft, needs_review, approved, rejected, published, archived
    quality_score: Optional[int] = None
    duplicate_group_id: Optional[int] = None

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    venue_name: Optional[str] = None
    address: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    date_text_original: Optional[str] = None
    price_min: Optional[Decimal] = None
    price_max: Optional[Decimal] = None
    price_text_original: Optional[str] = None
    is_free: Optional[bool] = None
    ticket_url: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None
    quality_score: Optional[int] = None
    duplicate_group_id: Optional[int] = None

class Event(EventBase):
    id: int
    created_at: datetime
    updated_at: datetime
    published_to_telegram_at: Optional[datetime] = None
    event_sources: List[EventSource] = []

    class Config:
        from_attributes = True

class EventScheduleRequest(BaseModel):
    scheduled_at: datetime

class EventMergeRequest(BaseModel):
    target_event_id: int


# --- POST SCHEMAS ---
class PostBase(BaseModel):
    event_id: Optional[int] = None
    post_type: str # single_event, daily_digest, weekend_digest, ad
    telegram_channel_id: str
    text: str
    status: str = "scheduled" # scheduled, published, failed
    scheduled_at: datetime

class PostCreate(PostBase):
    pass

class Post(PostBase):
    id: int
    telegram_message_id: Optional[int] = None
    published_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# --- SUBMISSION SCHEMAS ---
class SubmissionBase(BaseModel):
    user_id: int
    username: Optional[str] = None
    title: str
    description: str
    date_text: str
    venue: Optional[str] = None
    address: Optional[str] = None
    price_text: Optional[str] = None
    link: Optional[str] = None
    image_file_id: Optional[str] = None
    status: str = "new" # new, accepted, rejected

class SubmissionCreate(SubmissionBase):
    pass

class Submission(SubmissionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- PARSER ERROR SCHEMAS ---
class ParserErrorBase(BaseModel):
    source_id: Optional[int] = None
    source_name: Optional[str] = None
    error_type: str
    error_message: str
    traceback: Optional[str] = None

class ParserError(ParserErrorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- DASHBOARD STATS ---
class DashboardStats(BaseModel):
    active_sources_count: int
    new_raw_items_count: int
    review_events_count: int
    published_today_count: int
    parser_errors_count: int
    recent_errors: List[ParserError]
