"""
Database connection management using asyncpg.
"""
import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None

# Export _pool for checking if initialized
__all__ = ['get_pool', 'init_pool', 'close_pool', '_pool']


async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool."""
    global _pool
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


async def init_pool(database_url: str, min_size: int = 5, max_size: int = 10):
    """
    Initialize the database connection pool.
    
    Args:
        database_url: PostgreSQL connection string
        min_size: Minimum number of connections in the pool
        max_size: Maximum number of connections in the pool
    """
    global _pool
    if _pool is not None:
        logger.warning("Database pool already initialized, closing existing pool")
        await close_pool()
    
    try:
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60
        )
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise


async def close_pool():
    """Close the database connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")
