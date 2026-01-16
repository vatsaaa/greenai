import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
)
from typing import Optional
from typing import AsyncGenerator

# Load local .env for development (no secrets should be committed)
load_dotenv()

# NOTE: FastAPI async DB requires the `asyncpg` driver. Use the
# `postgresql+asyncpg://...` scheme for async engines. This value is
# read from the environment so docker-compose or the runtime can
# supply the correct hostname and credentials.
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. Set it in the environment or in a local .env for development."
    )

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query debugging
    future=True,
    pool_size=20,
    max_overflow=10,
)

# Factory for creating new AsyncSessions
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency Injection for FastAPI Routes.
    Yields a DB session and closes it automatically after the request.
    """
    async with AsyncSessionLocal() as session:
        yield session
