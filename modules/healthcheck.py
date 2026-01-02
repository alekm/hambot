import json
import time
import logging
from pathlib import Path
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

HEALTHCHECK_FILE = Path("/app/config/healthcheck.json")


class HealthcheckCog(commands.Cog):
    """
    Manages healthcheck heartbeat for Docker/Railway deployments.
    Writes a heartbeat file every 30 seconds with connection status.
    """

    def __init__(self, bot):
        self.bot = bot
        self._task_started = False
        logger.info("HealthcheckCog __init__ called")

    async def cog_load(self):
        """Start heartbeat task when cog loads."""
        logger.info("HealthcheckCog cog_load() called")
        await self.start_heartbeat()

    def start_heartbeat(self):
        """Start the heartbeat task (can be called from on_ready as fallback)."""
        if self._task_started:
            logger.info("Healthcheck heartbeat task already started")
            return
        try:
            if not self._heartbeat_task.is_running():
                self._heartbeat_task.start()
                self._task_started = True
                logger.info("Healthcheck heartbeat task started successfully")
            else:
                logger.info("Healthcheck heartbeat task already running")
        except Exception as e:
            logger.error(f"Failed to start healthcheck heartbeat task: {e}", exc_info=True)

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
            logger.info(f"Writing healthcheck to {HEALTHCHECK_FILE}")

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

            logger.info(
                f"Heartbeat written: {status['status']}, "
                f"guilds={status['guilds']}, "
                f"latency={status['latency']}ms"
            )
        except Exception as e:
            logger.error(f"Failed to write healthcheck heartbeat: {e}", exc_info=True)

    @_heartbeat_task.before_loop
    async def before_heartbeat(self):
        """Wait for bot to be ready before starting heartbeat."""
        logger.info("Healthcheck task before_loop: waiting for bot to be ready")
        await self.bot.wait_until_ready()
        logger.info("Healthcheck task before_loop: bot is ready, starting heartbeat loop")


def setup(bot):
    bot.add_cog(HealthcheckCog(bot))
