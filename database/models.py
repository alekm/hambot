"""
Database models and schema definitions.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
import asyncpg
from database.connection import get_pool

logger = logging.getLogger(__name__)


async def create_schema():
    """Create database tables if they don't exist."""
    import asyncio
    
    pool = await get_pool()
    
    # Retry logic in case of connection issues
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with pool.acquire() as conn:
                # Create users table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        discord_id BIGINT PRIMARY KEY,
                        username TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """)
                
                # Create alerts table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
                        callsign_or_prefix TEXT NOT NULL,
                        is_prefix BOOLEAN NOT NULL DEFAULT FALSE,
                        modes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                        data_source TEXT NOT NULL DEFAULT 'pskreporter',
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        expires_at TIMESTAMP NOT NULL,
                        active BOOLEAN NOT NULL DEFAULT TRUE,
                        CONSTRAINT valid_expires_at CHECK (expires_at > created_at)
                    )
                """)
                
                # Create spot_history table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS spot_history (
                        id SERIAL PRIMARY KEY,
                        alert_id INTEGER NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
                        spot_id TEXT NOT NULL,
                        spot_source TEXT NOT NULL,
                        callsign TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        frequency REAL,
                        timestamp TIMESTAMP NOT NULL,
                        sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        UNIQUE(spot_id, spot_source)
                    )
                """)
                
                # Create alert_cooldowns table for throttling
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS alert_cooldowns (
                        alert_id INTEGER NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
                        last_sent TIMESTAMP NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (alert_id)
                    )
                """)
                
                # Create bot_status table for reporting (matches hambot.net schema)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS bot_status (
                        id SERIAL PRIMARY KEY,
                        status TEXT NOT NULL,
                        version TEXT NOT NULL,
                        uptime_seconds INTEGER NOT NULL,
                        server_count INTEGER NOT NULL,
                        last_heartbeat TIMESTAMP NOT NULL DEFAULT NOW(),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """)
                
                # Create usage_statistics table for reporting (matches hambot.net schema)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS usage_statistics (
                        id SERIAL PRIMARY KEY,
                        command_name TEXT NOT NULL,
                        execution_count INTEGER NOT NULL,
                        period TEXT NOT NULL DEFAULT 'hourly',
                        timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """)
                
                # Create alert_messages table to track sent DM messages for auto-deletion
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS alert_messages (
                        id SERIAL PRIMARY KEY,
                        message_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
                        channel_id BIGINT NOT NULL,
                        sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        deleted BOOLEAN NOT NULL DEFAULT FALSE,
                        UNIQUE(message_id, channel_id)
                    )
                """)
                
                # Create indexes for better query performance
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(active) WHERE active = TRUE
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_data_source ON alerts(data_source)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_expires_at ON alerts(expires_at) WHERE active = TRUE
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_spot_history_alert_id ON spot_history(alert_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_spot_history_spot_source ON spot_history(spot_source)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_spot_history_sent_at ON spot_history(sent_at)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_spot_history_alert_id_sent_at ON spot_history(alert_id, sent_at)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_bot_status_last_heartbeat ON bot_status(last_heartbeat)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_usage_statistics_command_name ON usage_statistics(command_name)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_usage_statistics_timestamp ON usage_statistics(timestamp)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alert_messages_sent_at ON alert_messages(sent_at) WHERE deleted = FALSE
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alert_messages_user_id ON alert_messages(user_id) WHERE deleted = FALSE
                """)

                # Additional indexes for performance optimization (added 2026-01-03)
                # Composite index for spot deduplication lookup (check_spot_sent)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_spot_history_spot_lookup
                    ON spot_history(spot_source, spot_id)
                """)

                # Composite index for alert user+source queries
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_user_source
                    ON alerts(user_id, data_source) WHERE active = TRUE
                """)

                # Index for callsign+mode+timestamp deduplication
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_spot_history_dedup
                    ON spot_history(alert_id, callsign, mode, timestamp)
                """)

                logger.info("Database schema created/verified (including performance indexes)")
                return  # Success, exit retry loop
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                logger.warning(f"Schema creation attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Failed to create schema after {max_retries} attempts: {e}")
                raise


async def create_user(discord_id: int, username: str) -> None:
    """Create a new user or update username if exists."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (discord_id, username)
            VALUES ($1, $2)
            ON CONFLICT (discord_id) DO UPDATE SET username = $2
        """, discord_id, username)


async def create_alert(
    user_id: int,
    callsign_or_prefix: str,
    modes: List[str],
    data_source: str = "all",
    expiration_days: int = 30
) -> int:
    """
    Create a new alert.
    
    Returns:
        The ID of the created alert
    """
    pool = await get_pool()
    expires_at = datetime.utcnow() + timedelta(days=expiration_days)
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO alerts (user_id, callsign_or_prefix, modes, data_source, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, user_id, callsign_or_prefix, modes, data_source, expires_at)
        
        return row['id']


async def get_user_alerts(user_id: int, active_only: bool = True) -> List[dict]:
    """Get all alerts for a user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT id, callsign_or_prefix, is_prefix, modes, data_source,
                   created_at, expires_at, active
            FROM alerts
            WHERE user_id = $1
        """
        params = [user_id]
        
        if active_only:
            query += " AND active = TRUE"
        
        query += " ORDER BY created_at DESC"
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def deactivate_alert(alert_id: int, user_id: int) -> bool:
    """Deactivate an alert. Returns True if alert was found and deactivated."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE alerts
            SET active = FALSE
            WHERE id = $1 AND user_id = $2 AND active = TRUE
        """, alert_id, user_id)
        
        return result == "UPDATE 1"


async def deactivate_alerts_by_callsign(user_id: int, callsign_or_prefix: str) -> int:
    """Deactivate all alerts matching a callsign/prefix for a user. Returns count deactivated."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE alerts
            SET active = FALSE
            WHERE user_id = $1 AND callsign_or_prefix = $2 AND active = TRUE
        """, user_id, callsign_or_prefix)
        
        # Parse "UPDATE N" to get count
        return int(result.split()[-1])


async def get_active_alerts_by_source(data_source: str) -> List[dict]:
    """Get all active alerts for a specific data source (including 'all' alerts)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, user_id, callsign_or_prefix, is_prefix, modes, data_source,
                   created_at, expires_at
            FROM alerts
            WHERE active = TRUE 
              AND (data_source = $1 OR data_source = 'all')
              AND expires_at > NOW()
            ORDER BY created_at
        """, data_source)
        
        return [dict(row) for row in rows]


async def record_spot_sent(
    alert_id: int,
    spot_id: str,
    spot_source: str,
    callsign: str,
    mode: str,
    frequency: Optional[float],
    timestamp: datetime
) -> None:
    """Record that a spot alert was sent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO spot_history (alert_id, spot_id, spot_source, callsign, mode, frequency, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (spot_id, spot_source) DO NOTHING
        """, alert_id, spot_id, spot_source, callsign, mode, frequency, timestamp)


async def check_spot_sent(spot_id: str, spot_source: str, alert_id: int, callsign: str, mode: str, timestamp: datetime) -> bool:
    """
    Check if a spot has already been sent for a specific alert.
    Checks both by spot_id+source AND by callsign+mode+timestamp (within 5 minutes)
    to prevent duplicate notifications across different data sources.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check by exact spot_id and source
        row = await conn.fetchrow("""
            SELECT 1 FROM spot_history
            WHERE spot_id = $1 AND spot_source = $2 AND alert_id = $3
            LIMIT 1
        """, spot_id, spot_source, alert_id)
        
        if row:
            return True
        
        # Check if we've already sent an alert for this callsign+mode within 5 minutes
        # (prevents duplicate notifications if same callsign is spotted on multiple sources)
        time_window = timestamp - timedelta(minutes=5)
        row = await conn.fetchrow("""
            SELECT 1 FROM spot_history
            WHERE alert_id = $1 
              AND callsign = $2 
              AND mode = $3 
              AND timestamp >= $4
            LIMIT 1
        """, alert_id, callsign.upper(), mode.upper(), time_window)
        
        return row is not None


async def check_alert_cooldown(alert_id: int, cooldown_minutes: int = 5) -> bool:
    """
    Check if an alert is in cooldown (throttling).
    
    Args:
        alert_id: Alert ID to check
        cooldown_minutes: Cooldown period in minutes
        
    Returns:
        True if alert is in cooldown (should not send), False if OK to send
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT last_sent FROM alert_cooldowns
            WHERE alert_id = $1
        """, alert_id)
        
        if row is None:
            # No cooldown record, OK to send
            return False
        
        last_sent = row['last_sent']
        cooldown_end = last_sent + timedelta(minutes=cooldown_minutes)
        
        if datetime.utcnow() < cooldown_end:
            # Still in cooldown
            return True
        
        # Cooldown expired, OK to send
        return False


