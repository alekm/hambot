"""
DXCC Prefix Lookup extension for qrm

---
Copyright (C) 2019-2020 classabbyamp, 0x5c  (as lookup.py)
Copyright (C) 2021 classabbyamp, 0x5c
SPDX-License-Identifier: LiLiQ-Rplus-1.1

Modified by N4OG 2022 - converted to slash command
Modified by N4OG 2024 - refactor
"""

import threading
from pathlib import Path
from datetime import datetime
import discord
from discord.ext import commands, tasks
from discord.commands import slash_command
from ctyparser import BigCty

CTY_PATH = Path("cty.json")

def run_update(cty_obj, dump_loc):
    try:
        updated = cty_obj.update()
        if updated:
            cty_obj.dump(dump_loc)
    except Exception as ex:
        print(f"[DXCCCog] Error updating CTY: {ex}")

class DXCCCog(commands.Cog):
    """DXCC Prefix Lookup Cog for hambot."""

    def __init__(self, bot):
        self.bot = bot
        self.embed_service = bot.get_cog('EmbedCog')
        try:
            self.cty = BigCty(CTY_PATH)
        except OSError:
            self.cty = BigCty()
        # Start periodic CTY updates after init
        self._update_cty.start()

    @slash_command(name="dx", description="Get DXCC information about a callsign prefix")
    async def dxcc_lookup(self, ctx, query: str):
        """Get DXCC info for a callsign prefix."""
        await ctx.trigger_typing()
        prefix = query.upper()
        embed = self._build_embed(prefix)
        await ctx.respond(embed=embed)

    def _build_embed(self, prefix: str) -> discord.Embed:
        """Builds an embed for DXCC lookup result."""
        base_title = f"DXCC Info for {prefix}"
        embed = discord.Embed(
            title=base_title,
            colour=0x31a896,
            timestamp=datetime.utcnow(),
            description=f"*Last Updated: {self.cty.formatted_version}*"
        )
        query = prefix
        while query:
            if query in self.cty:
                data = self.cty[query]
                embed.title = f"DXCC Info for {query}"
                embed.add_field(name="Entity", value=data.get("entity", "N/A"))
                embed.add_field(name="CQ Zone", value=str(data.get("cq", "")))
                embed.add_field(name="ITU Zone", value=str(data.get("itu", "")))
                embed.add_field(name="Continent", value=data.get("continent", ""))
                tz = data.get("tz", "")
                tz_str = f"+{tz}" if (isinstance(tz, int) and tz > 0) else str(tz)
                embed.add_field(name="Time Zone", value=tz_str)
                break
            else:
                query = query[:-1]
        else:
            embed.title = f"DXCC Info for {prefix} not found"
        return embed

    @tasks.loop(hours=24)
    async def _update_cty(self):
        """Periodically update the CTY database in a background thread."""
        threading.Thread(target=run_update, args=(self.cty, CTY_PATH), daemon=True).start()

def setup(bot: commands.Bot):
    bot.add_cog(DXCCCog(bot))
