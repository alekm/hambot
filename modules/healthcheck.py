import json
import time
import logging
from pathlib import Path
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

HEALTHCHECK_FILE = Path("config/healthcheck.json")


class HealthcheckCog(commands.Cog):
    """
    Manages healthcheck heartbeat for Docker/Railway deployments.
    Writes a heartbeat file every 30 seconds with connection status.
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Start heartbeat task when cog loads."""
        self._heartbeat_task.start()
        logger.info("Healthcheck heartbeat started")

    async def cog_unload(self):
        """Stop heartbeat task on unload."""
        self._heartbeat_task.cancel()
        logger.info("Healthcheck heartbeat stopped")

    @tasks.loop(seconds=30)
    async def _heartbeat_task(self):
        """Write heartbeat file every 30 seconds."""
        try:
            # Ensure config directory exists
            HEALTHCHECK_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Prepare healthcheck data
            status = {
                "timestamp": time.time(),
                "status": "connected" if self.bot.is_ready() else "connecting",
                "guilds": len(self.bot.guilds),
                "latency": round(self.bot.latency * 1000, 2)  # ms
            }

            # Write atomically using temp file + rename
            temp_file = HEALTHCHECK_FILE.with_suffix('.json.tmp')
            with open(temp_file, 'w') as f:
                json.dump(status, f)
            temp_file.replace(HEALTHCHECK_FILE)

            logger.debug(
                f"Heartbeat: {status['status']}, "
                f"guilds={status['guilds']}, "
                f"latency={status['latency']}ms"
            )
        except Exception as e:
            logger.error(f"Failed to write healthcheck heartbeat: {e}")

    @_heartbeat_task.before_loop
    async def before_heartbeat(self):
        """Wait for bot to be ready before starting heartbeat."""
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(HealthcheckCog(bot))
