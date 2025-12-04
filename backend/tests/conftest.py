"""
BharatBuild AI - Test Configuration and Fixtures
"""
import os
import asyncio
from typing import AsyncGenerator, Generator
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from faker import Faker

# Set testing environment
os.environ['TESTING'] = 'true'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key-for-testing'
os.environ['ANTHROPIC_API_KEY'] = 'test-api-key'

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token

fake = Faker()

# Test database setup
TEST_DATABASE_URL = 'sqlite+aiosqlite:///./test.db'
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope='session')
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='function')
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        email=fake.email(),
        hashed_password=get_password_hash('testpassword123'),
        full_name=fake.name(),
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user"""
    user = User(
        email=fake.email(),
        hashed_password=get_password_hash('adminpassword123'),
        full_name=fake.name(),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Generate authentication headers for test user"""
    token_data = {
        'sub': str(test_user.id),
        'email': test_user.email,
        'role': test_user.role.value
    }
    token = create_access_token(token_data)
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict:
    """Generate authentication headers for admin user"""
    token_data = {
        'sub': str(admin_user.id),
        'email': admin_user.email,
        'role': admin_user.role.value
    }
    token = create_access_token(token_data)
    return {'Authorization': f'Bearer {token}'}
