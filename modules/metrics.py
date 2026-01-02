import json
import time
import asyncio
import logging
from pathlib import Path
from discord.ext import commands, tasks
from discord.commands import slash_command
import discord
import aiofiles

logger = logging.getLogger(__name__)


class MetricsCog(commands.Cog):
    """
    Cog for tracking and displaying per-server command usage metrics.
    Tracks command usage, errors, and provides admin-only access to statistics.
    """

    def __init__(self, bot):
        self.bot = bot
        self.embed_service = None
        self.metrics = {}
        self.metrics_file = Path("/app/config/metrics.json")
        self.lock = asyncio.Lock()
        self._autosave_started = False

    async def cog_load(self):
        """Called when the cog is loaded/reloaded."""
        await self.start_autosave()

    async def start_autosave(self):
        """Start the autosave task (can be called from on_ready as fallback)."""
        if self._autosave_started:
            return
        
        # Get embed service
        self.embed_service = self.bot.get_cog('EmbedCog')
        if not self.embed_service:
            logger.warning("EmbedCog not found. Using fallback embeds.")

        # Load metrics from disk
        await self._load_metrics()

        # Start autosave task
        try:
            if not self._autosave_task.is_running():
                self._autosave_task.start()
                self._autosave_started = True
            else:
                self._autosave_started = True
        except Exception as e:
            logger.error(f"Failed to start metrics autosave task: {e}", exc_info=True)

    async def cog_unload(self):
        """Called when the cog is unloaded."""
        # Stop autosave task
        self._autosave_task.cancel()

        # Final save
        await self._save_metrics()
        logger.info("MetricsCog unloaded, metrics saved")

    async def _load_metrics(self):
        """Load metrics from config/metrics.json"""
        try:
            if self.metrics_file.exists():
                async with aiofiles.open(self.metrics_file, 'r') as f:
                    content = await f.read()
                    self.metrics = json.loads(content)
                    logger.info(f"Loaded metrics for {len(self.metrics)} guild(s)")
            else:
                logger.info("No existing metrics file found, starting fresh")
                self.metrics = {}
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted metrics file: {e}. Starting fresh.")
            # Backup corrupted file
            backup_path = self.metrics_file.with_suffix('.json.corrupted')
            try:
                async with aiofiles.open(self.metrics_file, 'r') as src:
                    content = await src.read()
                async with aiofiles.open(backup_path, 'w') as dst:
                    await dst.write(content)
                logger.info(f"Backed up corrupted file to {backup_path}")
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupted file: {backup_error}")
            self.metrics = {}
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            self.metrics = {}

    async def _save_metrics(self):
        """Save metrics to config/metrics.json using atomic write."""
        async with self.lock:
            try:
                # Ensure config directory exists
                self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

                # Write to temp file first, then atomic rename
                temp_file = self.metrics_file.with_suffix('.json.tmp')
                metrics_json = json.dumps(self.metrics, indent=2)
                async with aiofiles.open(temp_file, 'w') as f:
                    await f.write(metrics_json)
                    await f.flush()  # Ensure data is written to disk
                
                # Atomic rename (safe on POSIX)
                temp_file.replace(self.metrics_file)
            except Exception as e:
                logger.error(f"Failed to save metrics: {e}", exc_info=True)

    @tasks.loop(minutes=5)
    async def _autosave_task(self):
        """Autosave metrics every 5 minutes."""
        await self._save_metrics()

    async def increment_command(self, guild_id: int, command_name: str):
        """Increment command counter for a specific guild."""
        if guild_id is None:
            logger.debug(f"Skipping metrics for DM command: {command_name}")
            return  # Skip DMs

        guild_key = str(guild_id)
        is_new_guild = False
        async with self.lock:
            is_new_guild = guild_key not in self.metrics
            if is_new_guild:
                self.metrics[guild_key] = {
                    "commands": {},
                    "errors": 0,
                    "total": 0,
                    "first_seen": time.time()
                }

            guild_metrics = self.metrics[guild_key]
            guild_metrics["commands"][command_name] = guild_metrics["commands"].get(command_name, 0) + 1
            guild_metrics["total"] += 1
        
        # Save immediately if this is a new guild (first command tracked)
        # Do this OUTSIDE the lock to avoid deadlock since _save_metrics() also acquires the lock
        if is_new_guild:
            await self._save_metrics()

    async def increment_error(self, guild_id: int):
        """Increment error counter for a specific guild."""
        if guild_id is None:
            logger.debug("Skipping error metrics for DM")
            return  # Skip DMs

        guild_key = str(guild_id)
        async with self.lock:
            if guild_key not in self.metrics:
                self.metrics[guild_key] = {
                    "commands": {},
                    "errors": 0,
                    "total": 0,
                    "first_seen": time.time()
                }
            self.metrics[guild_key]["errors"] += 1

    def get_guild_metrics(self, guild_id: int) -> dict:
        """Get metrics for a specific guild (read-only, no lock needed)."""
        guild_key = str(guild_id)
        return self.metrics.get(guild_key, {
            "commands": {},
            "errors": 0,
            "total": 0,
            "first_seen": time.time()
        })

    @commands.Cog.listener()
    async def on_application_command(self, ctx):
        """Track all slash command usage automatically."""
        guild_id = ctx.guild.id if ctx.guild else None
        command_name = ctx.command.name if ctx.command else "unknown"

        # Don't track the metrics command itself
        if command_name == "metrics":
            return

        await self.increment_command(guild_id, command_name)

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        """Track command errors automatically."""
        guild_id = ctx.guild.id if ctx.guild else None
        await self.increment_error(guild_id)
        # Note: Don't suppress the error, let it propagate for normal error handling

    def _is_authorized(self, ctx) -> bool:
        """Check if user is authorized to view metrics (admin or bot owner)."""
        # Bot owner always authorized
        if ctx.author.id == self.bot.owner_id:
            return True

        # DMs not allowed (no guild = no admin check possible)
        if ctx.guild is None:
            return False

        # Check for administrator permission
        return ctx.author.guild_permissions.administrator

    def _build_metrics_embed(self, guild, metrics: dict) -> discord.Embed:
        """Build formatted metrics embed."""
        # Calculate tracking duration
        first_seen = metrics.get("first_seen", time.time())
        days_tracking = (time.time() - first_seen) / 86400

        # Summary stats
        total_commands = metrics.get("total", 0)
        total_errors = metrics.get("errors", 0)
        error_rate = (total_errors / total_commands * 100) if total_commands > 0 else 0

        # Build description
        description = (
            f"**Total Commands:** {total_commands:,}\n"
            f"**Errors:** {total_errors:,} ({error_rate:.1f}%)\n"
            f"**Tracking Since:** <t:{int(first_seen)}:R>\n"
            f"**Days Tracked:** {days_tracking:.1f}"
        )

        # Create embed
        embed = self._safe_embed(
            title=f"Command Metrics: {guild.name}",
            description=description
        )

        # Command breakdown (sorted by usage)
        commands = metrics.get("commands", {})
        if commands and total_commands > 0:
            # Sort by count, descending
            sorted_commands = sorted(commands.items(), key=lambda x: x[1], reverse=True)

            # Top 10 commands (or all if fewer)
            top_commands = sorted_commands[:10]

            command_list = []
            for cmd_name, count in top_commands:
                percentage = (count / total_commands * 100)
                command_list.append(f"`/{cmd_name}`: {count:,} ({percentage:.1f}%)")

            embed.add_field(
                name="Command Usage (Top 10)",
                value="\n".join(command_list),
                inline=False
            )

            # If more than 10 commands, show count
            if len(sorted_commands) > 10:
                remaining = len(sorted_commands) - 10
                embed.set_footer(text=f"... and {remaining} more command(s)")
        else:
            embed.add_field(
                name="Command Usage",
                value="No commands tracked yet. Start using commands to see stats!",
                inline=False
            )

        return embed

    def _safe_embed(self, title: str, description: str) -> discord.Embed:
        """Generate embed with fallback if EmbedCog unavailable."""
        if self.embed_service and hasattr(self.embed_service, "generate"):
            return self.embed_service.generate(title=title, description=description)
        # Fallback
        return discord.Embed(
            title=title,
            description=description,
            colour=self.bot.config.get('embedcolor', 0x31a896)
        )

    @slash_command(
        name="metrics",
        description="View command usage statistics for this server (admin only)",
        default_member_permissions=discord.Permissions(administrator=True)
    )
    async def metrics(self, ctx):
        """Display server command usage metrics."""
        # Handle DMs
        if ctx.guild is None:
            embed = self._safe_embed(
                title="Not Available in DMs",
                description="Metrics are only available in servers, not in direct messages."
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Permission check
        if not self._is_authorized(ctx):
            embed = self._safe_embed(
                title="Permission Denied",
                description="Only server administrators or the bot owner can view metrics."
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Get metrics for this guild
        guild_metrics = self.get_guild_metrics(ctx.guild.id)

        # Build and send embed
        embed = self._build_metrics_embed(ctx.guild, guild_metrics)
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(MetricsCog(bot))
