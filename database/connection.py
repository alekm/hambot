"""
Database connection management using asyncpg.
"""
import os
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


async def init_pool(database_url: str, min_size: int = None, max_size: int = None):
    """
    Initialize the database connection pool with production-ready settings.

    Args:
        database_url: PostgreSQL connection string
        min_size: Minimum number of connections (default: 10, env: DB_POOL_MIN)
        max_size: Maximum number of connections (default: 50, env: DB_POOL_MAX)
    """
    global _pool
    if _pool is not None:
        logger.warning("Database pool already initialized, closing existing pool")
        await close_pool()

    # Use environment variables or defaults
    if min_size is None:
        min_size = int(os.getenv('DB_POOL_MIN', '10'))
    if max_size is None:
        max_size = int(os.getenv('DB_POOL_MAX', '50'))

    try:
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60,
            max_queries=50000,  # Prevent connection leaks
            max_inactive_connection_lifetime=300  # 5 min idle timeout
        )
        logger.info(f"Database connection pool initialized (min={min_size}, max={max_size})")
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
