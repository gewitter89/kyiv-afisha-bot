from datetime import datetime
from typing import List, Optional
from sqlalchemy import Table, Column, Integer, BigInteger, String, Text, Boolean, DateTime, Float, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.core.database import Base

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="editor", nullable=False) # admin, editor
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False) # e.g. concert, standup, kids, date, free
    name = Column(String, nullable=False) # Friendly Ukrainian name e.g. "Концерти", "Безкоштовно"


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # website, rss, telegram, manual
    url = Column(String, nullable=True)
    telegram_channel_username = Column(String, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    crawl_interval_minutes = Column(Integer, default=60, nullable=False)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    raw_items = relationship("RawItem", back_populates="source", cascade="all, delete-orphan")
    event_sources = relationship("EventSource", back_populates="source")


class RawItem(Base):
    __tablename__ = "raw_items"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(String, nullable=True) # ID from RSS or telegram post ID
    url = Column(String, nullable=True)
    title = Column(String, nullable=True)
    raw_text = Column(Text, nullable=False)
    raw_html = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    hash = Column(String, unique=True, index=True, nullable=False) # SHA256 of text/url to prevent duplicates
    processing_status = Column(String, default="new", nullable=False) # new, processed, error, ignored
    error_message = Column(String, nullable=True)

    # Relationships
    source = relationship("Source", back_populates="raw_items")
    event_sources = relationship("EventSource", back_populates="raw_item", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    short_description = Column(Text, nullable=True)
    full_description = Column(Text, nullable=True)
    category = Column(String, nullable=True) # Matches a Category.slug
    subcategory = Column(String, nullable=True)
    city = Column(String, default="Київ", nullable=False)
    district = Column(String, nullable=True)
    venue_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    start_datetime = Column(DateTime, nullable=True)
    end_datetime = Column(DateTime, nullable=True)
    date_text_original = Column(String, nullable=True)
    price_min = Column(Numeric(10, 2), nullable=True)
    price_max = Column(Numeric(10, 2), nullable=True)
    price_text_original = Column(String, nullable=True)
    is_free = Column(Boolean, default=False, nullable=False)
    ticket_url = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    source_name = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    status = Column(String, default="draft", nullable=False) # draft, needs_review, approved, rejected, published, archived
    quality_score = Column(Integer, nullable=True)
    duplicate_group_id = Column(Integer, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_to_telegram_at = Column(DateTime, nullable=True)

    # Relationships
    event_sources = relationship("EventSource", back_populates="event", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="event")


class EventSource(Base):
    __tablename__ = "event_sources"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    raw_item_id = Column(Integer, ForeignKey("raw_items.id", ondelete="SET NULL"), nullable=True)
    url = Column(String, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="event_sources")
    source = relationship("Source", back_populates="event_sources")
    raw_item = relationship("RawItem", back_populates="event_sources")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True) # Nullable for digests
    post_type = Column(String, nullable=False) # single_event, daily_digest, weekend_digest, ad
    telegram_channel_id = Column(String, nullable=False)
    telegram_message_id = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    status = Column(String, default="scheduled", nullable=False) # scheduled, published, failed
    scheduled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="posts")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False) # Telegram User ID
    username = Column(String, nullable=True) # Telegram Username
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    date_text = Column(String, nullable=False)
    venue = Column(String, nullable=True)
    address = Column(String, nullable=True)
    price_text = Column(String, nullable=True)
    link = Column(String, nullable=True)
    image_file_id = Column(String, nullable=True) # Telegram Photo File ID
    status = Column(String, default="new", nullable=False) # new, accepted, rejected
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ParserError(Base):
    __tablename__ = "parser_errors"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=True)
    source_name = Column(String, nullable=True)
    error_type = Column(String, nullable=False) # e.g. ConnectionError, AIValidationError, HTMLParseError
    error_message = Column(Text, nullable=False)
    traceback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

