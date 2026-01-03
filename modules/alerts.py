"""
Alerts cog - handles alert management commands.
"""
import logging
from datetime import datetime, timedelta
from discord.ext import commands
from discord.commands import slash_command
import discord
from database.models import (
    create_user, create_alert, get_user_alerts, deactivate_alert,
    deactivate_alerts_by_callsign
)
from utils.validators import (
    validate_callsign, validate_modes, parse_modes_string, get_default_modes
)
from utils.formatters import format_alerts_list

logger = logging.getLogger(__name__)


class AlertsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed_color = bot.config.get('embedcolor', 0x31a896)
        self.expiration_days = bot.config.get('expiration_days', 30)
        self.default_modes_pskreporter = bot.config.get('default_modes_pskreporter', ['FT8', 'FT4', 'PSK31', 'CW', 'RTTY'])
        self.database_available = 'database_url' in bot.config

    def _check_database(self):
        """Check if database is available."""
        if not self.database_available:
            from database.connection import _pool
            self.database_available = _pool is not None
        return self.database_available

    @slash_command(name="addalert", description="Add a new alert for a callsign or prefix")
    async def addalert(
        self,
        ctx,
        callsign_or_prefix: discord.Option(str, "Callsign or prefix to monitor", required=True),
        modes: discord.Option(str, "Comma-separated list of modes (e.g., FT8,FT4,CW). Leave empty to match all modes", required=False),
        data_source: discord.Option(str, "Data source (default: all)", required=False, choices=["all", "pskreporter", "dxcluster"])
    ):
        """Add a new alert for a callsign or prefix."""
        await ctx.defer(ephemeral=True)
        
        # Check if database is available
        if not self._check_database():
            await ctx.respond(
                "❌ Alert features are not available. Database is not configured. Please set DATABASE_URL in your environment.",
                ephemeral=True
            )
            return
        
        # Validate callsign
        if not validate_callsign(callsign_or_prefix):
            await ctx.respond(
                f"Invalid callsign format: {callsign_or_prefix}",
                ephemeral=True
            )
            return
        
        # Determine data source (default to "all" to monitor all sources)
        source = (data_source or "all").lower()
        
        # Parse and validate modes (empty = match all modes)
        if modes:
            mode_list = parse_modes_string(modes)
        else:
            # Empty modes list = match all modes
            mode_list = []
        
        is_valid, error_msg = validate_modes(mode_list, source)
        if not is_valid:
            await ctx.respond(
                f"Mode validation failed: {error_msg}",
                ephemeral=True
            )
            return
        
        try:
            # Create or update user
            await create_user(ctx.author.id, str(ctx.author))
            
            # Create alert
            alert_id = await create_alert(
                user_id=ctx.author.id,
                callsign_or_prefix=callsign_or_prefix.upper(),
                modes=mode_list,
                data_source=source,
                expiration_days=self.expiration_days
            )
            
            expires_at = datetime.utcnow() + timedelta(days=self.expiration_days)
            days_remaining = self.expiration_days
            
            embed = discord.Embed(
                title="✅ Alert Created",
                color=self.embed_color,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Callsign/Prefix", value=callsign_or_prefix.upper(), inline=True)
            embed.add_field(name="Modes", value=", ".join(mode_list) if mode_list else "All modes", inline=True)
            embed.add_field(name="Data Source", value=source.upper(), inline=True)
            embed.add_field(name="Expires", value=f"In {days_remaining} days", inline=True)
            embed.add_field(name="Alert ID", value=str(alert_id), inline=True)
            embed.set_footer(text="You will receive DM alerts when this callsign is spotted")
            
            await ctx.respond(embed=embed, ephemeral=True)
            logger.info(f"Alert created: user={ctx.author.id}, callsign={callsign_or_prefix}, modes={mode_list}, source={source}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}", exc_info=True)
            await ctx.respond(
                f"Failed to create alert: {str(e)}",
                ephemeral=True
            )

    @slash_command(name="removealert", description="Remove an alert by callsign/prefix or alert ID")
    async def removealert(
        self,
        ctx,
        callsign_or_prefix: discord.Option(str, "Callsign/prefix or alert ID to remove", required=False)
    ):
        """Remove an alert."""
        await ctx.defer(ephemeral=True)
        
        # Check if database is available
        if not self._check_database():
            await ctx.respond(
                "❌ Alert features are not available. Database is not configured. Please set DATABASE_URL in your environment.",
                ephemeral=True
            )
            return
        
        try:
            if callsign_or_prefix:
                # Try to parse as alert ID first
                try:
                    alert_id = int(callsign_or_prefix)
                    # Remove by ID
                    success = await deactivate_alert(alert_id, ctx.author.id)
                    if success:
                        await ctx.respond(
                            f"✅ Alert #{alert_id} has been removed.",
                            ephemeral=True
                        )
                    else:
                        await ctx.respond(
                            f"❌ Alert #{alert_id} not found or already inactive.",
                            ephemeral=True
                        )
                except ValueError:
                    # Not a number, treat as callsign/prefix
                    count = await deactivate_alerts_by_callsign(
                        ctx.author.id,
                        callsign_or_prefix.upper()
                    )
                    if count > 0:
                        await ctx.respond(
                            f"✅ Removed {count} alert(s) for {callsign_or_prefix.upper()}",
                            ephemeral=True
                        )
                    else:
                        await ctx.respond(
                            f"❌ No active alerts found for {callsign_or_prefix.upper()}",
                            ephemeral=True
                        )
            else:
                # List alerts and let user choose
                alerts = await get_user_alerts(ctx.author.id, active_only=True)
                if not alerts:
                    await ctx.respond(
                        "You have no active alerts to remove.",
                        ephemeral=True
                    )
                    return
                
                # Show list of alerts
                embed = format_alerts_list(alerts, self.embed_color)
                embed.title = "Your Active Alerts"
                embed.description = "Use `/removealert <callsign>` or `/removealert <alert_id>` to remove an alert"
                await ctx.respond(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error removing alert: {e}", exc_info=True)
            await ctx.respond(
                f"Failed to remove alert: {str(e)}",
                ephemeral=True
            )

    @slash_command(name="listalerts", description="List all your active alerts")
    async def listalerts(self, ctx):
        """List all active alerts for the user."""
        await ctx.defer(ephemeral=True)
        
        # Check if database is available
        if not self._check_database():
            await ctx.respond(
                "❌ Alert features are not available. Database is not configured. Please set DATABASE_URL in your environment.",
                ephemeral=True
            )
            return
        
        try:
            alerts = await get_user_alerts(ctx.author.id, active_only=True)
            
            if not alerts:
                embed = discord.Embed(
                    title="Your Active Alerts",
                    description="You have no active alerts.",
                    color=self.embed_color
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            embed = format_alerts_list(alerts, self.embed_color)
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error listing alerts: {e}", exc_info=True)
            await ctx.respond(
                f"Failed to list alerts: {str(e)}",
                ephemeral=True
            )


def setup(bot):
    bot.add_cog(AlertsCog(bot))
