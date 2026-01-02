"""
Reporter module for hambot to send heartbeat and usage statistics to hambot.net

Usage:
    1. Copy this file to your hambot repository
    2. Add environment variables:
       - REPORT_URL: Base URL of the reporting API (e.g., https://hambot.net/api/bot)
       - REPORT_API_KEY: API key for authentication
    3. Import and initialize in your bot's main file:
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
    """Handles reporting bot status and usage statistics to hambot.net"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.report_url = os.getenv("REPORT_URL")
        self.api_key = os.getenv("REPORT_API_KEY")
        self.enabled = bool(self.report_url and self.api_key)

        # Track command usage
        self.command_counts: Dict[str, int] = {}
        self.start_time = datetime.now()

        if not self.enabled:
            logger.warning(
                "Bot reporter disabled: REPORT_URL and REPORT_API_KEY must be set"
            )
        else:
            logger.info(f"Bot reporter enabled, reporting to {self.report_url}")

    async def start(self):
        """Start the reporter tasks"""
        if not self.enabled:
            return

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

        data = {
            "status": "online",
            "version": getattr(self.bot, "version", "unknown"),
            "uptime": uptime,
            "serverCount": len(self.bot.guilds),
            "timestamp": int(datetime.now().timestamp()),  # Unix timestamp for server to use
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

        data = {
            "stats": stats,
            "period": "hourly",
        }

        result = await self._make_request("stats", data)
        if result:
            logger.info(f"Stats sent successfully: {result}")
            # Reset counters after successful send
            self.command_counts.clear()

    def record_command(self, command_name: str):
        """Record a command execution"""
        if not self.enabled:
            return

        self.command_counts[command_name] = (
            self.command_counts.get(command_name, 0) + 1
        )
        logger.debug(f"Recorded command: {command_name}")

    @tasks.loop(minutes=5)
    async def heartbeat_task(self):
        """Periodic heartbeat task (every 5 minutes)"""
        logger.info("Sending periodic heartbeat to reporting server")
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
# In your main bot file (e.g., main.py or bot.py):

from reporter import BotReporter

# ... your bot initialization code ...

bot = commands.Bot(command_prefix='/', intents=intents)
bot.version = "1.0.0"  # Set your bot version

# Initialize reporter
reporter = BotReporter(bot)

# Hook into command execution to track usage
@bot.event
async def on_command_completion(ctx):
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
