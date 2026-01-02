"""
Spot monitor cog - monitors spot sources and sends alerts.
"""
import logging
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from providers.pskreporter import PSKReporterProvider
from providers.base import BaseSpotProvider
from database.models import (
    get_active_alerts_by_source, record_spot_sent, check_spot_sent, create_user
)
from database.connection import get_pool
from utils.formatters import format_alert_embed

logger = logging.getLogger(__name__)


class SpotMonitorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed_color = bot.config.get('embedcolor', 0x31a896)
        self.poll_interval = bot.config.get('poll_interval', 2)
        self.enabled_sources = bot.config.get('enabled_data_sources', ['pskreporter'])
        self.database_available = 'database_url' in bot.config
        
        # Initialize providers
        self.providers: dict[str, BaseSpotProvider] = {}
        self._init_providers()
    
    def _check_database(self):
        """Check if database is available."""
        if not self.database_available:
            from database.connection import _pool
            self.database_available = _pool is not None
        return self.database_available
    
    def _init_providers(self):
        """Initialize spot providers based on enabled sources."""
        if 'pskreporter' in self.enabled_sources:
            self.providers['pskreporter'] = PSKReporterProvider()
            logger.info("PSKReporter provider initialized")
        # Future: Add other providers here
    
    async def cog_load(self):
        """Called when the cog is loaded."""
        # Check if database is available
        if not self._check_database():
            logger.warning("Database not available - spot monitoring will not start")
            return
        
        # Test provider connections
        for source, provider in self.providers.items():
            try:
                connected = await provider.test_connection()
                if connected:
                    logger.info(f"{source} provider connection test passed")
                else:
                    logger.warning(f"{source} provider connection test failed")
            except Exception as e:
                logger.error(f"Error testing {source} provider connection: {e}")
        
        # Configure and start monitoring task
        self.monitor_task.change_interval(minutes=self.poll_interval)
        self.monitor_task.start()
        logger.info(f"Spot monitoring task started (interval: {self.poll_interval} minutes)")
    
    async def cog_unload(self):
        """Called when the cog is unloaded."""
        self.monitor_task.cancel()
        
        # Close provider sessions
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                try:
                    await provider.close()
                except Exception as e:
                    logger.error(f"Error closing provider: {e}")
    
    @tasks.loop()
    async def monitor_task(self):
        """Background task to monitor spots and send alerts."""
        try:
            await self.bot.wait_until_ready()
            
            # Check if database is available
            if not self._check_database():
                logger.warning("Database not available - skipping spot monitoring cycle")
                return
            
            # Poll each enabled provider
            for source, provider in self.providers.items():
                try:
                    await self._process_provider(source, provider)
                except Exception as e:
                    logger.error(f"Error processing {source} provider: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"Error in monitor task: {e}", exc_info=True)
    
    @monitor_task.before_loop
    async def before_monitor_task(self):
        """Wait for bot to be ready before starting monitor task."""
        await self.bot.wait_until_ready()
    
    async def _process_provider(self, source: str, provider: BaseSpotProvider):
        """Process spots from a provider and send alerts."""
        # Get last check time (or default to 10 minutes ago)
        since = provider.last_check
        if since is None:
            since = datetime.utcnow() - timedelta(minutes=10)
        
        # Fetch recent spots
        spots = await provider.fetch_recent_spots(since=since)
        provider.last_check = datetime.utcnow()
        
        if not spots:
            logger.debug(f"No new spots from {source}")
            return
        
        logger.info(f"Processing {len(spots)} spots from {source}")
        
        # Get active alerts for this source
        alerts = await get_active_alerts_by_source(source)
        
        if not alerts:
            logger.debug(f"No active alerts for {source}")
            return
        
        # Match spots against alerts
        matches = []
        for spot in spots:
            for alert in alerts:
                # Check if callsign matches
                if spot.callsign.upper() == alert['callsign_or_prefix'].upper():
                    # Check if mode matches
                    if spot.mode.upper() in [m.upper() for m in alert['modes']]:
                        # Check if we've already sent this spot
                        already_sent = await check_spot_sent(
                            spot.spot_id,
                            spot.source,
                            alert['id']
                        )
                        if not already_sent:
                            matches.append((spot, alert))
        
        # Send alerts for matches
        for spot, alert in matches:
            try:
                await self._send_alert(spot, alert)
            except Exception as e:
                logger.error(f"Error sending alert for spot {spot.spot_id}: {e}", exc_info=True)
    
    async def _send_alert(self, spot, alert):
        """Send a DM alert to the user."""
        try:
            # Get user
            user = await self.bot.fetch_user(alert['user_id'])
            if user is None:
                logger.warning(f"User {alert['user_id']} not found")
                return
            
            # Create embed
            embed = format_alert_embed(
                callsign=spot.callsign,
                mode=spot.mode,
                frequency=spot.frequency,
                timestamp=spot.timestamp,
                spotter=spot.spotter,
                embed_color=self.embed_color
            )
            
            # Send DM
            try:
                await user.send(embed=embed)
                logger.info(f"Alert sent to {user.id} for {spot.callsign} on {spot.mode}")
            except discord.Forbidden:
                logger.warning(f"Cannot send DM to user {user.id} (blocked or DMs disabled)")
                return
            except discord.HTTPException as e:
                logger.error(f"HTTP error sending DM to {user.id}: {e}")
                return
            
            # Record in database
            await record_spot_sent(
                alert_id=alert['id'],
                spot_id=spot.spot_id,
                spot_source=spot.source,
                callsign=spot.callsign,
                mode=spot.mode,
                frequency=spot.frequency,
                timestamp=spot.timestamp
            )
            
            # Ensure user exists in database
            await create_user(user.id, str(user))
            
        except Exception as e:
            logger.error(f"Error in _send_alert: {e}", exc_info=True)
            raise


def setup(bot):
    bot.add_cog(SpotMonitorCog(bot))
