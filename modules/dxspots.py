"""
DX Spots display commands for hambot.
"""
import logging
from datetime import datetime
from discord.ext import commands
from discord.commands import slash_command, Option
from providers.dxcluster import DXClusterProvider
import discord

logger = logging.getLogger(__name__)


class DXSpotsCog(commands.Cog):
    """Cog for displaying DX Cluster spots."""
    
    def __init__(self, bot):
        self.bot = bot
        self.embed_color = bot.config.get('embedcolor', 0x31a896)
        self.dx_provider: DXClusterProvider = None
    
    async def cog_load(self):
        """Called when the cog is loaded."""
        # Get DX Cluster provider from spot monitor
        spot_monitor = self.bot.get_cog('SpotMonitorCog')
        if spot_monitor and 'dxcluster' in spot_monitor.providers:
            self.dx_provider = spot_monitor.providers['dxcluster']
            logger.info("DX Spots cog loaded, DX Cluster provider found")
        else:
            logger.warning("DX Spots cog loaded but DX Cluster provider not found")
    
    def _format_frequency(self, frequency: float) -> str:
        """Format frequency in a human-readable way."""
        if frequency >= 1_000_000:
            return f"{frequency / 1_000_000:.3f} MHz"
        elif frequency >= 1_000:
            return f"{frequency / 1_000:.2f} kHz"
        else:
            return f"{frequency:.0f} Hz"
    
    def _format_spot_embed(self, spots, title: str) -> discord.Embed:
        """Format spots into a Discord embed."""
        embed = discord.Embed(
            title=title,
            color=self.embed_color,
            timestamp=datetime.utcnow()
        )
        
        if not spots:
            embed.description = "No DX spots found."
            return embed
        
        # Build description with spot list
        lines = []
        for spot in spots[:20]:  # Limit to 20 spots per embed
            freq_str = self._format_frequency(spot.frequency) if spot.frequency else "N/A"
            spotter_str = f" by {spot.spotter}" if spot.spotter else ""
            time_str = spot.timestamp.strftime("%H:%M UTC")
            
            line = f"**{spot.callsign}** on {spot.mode} @ {freq_str}{spotter_str} ({time_str})"
            if spot.additional_data and 'comment' in spot.additional_data:
                line += f" - {spot.additional_data['comment']}"
            lines.append(line)
        
        embed.description = "\n".join(lines)
        
        if len(spots) > 20:
            embed.set_footer(text=f"Showing 20 of {len(spots)} spots")
        else:
            embed.set_footer(text=f"{len(spots)} spot(s)")
        
        return embed
    
    @slash_command(name="dxspots", description="Show recent DX Cluster spots")
    async def dxspots(
        self,
        ctx,
        filter: Option(
            str,
            description="Filter by callsign, band (e.g., '20m'), or count (number)",
            required=False,
            default=None
        )
    ):
        """Display recent DX Cluster spots."""
        # Try to get provider if not already set
        if not self.dx_provider:
            spot_monitor = self.bot.get_cog('SpotMonitorCog')
            if spot_monitor and 'dxcluster' in spot_monitor.providers:
                self.dx_provider = spot_monitor.providers['dxcluster']
        
        if not self.dx_provider:
            await ctx.respond(
                "DX Cluster is not enabled. Please add 'dxcluster' to ENABLED_DATA_SOURCES in your configuration.",
                ephemeral=True
            )
            return
        
        # Check if connected
        if not self.dx_provider.connected:
            await ctx.respond(
                "DX Cluster is not connected. The connection may still be establishing. Please try again in a moment.",
                ephemeral=True
            )
            return
        
        await ctx.defer(ephemeral=True)
        
        try:
            # Get recent spots from provider
            # Use the synchronous get_recent_spots method which reads from the buffer
            spots = self.dx_provider.get_recent_spots(count=100)
            
            if not spots:
                await ctx.respond("No DX spots available yet. The connection may still be establishing or no spots have been received.", ephemeral=True)
                return
            
            # Apply filters
            filtered_spots = spots
            
            if filter:
                filter_upper = filter.upper().strip()
                
                # Check if it's a number (count)
                try:
                    count = int(filter_upper)
                    filtered_spots = spots[:count]
                    title = f"Recent DX Spots (Last {count})"
                except ValueError:
                    # Check if it's a band (e.g., "20m", "40m")
                    band_freqs = {
                        '160M': (1800, 2000),
                        '80M': (3500, 4000),
                        '60M': (5330, 5410),
                        '40M': (7000, 7300),
                        '30M': (10100, 10150),
                        '20M': (14000, 14350),
                        '17M': (18068, 18168),
                        '15M': (21000, 21450),
                        '12M': (24890, 24990),
                        '10M': (28000, 29700),
                        '6M': (50000, 54000),
                        '2M': (144000, 148000),
                    }
                    
                    is_band = False
                    for band_name, (low_khz, high_khz) in band_freqs.items():
                        # Match variations: "20M", "20m", "20", etc.
                        band_num = band_name.replace('M', '')
                        if filter_upper in [band_name, band_name.replace('M', 'm'), band_num]:
                            # Filter by frequency range
                            filtered_spots = [
                                s for s in spots
                                if s.frequency and (low_khz * 1000 <= s.frequency <= high_khz * 1000)
                            ]
                            title = f"DX Spots on {band_name}"
                            is_band = True
                            break
                    
                    if not is_band:
                        # Assume it's a callsign filter
                        filtered_spots = [
                            s for s in spots
                            if filter_upper in s.callsign.upper() or 
                               (s.spotter and filter_upper in s.spotter.upper())
                        ]
                        title = f"DX Spots for {filter}"
            else:
                # Default: show last 10
                filtered_spots = spots[:10]
                title = "Recent DX Spots (Last 10)"
            
            if not filtered_spots:
                await ctx.respond(f"No DX spots found matching '{filter}'.", ephemeral=True)
                return
            
            embed = self._format_spot_embed(filtered_spots, title)
            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in dxspots command: {e}", exc_info=True)
            await ctx.respond(f"Error fetching DX spots: {str(e)}", ephemeral=True)


def setup(bot):
    bot.add_cog(DXSpotsCog(bot))
