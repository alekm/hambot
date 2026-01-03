"""
Reporter module for hambot to send heartbeat and usage statistics.

Supports two modes:
    1. Direct database writes (preferred) - if DATABASE_URL is configured
    2. HTTP API (fallback) - if REPORT_URL and REPORT_API_KEY are configured

Usage:
    from reporter import BotReporter
    reporter = BotReporter(bot)
    await reporter.start()
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
import aiohttp
import discord
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)


class BotReporter:
    """Handles reporting bot status and usage statistics."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.report_url = os.getenv("REPORT_URL")
        self.api_key = os.getenv("REPORT_API_KEY")
        
        # Will be set in start() when bot.config is available
        self.use_database = False
        self.use_api = bool(self.report_url and self.api_key)
        self.bot_id = 'unknown'

        # Track command usage
        self.command_counts: Dict[str, int] = {}
        self.start_time = datetime.now()

    async def start(self):
        """Start the reporter tasks"""
        # Check if database is available (preferred method)
        # bot.config should be available by now
        if hasattr(self.bot, 'config'):
            self.use_database = 'database_url' in self.bot.config
            self.bot_id = str(self.bot.config.get('clientID', 'unknown'))
        else:
            self.use_database = False
            self.bot_id = 'unknown'
        
        self.enabled = self.use_database or self.use_api

        if not self.enabled:
            logger.info("Bot reporter disabled: Set DATABASE_URL (preferred) or REPORT_URL+REPORT_API_KEY")
            return

        if self.use_database:
            logger.info(f"Bot reporter enabled: Using direct database writes (bot_id: {self.bot_id})")
        else:
            logger.info(f"Bot reporter enabled: Using HTTP API (bot_id: {self.bot_id}, URL: {self.report_url})")

        # Wait for bot to be ready
        await self.bot.wait_until_ready()

        # Start periodic tasks
        self.heartbeat_task.start()
        self.stats_task.start()
        logger.info("Reporter tasks started: heartbeat every 5min, stats every 1hr")

        # Send initial heartbeat
        logger.info("Sending initial heartbeat")
        await self.send_heartbeat()

    async def stop(self):
        """Stop the reporter tasks"""
        if self.heartbeat_task.is_running():
            self.heartbeat_task.cancel()
        if self.stats_task.is_running():
            self.stats_task.cancel()

    async def _make_request(
        self, endpoint: str, data: dict
    ) -> Optional[dict]:
        """Make an authenticated request to the API"""
        if not self.enabled:
            return None

        url = f"{self.report_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(
                            f"Failed to report to {endpoint}: {response.status}"
                        )
                        return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout reporting to {endpoint}")
            return None
        except Exception as e:
            logger.error(f"Error reporting to {endpoint}: {e}")
            return None

    async def send_heartbeat(self):
        """Send bot status heartbeat"""
        uptime = int((datetime.now() - self.start_time).total_seconds())
        version = getattr(self.bot, "version", "unknown")
        server_count = len(self.bot.guilds)

        # Try database first (preferred)
        if self.use_database:
            try:
                from database.connection import _pool
                if _pool is not None:
                    from database.models import record_heartbeat
                    await record_heartbeat(
                        status="online",
                        version=version,
                        uptime=uptime,
                        server_count=server_count,
                        timestamp=datetime.utcnow()
                    )
                    logger.debug(f"Heartbeat written to database")
                    return
            except Exception as e:
                logger.warning(f"Failed to write heartbeat to database: {e}, falling back to API")
        
        # Fall back to HTTP API
        if self.use_api:
            data = {
                "status": "online",
                "version": version,
                "uptime": uptime,
                "serverCount": server_count,
                "timestamp": int(datetime.now().timestamp() * 1000),  # Unix timestamp in milliseconds for JavaScript Date
            }

            result = await self._make_request("heartbeat", data)
            if result:
                logger.info(f"Heartbeat sent successfully to {self.report_url}/heartbeat")
            else:
                logger.warning(f"Heartbeat failed to send (check errors above)")

    async def send_stats(self):
        """Send aggregated usage statistics"""
        if not self.command_counts:
            logger.debug("No stats to report")
            return

        stats = [
            {"commandName": cmd, "count": count}
            for cmd, count in self.command_counts.items()
        ]

        logger.info(f"Sending stats: {len(stats)} command types, total commands: {sum(s['count'] for s in stats)}")

        # Try database first (preferred) - using batch writes for better performance
        if self.use_database:
            try:
                from database.connection import _pool
                if _pool is not None:
                    from database.models import record_stats
                    # record_stats now uses executemany for batch insert (10x faster)
                    await record_stats(
                        stats=stats,
                        period="hourly",
                        timestamp=datetime.utcnow()
                    )
                    logger.debug(f"Stats batch written to database ({len(stats)} commands)")
                    # Reset counters after successful write
                    self.command_counts.clear()
                    return
            except Exception as e:
                logger.warning(f"Failed to write stats to database: {e}, falling back to API")
        
        # Fall back to HTTP API
        if self.use_api:
            data = {
                "stats": stats,
                "period": "hourly",
                "timestamp": int(datetime.now().timestamp() * 1000),  # Unix timestamp in milliseconds for JavaScript Date
            }

            result = await self._make_request("stats", data)
            if result:
                logger.info(f"Stats sent successfully: {result}")
                # Reset counters after successful send
                self.command_counts.clear()

    def record_command(self, command_name: str):
        """Record a command execution"""
        # Check if enabled (may not be set if start() hasn't been called yet)
        if not hasattr(self, 'enabled') or not self.enabled:
            # Re-check if we should be enabled (in case start() hasn't been called yet)
            if hasattr(self.bot, 'config'):
                use_db = 'database_url' in self.bot.config
                use_api = bool(self.report_url and self.api_key)
                if not (use_db or use_api):
                    return
            else:
                return

        self.command_counts[command_name] = (
            self.command_counts.get(command_name, 0) + 1
        )
        total = sum(self.command_counts.values())
        logger.debug(f"Recorded command: {command_name} (total tracked: {total})")

    @tasks.loop(minutes=5)
    async def heartbeat_task(self):
        """Periodic heartbeat task (every 5 minutes)"""
        logger.debug("Sending periodic heartbeat")
        await self.send_heartbeat()

    @tasks.loop(hours=1)
    async def stats_task(self):
        """Periodic stats reporting task (every hour)"""
        await self.send_stats()

    @heartbeat_task.before_loop
    @stats_task.before_loop
    async def before_tasks(self):
        """Wait for bot to be ready before starting tasks"""
        await self.bot.wait_until_ready()


# Example integration in bot's main file:
"""
# In your main bot file (e.g., hambot.py):

from reporter import BotReporter

# ... your bot initialization code ...

bot = commands.Bot(command_prefix='/', intents=intents)
bot.config = config  # Make sure config is set before initializing reporter
bot.version = "1.0.0"  # Set your bot version

# Initialize reporter (after bot.config is set)
reporter = BotReporter(bot)

# Hook into command execution to track usage
@bot.event
async def on_application_command(ctx):
    if ctx.command and ctx.command.name != "metrics":
        reporter.record_command(ctx.command.name)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await reporter.start()

@bot.event
async def on_close():
    await reporter.stop()

# ... rest of your bot code ...
"""
