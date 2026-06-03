from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from sqlalchemy.orm import Mapper
from app.core.config import settings

def sanitize_surrogates(text: str) -> str:
    if not isinstance(text, str):
        return text
    return "".join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))

@event.listens_for(Mapper, "before_insert")
def before_insert_listener(mapper, connection, target):
    for column in mapper.columns:
        try:
            if hasattr(target, column.key):
                val = getattr(target, column.key)
                if isinstance(val, str):
                    setattr(target, column.key, sanitize_surrogates(val))
        except AttributeError:
            pass

@event.listens_for(Mapper, "before_update")
def before_update_listener(mapper, connection, target):
    for column in mapper.columns:
        try:
            if hasattr(target, column.key):
                val = getattr(target, column.key)
                if isinstance(val, str):
                    setattr(target, column.key, sanitize_surrogates(val))
        except AttributeError:
            pass



# Async Engine for FastAPI
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Declarative base for models
Base = declarative_base()

# FastAPI DB Session Dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
