"""
Expiration service cog - handles automatic alert expiration.
"""
import logging
from discord.ext import commands, tasks
from database.models import expire_alerts

logger = logging.getLogger(__name__)


class ExpirationServiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database_available = 'database_url' in bot.config
    
    def _check_database(self):
        """Check if database is available."""
        if not self.database_available:
            from database.connection import _pool
            self.database_available = _pool is not None
        return self.database_available
    
    async def cog_load(self):
        """Called when the cog is loaded."""
        # Check if database is available
        if not self._check_database():
            logger.warning("Database not available - expiration service will not start")
            return
        
        self.expiration_task.start()
        logger.info("Expiration service task started")
    
    async def cog_unload(self):
        """Called when the cog is unloaded."""
        self.expiration_task.cancel()
    
    @tasks.loop(hours=1)
    async def expiration_task(self):
        """Background task to expire old alerts."""
        try:
            await self.bot.wait_until_ready()
            
            # Check if database is available
            if not self._check_database():
                logger.warning("Database not available - skipping expiration cycle")
                return
            
            count = await expire_alerts()
            if count > 0:
                logger.info(f"Expired {count} alert(s)")
            else:
                logger.debug("No alerts expired")
                
        except Exception as e:
            logger.error(f"Error in expiration task: {e}", exc_info=True)
    
    @expiration_task.before_loop
    async def before_expiration_task(self):
        """Wait for bot to be ready before starting expiration task."""
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(ExpirationServiceCog(bot))
