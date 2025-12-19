from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator, Optional

from app.core.config import settings

# Create base class for models (can be defined before engine)
Base = declarative_base()

# Lazy engine initialization - create on first use to avoid import-time issues
_engine: Optional[AsyncEngine] = None
_async_session_local: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> str:
    """Get properly formatted database URL"""
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    return db_url


def get_engine() -> AsyncEngine:
    """Get or create the database engine (lazy initialization)"""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        if "sqlite" in db_url:
            _engine = create_async_engine(
                db_url,
                echo=settings.DB_ECHO,
                connect_args={"check_same_thread": False},
                poolclass=NullPool,
            )
        else:
            # For AWS RDS: use NullPool for fresh connections each time
            _engine = create_async_engine(
                db_url,
                echo=settings.DB_ECHO,
                poolclass=NullPool,
            )
    return _engine


def get_session_local() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory (lazy initialization)"""
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    return _async_session_local


# For backward compatibility, callers should use get_engine() instead of importing engine directly


# Backward compatibility: AsyncSessionLocal callable
def AsyncSessionLocal():
    """Create a new async session"""
    return get_session_local()()


# Dependency to get DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session - only commits if there are pending changes"""
    session_factory = get_session_local()
    async with session_factory() as session:
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
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection"""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