async def update_alert_cooldown(alert_id: int) -> None:
    """Update the cooldown timestamp for an alert (call after sending)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO alert_cooldowns (alert_id, last_sent)
            VALUES ($1, NOW())
            ON CONFLICT (alert_id) DO UPDATE SET last_sent = NOW()
        """, alert_id)


async def get_user_alert_count_recent(user_id: int, minutes: int = 60) -> int:
    """
    Get count of alerts sent to a user in the last N minutes (for rate limiting).
    
    Args:
        user_id: User ID
        minutes: Time window in minutes
        
    Returns:
        Count of alerts sent
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Use make_interval for safe parameterized query
        row = await conn.fetchrow("""
            SELECT COUNT(DISTINCT sh.alert_id) as count
            FROM spot_history sh
            JOIN alerts a ON sh.alert_id = a.id
            WHERE a.user_id = $1
            AND sh.sent_at > NOW() - make_interval(mins => $2)
        """, user_id, minutes)
        
        return row['count'] if row else 0


async def expire_alerts() -> int:
    """Deactivate expired alerts. Returns count of expired alerts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE alerts
            SET active = FALSE
            WHERE active = TRUE AND expires_at <= NOW()
        """)
        
        # Parse "UPDATE N" to get count
        return int(result.split()[-1])


async def record_heartbeat(
    status: str,
    version: str,
    uptime: int,
    server_count: int,
    timestamp: Optional[datetime] = None
) -> None:
    """
    Record a bot heartbeat to the database (matches hambot.net schema).
    
    Args:
        status: Bot status (e.g., 'online')
        version: Bot version string
        uptime: Uptime in seconds
        server_count: Number of servers/guilds
        timestamp: Optional timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO bot_status (status, version, uptime_seconds, server_count, last_heartbeat)
            VALUES ($1, $2, $3, $4, $5)
        """, status, version, uptime, server_count, timestamp)


async def record_stats(
    stats: List[dict],
    period: str = "hourly",
    timestamp: Optional[datetime] = None
) -> None:
    """
    Record bot statistics to the database using batch insert (matches hambot.net schema).
    Uses executemany for ~10x better performance with multiple stats.

    Args:
        stats: List of dicts with 'commandName' and 'count' keys
        period: Period identifier (e.g., 'hourly')
        timestamp: Optional base timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    if not stats:
        return

    # Prepare batch data
    batch_data = []
    for stat in stats:
        # Use per-stat timestamp if provided, otherwise use base timestamp
        stat_timestamp = stat.get('timestamp')
        if stat_timestamp and isinstance(stat_timestamp, datetime):
            ts = stat_timestamp
        elif stat_timestamp:
            # Try to parse if it's a string
            try:
                ts = datetime.fromisoformat(stat_timestamp.replace('Z', '+00:00'))
            except:
                ts = timestamp
        else:
            ts = timestamp

        batch_data.append((
            stat.get('commandName'),
            stat.get('count'),
            period,
            ts
        ))

    # Batch insert using executemany (much faster than individual inserts)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.executemany("""
            INSERT INTO usage_statistics (command_name, execution_count, period, timestamp)
            VALUES ($1, $2, $3, $4)
        """, batch_data)


async def record_alert_message(message_id: int, user_id: int, channel_id: int, sent_at: Optional[datetime] = None) -> None:
    """
    Record a sent alert DM message for later deletion.
    
    Args:
        message_id: Discord message ID
        user_id: Discord user ID
        channel_id: Discord channel ID (DM channel)
        sent_at: Optional timestamp (defaults to now)
    """
    if sent_at is None:
        sent_at = datetime.utcnow()
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO alert_messages (message_id, user_id, channel_id, sent_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (message_id, channel_id) DO NOTHING
        """, message_id, user_id, channel_id, sent_at)


