"""
DXCC Prefix Lookup extension for qrm
---
Copyright (C) 2019-2020 classabbyamp, 0x5c  (as lookup.py)
Copyright (C) 2021 classabbyamp, 0x5c
SPDX-License-Identifier: LiLiQ-Rplus-1.1

Modified by N4OG 2022 - converted to slash command
"""


import threading
from pathlib import Path
from ctyparser import BigCty
from discord.ext import commands, tasks
from discord.commands import (  # Importing the decorator that makes slash commands.
    slash_command,
)
#import common as cmn
from onlinelookup import olresult, hamqth, callook, olerror
import discord
from datetime import datetime




cty_path = Path("cty.json")


class DXCCCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed = bot.get_cog('EmbedCog')
        try:
            self.cty = BigCty(cty_path)
        except OSError:
            self.cty = BigCty()
    
    @slash_command(name="dx", description="Get DXCC information about a callsign prefix")
    async def _dxcc_lookup(self, ctx, query: str):
        await ctx.trigger_typing()
        query = query.upper()
        full_query = query
        embed = discord.Embed(title = "DXCC Info for ", colour=0x31a896, timestamp=datetime.now())
        embed.description = f"*Last Updated: {self.cty.formatted_version}*"
        while query:
            if query in self.cty.keys():
                data = self.cty[query]
                embed.add_field(name="Entity", value=data["entity"])
                embed.add_field(name="CQ Zone", value=data["cq"])
                embed.add_field(name="ITU Zone", value=data["itu"])
                embed.add_field(name="Continent", value=data["continent"])
                embed.add_field(name="Time Zone",
                                value=f"+{data['tz']}" if data["tz"] > 0 else str(data["tz"]))
                embed.title += query
                break
            else:
                query = query[:-1]
        else:
            embed.title += full_query + " not found"
        await ctx.respond(embed=embed)

    @tasks.loop(hours=24)
    async def _update_cty(self):
        update = threading.Thread(target=run_update, args=(self.cty, cty_path))
        update.start()


def run_update(cty_obj, dump_loc):
    update = cty_obj.update()
    if update:
        cty_obj.dump(dump_loc)


def setup(bot: commands.Bot):
    dxcccog = DXCCCog(bot)
    bot.add_cog(dxcccog)
    dxcccog._update_cty.start()
