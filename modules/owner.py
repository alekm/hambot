import discord
from discord.ext import commands
from discord.commands import slash_command
import psutil
import sys
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OwnerCog(commands.Cog):
    """
    Owner-only utilities for bot management.
    All commands are DM-only and restricted to the bot owner.
    """

    def __init__(self, bot):
        self.bot = bot
        self.process = psutil.Process()  # Current process for system stats

    async def _check_owner_dm(self, ctx) -> bool:
        """
        Verify command is from owner in DMs.
        Returns True if authorized, False otherwise (with error message sent).
        """
        if ctx.guild is not None:
            await ctx.respond("⛔ This command only works in DMs.", ephemeral=True)
            return False
        if ctx.author.id != self.bot.owner_id:
            await ctx.respond("⛔ Only the bot owner can use this command.", ephemeral=True)
            return False
        return True

    @slash_command(
        name="ownerstats",
        description="[OWNER] View bot statistics across all servers"
    )
    async def ownerstats(self, ctx):
        """Global statistics dashboard showing aggregate metrics."""
        if not await self._check_owner_dm(ctx):
            return

        await ctx.defer()  # Processing...

        # Get metrics from MetricsCog
        metrics_cog = self.bot.get_cog('MetricsCog')
        if not metrics_cog:
            await ctx.respond("❌ MetricsCog not loaded")
            return

        # Aggregate all server metrics
        total_commands = 0
        total_errors = 0
        command_counts = {}
        server_activity = {}

        for guild_id, guild_metrics in metrics_cog.metrics.items():
            total_commands += guild_metrics.get('total', 0)
            total_errors += guild_metrics.get('errors', 0)

            # Aggregate command counts
            for cmd, count in guild_metrics.get('commands', {}).items():
                command_counts[cmd] = command_counts.get(cmd, 0) + count

            # Track server activity
            server_activity[guild_id] = guild_metrics.get('total', 0)

        # Get top commands
        top_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Get top servers
        top_servers = sorted(server_activity.items(), key=lambda x: x[1], reverse=True)[:5]

        # Build embed
        embed = discord.Embed(
            title="🔧 Bot Owner Statistics",
            color=self.bot.config.get('embedcolor', 0x31a896),
            timestamp=datetime.utcnow()
        )

        # Overview
        total_members = sum(g.member_count for g in self.bot.guilds)
        uptime_seconds = int(time.time() - self.bot.start_time)
        uptime_str = self._format_uptime(uptime_seconds)

        embed.add_field(
            name="📊 Overview",
            value=(
                f"**Servers:** {len(self.bot.guilds)}\n"
                f"**Members:** {total_members:,}\n"
                f"**Uptime:** {uptime_str}"
            ),
            inline=False
        )

        # Commands
        error_rate = (total_errors / total_commands * 100) if total_commands > 0 else 0
        embed.add_field(
            name="⚡ Commands",
            value=(
                f"**Total:** {total_commands:,}\n"
                f"**Errors:** {total_errors:,} ({error_rate:.1f}%)"
            ),
            inline=True
        )

        # Top Commands
        if top_commands:
            cmd_list = "\n".join([f"`/{cmd}`: {count:,}" for cmd, count in top_commands])
            embed.add_field(
                name="🏆 Top Commands",
                value=cmd_list,
                inline=True
            )

        # Top Servers
        if top_servers:
            server_list = []
            for guild_id, count in top_servers:
                guild = self.bot.get_guild(int(guild_id))
                name = guild.name if guild else f"Unknown ({guild_id})"
                server_list.append(f"{name}: {count:,}")
            embed.add_field(
                name="🔝 Most Active Servers",
                value="\n".join(server_list),
                inline=False
            )

        await ctx.respond(embed=embed)

    @slash_command(
        name="serverlist",
        description="[OWNER] List all servers the bot is in"
    )
    async def serverlist(self, ctx):
        """List all servers with member counts and activity stats."""
        if not await self._check_owner_dm(ctx):
            return

        await ctx.defer()

        # Get metrics
        metrics_cog = self.bot.get_cog('MetricsCog')

        # Build server list
        servers = []
        for guild in sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True):
            guild_metrics = metrics_cog.get_guild_metrics(guild.id) if metrics_cog else {}
            servers.append({
                'name': guild.name,
                'id': guild.id,
                'members': guild.member_count,
                'commands': guild_metrics.get('total', 0),
                'joined': guild.me.joined_at
            })

        # Build embed (show first 15)
        embed = discord.Embed(
            title=f"📋 Server List ({len(servers)} total)",
            color=self.bot.config.get('embedcolor', 0x31a896),
            timestamp=datetime.utcnow()
        )

        for server in servers[:15]:
            embed.add_field(
                name=server['name'],
                value=(
                    f"ID: `{server['id']}`\n"
                    f"Members: {server['members']:,}\n"
                    f"Commands: {server['commands']:,}\n"
                    f"Joined: {server['joined'].strftime('%Y-%m-%d')}"
                ),
                inline=True
            )

        if len(servers) > 15:
            embed.set_footer(text=f"... and {len(servers) - 15} more servers")

        await ctx.respond(embed=embed)

    @slash_command(
        name="reloadcog",
        description="[OWNER] Reload a cog without restarting the bot"
    )
    async def reloadcog(self, ctx, cogname: str):
        """
        Hot reload a cog for quick updates without full restart.
        Usage: /reloadcog metrics
        """
        if not await self._check_owner_dm(ctx):
            return

        await ctx.defer()

        cog_module = f"modules.{cogname}"

        try:
            # Unload if already loaded
            if cog_module in self.bot.extensions:
                self.bot.unload_extension(cog_module)
                logger.info(f"Unloaded {cog_module}")

            # Load/reload
            self.bot.load_extension(cog_module)
            logger.info(f"Loaded {cog_module}")

            await ctx.respond(f"✅ Successfully reloaded `{cogname}`")
        except Exception as e:
            logger.error(f"Failed to reload {cogname}: {e}")
            await ctx.respond(f"❌ Failed to reload `{cogname}`:\n```{str(e)}```")

    @slash_command(
        name="listcogs",
        description="[OWNER] List all loaded cogs and their status"
    )
    async def listcogs(self, ctx):
        """Show all currently loaded cogs."""
        if not await self._check_owner_dm(ctx):
            return

        embed = discord.Embed(
            title="🔌 Loaded Cogs",
            color=self.bot.config.get('embedcolor', 0x31a896),
            timestamp=datetime.utcnow()
        )

        cog_list = []
        for name in self.bot.cogs.keys():
            cog_list.append(f"✅ {name}")

        embed.description = "\n".join(sorted(cog_list))
        embed.add_field(
            name="Total",
            value=f"{len(self.bot.cogs)} cogs loaded",
            inline=False
        )

        await ctx.respond(embed=embed)

    @slash_command(
        name="syshealth",
        description="[OWNER] View system health and diagnostics"
    )
    async def syshealth(self, ctx):
        """System diagnostics including memory, CPU, and latency."""
        if not await self._check_owner_dm(ctx):
            return

        await ctx.defer()

        # System stats
        memory = self.process.memory_info()
        memory_mb = memory.rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent(interval=0.1)

        # Uptime
        uptime_seconds = int(time.time() - self.bot.start_time)
        uptime_str = self._format_uptime(uptime_seconds)

        # Latency
        ws_latency = round(self.bot.latency * 1000, 2)

        # Versions
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        discord_version = discord.__version__

        embed = discord.Embed(
            title="💚 System Health",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=uptime_str,
            inline=True
        )

        embed.add_field(
            name="💾 Memory",
            value=f"{memory_mb:.1f} MB",
            inline=True
        )

        embed.add_field(
            name="⚡ CPU",
            value=f"{cpu_percent:.1f}%",
            inline=True
        )

        embed.add_field(
            name="🌐 Latency",
            value=f"{ws_latency} ms",
            inline=True
        )

        embed.add_field(
            name="🐍 Python",
            value=python_version,
            inline=True
        )

        embed.add_field(
            name="🤖 py-cord",
            value=discord_version,
            inline=True
        )

        # Guild info
        total_members = sum(g.member_count for g in self.bot.guilds)
        embed.add_field(
            name="📊 Connections",
            value=f"{len(self.bot.guilds)} servers\n{total_members:,} members",
            inline=False
        )

        await ctx.respond(embed=embed)

    def _format_uptime(self, total_seconds: int) -> str:
        """Format uptime in human-readable format (e.g., '2d 5h 30m 15s')."""
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return " ".join(parts)


def setup(bot):
    bot.add_cog(OwnerCog(bot))