async def get_messages_to_delete(older_than_hours: int = 1) -> List[dict]:
    """
    Get alert messages that are older than specified hours and not yet deleted.
    
    Args:
        older_than_hours: Number of hours (default: 1)
        
    Returns:
        List of dicts with message_id, user_id, channel_id, sent_at
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        rows = await conn.fetch("""
            SELECT message_id, user_id, channel_id, sent_at
            FROM alert_messages
            WHERE deleted = FALSE AND sent_at < $1
            ORDER BY sent_at ASC
        """, cutoff_time)
        
        return [dict(row) for row in rows]


async def mark_message_deleted(message_id: int, channel_id: int) -> None:
    """Mark a message as deleted."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE alert_messages
            SET deleted = TRUE
            WHERE message_id = $1 AND channel_id = $2
        """, message_id, channel_id)


async def purge_old_deleted_messages(older_than_days: int = 7) -> int:
    """
    Delete old deleted message records from the database to prevent bloat.
    
    Args:
        older_than_days: Delete records that were deleted more than this many days ago (default: 7)
        
    Returns:
        Number of records deleted
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        cutoff_time = datetime.utcnow() - timedelta(days=older_than_days)
        result = await conn.execute("""
            DELETE FROM alert_messages
            WHERE deleted = TRUE AND sent_at < $1
        """, cutoff_time)
        
        # Parse "DELETE N" to get count
        return int(result.split()[-1]) if result.startswith("DELETE") else 0
