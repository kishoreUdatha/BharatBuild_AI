from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from app.core.config import settings

# Handle different database URLs
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine with appropriate settings for SQLite vs PostgreSQL
if "sqlite" in DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DB_ECHO,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        future=True
    )
else:
    # For AWS RDS: use NullPool to create fresh connections (no pooling)
    # Match the working create-tables endpoint: no custom connect_args
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DB_ECHO,
        poolclass=NullPool,
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Create base class for models
Base = declarative_base()


# Dependency to get DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session - only commits if there are pending changes"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Only commit if there are pending changes (new, dirty, or deleted objects)
            if session.new or session.dirty or session.deleted:
                await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Database initialization
async def init_db():
    """Initialize database"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection"""
    await engine.dispose()

