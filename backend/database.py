"""
Database configuration and connection management.

This module sets up both async and sync database connections for the mental health
services API. It provides session factories and dependency injection functions
for FastAPI routes.
"""
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_settings

settings = get_settings()

# Async engine for PostgreSQL with pgvector
# Clean up URL format for asyncpg (remove schema parameter)
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

# Remove schema parameter if present (asyncpg doesn't support it)
if "?schema=" in database_url:
    database_url = database_url.split("?schema=")[0]

async_engine = create_async_engine(
    database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    # Add connection arguments for asyncpg
    connect_args={"server_settings": {"jit": "off"}}
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Sync engine for migrations and initial setup
sync_engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency for FastAPI routes.
    
    Provides an async database session that automatically handles
    connection cleanup and error handling.
    
    Yields:
        AsyncSession: SQLAlchemy async database session
        
    Example:
        @app.get("/services")
        async def get_services(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(ServiceSearchView))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_db():
    """
    Sync database session dependency for compatibility.
    
    Provides a synchronous database session for migration scripts
    and other sync operations.
    
    Yields:
        Session: SQLAlchemy sync database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()