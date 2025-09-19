import importlib
import os
import time
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands
from discord.commands import slash_command

import aiohttp
import aiofiles
import asyncio

from onlinelookup import callook, hamqth, olerror, olresult

import logging
logger = logging.getLogger(__name__)

# Path to the cty.json file, used for country lookups
# This file should be in the same directory as this module or adjust the path accordingly
# It contains the country codes and names used for callsign lookups.
# If you don't have this file, you can download it from https://www.country-files.com
CTY_PATH = Path("cty.json")


class LookupCog(commands.Cog):
    def __init__(self, bot):
        # Reload any lookup classes/cogs if hot-reloading
        importlib.reload(olresult)
        importlib.reload(olerror)
        importlib.reload(callook)
        importlib.reload(hamqth)

        self.bot = bot
        self.embed_service = bot.get_cog('EmbedCog')
        self.callook = callook.AsyncCallookLookup()
        self.hamqth = hamqth.AsyncHamQTHLookup(
            bot.config['hamqth']['username'],
            bot.config['hamqth']['password']
        )
        # If examtools is used add similar:
        # self.examtools = examtools.AsyncExamToolsLookup(...)

    async def cog_load(self):
        # If HamQTH uses an async connect, call it here
        try:
            await self.hamqth.connect()
            logger.info("HamQTH connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to HamQTH: {str(e)}")
            logger.warning("HamQTH lookups will not be available, but Callook will still work")

    @slash_command(name="cond", description="Replies with Current Solar Conditions")
    async def cond(self, ctx):
        await ctx.trigger_typing()
        fname = "conditions.jpg"
        url = 'https://www.hamqsl.com/solar101pic.php'
        try:
            if os.path.isfile(fname):
                os.remove(fname)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await ctx.respond(f"Failed to fetch solar image: {resp.status}", ephemeral=True)
                        return
                    data = await resp.read()
            async with aiofiles.open(fname, 'wb') as f:
                await f.write(data)
            embed = discord.Embed(
                title=":sunny: Current Solar Conditions :sunny:",
                description='Images from https://hamqsl.com',
                colour=0x31a896,
                timestamp=datetime.now()
            )
            embed.set_image(url=f'attachment://{fname}')
            async with aiofiles.open(fname, 'rb') as f:
                file = discord.File(f.name, fname)
                await ctx.respond(embed=embed, file=file)
        except Exception as ex:
            await ctx.respond(f"Failed to fetch solar conditions: {ex}", ephemeral=True)

    @slash_command(name="drap", description="D Region Absorption Predictions Map")
    async def drap(self, ctx):
        await ctx.trigger_typing()
        fname = "d-rap.png"
        url = 'https://services.swpc.noaa.gov/images/animations/d-rap/global_f05/d-rap/latest.png'
        try:
            if os.path.isfile(fname):
                os.remove(fname)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await ctx.respond(f"Failed to fetch DRAP map: {resp.status}", ephemeral=True)
                        return
                    data = await resp.read()
            async with aiofiles.open(fname, 'wb') as f:
                await f.write(data)
            embed = discord.Embed(
                title=":globe_with_meridians: D Region Absorption Predictions Map :globe_with_meridians:",
                description='Images from https://www.swpc.noaa.gov/',
                colour=0x31a896,
                timestamp=datetime.now()
            )
            embed.set_image(url=f'attachment://{fname}')
            async with aiofiles.open(fname, 'rb') as f:
                file = discord.File(f.name, fname)
                await ctx.respond(embed=embed, file=file)
        except Exception as ex:
            await ctx.respond(f"Failed to fetch DRAP map: {ex}", ephemeral=True)

    @slash_command(name="fof2", description="Frequency of F2 Layer Map")
    async def fof2(self, ctx):
        await ctx.trigger_typing()
        jpg_name = "fof2.jpg"
        svg_name = "fof2.svg"
        url = "https://prop.kc2g.com/renders/current/fof2-normal-now.svg"
        try:
            should_download = (
                not os.path.isfile(jpg_name)
                or (time.time() - os.path.getmtime(jpg_name)) / 60 >= 15
            )
            if should_download:
                for f in (jpg_name, svg_name):
                    if os.path.isfile(f):
                        os.remove(f)
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            await ctx.respond(f"Failed to fetch FOF2 SVG: {resp.status}", ephemeral=True)
                            return
                        data = await resp.read()
                async with aiofiles.open(svg_name, 'wb') as f:
                    await f.write(data)
                proc = await asyncio.create_subprocess_shell(
                    f"rsvg-convert {svg_name} -o {jpg_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    await ctx.respond(f"SVG-to-JPG conversion failed: {stderr.decode()}", ephemeral=True)
                    return
                if os.path.isfile(svg_name):
                    os.remove(svg_name)
            embed = discord.Embed(
                title="Frequency of F2 Layer Map",
                colour=0x31a896,
                timestamp=datetime.now()
            )
            embed.set_image(url=f'attachment://{jpg_name}')
            async with aiofiles.open(jpg_name, 'rb') as f:
                file = discord.File(f.name, jpg_name)
                await ctx.respond(embed=embed, file=file)
        except Exception as ex:
            await ctx.respond(f"Failed to fetch FOF2 map: {ex}", ephemeral=True)

    @slash_command(name="muf", description="Maximum Usable Frequency Map")
    async def muf(self, ctx):
        await ctx.trigger_typing()
        jpg_name = "muf.jpg"
        svg_name = "muf.svg"
        url = "https://prop.kc2g.com/renders/current/mufd-normal-now.svg"
        try:
            should_download = (
                not os.path.isfile(jpg_name)
                or (time.time() - os.path.getmtime(jpg_name)) / 60 >= 15
            )
            if should_download:
                for f in (jpg_name, svg_name):
                    if os.path.isfile(f):
                        os.remove(f)
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            await ctx.respond(f"Failed to fetch MUF SVG: {resp.status}", ephemeral=True)
                            return
                        data = await resp.read()
                async with aiofiles.open(svg_name, 'wb') as f:
                    await f.write(data)
                proc = await asyncio.create_subprocess_shell(
                    f"rsvg-convert {svg_name} -o {jpg_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    await ctx.respond(f"SVG-to-JPG conversion failed: {stderr.decode()}", ephemeral=True)
                    return
                if os.path.isfile(svg_name):
                    os.remove(svg_name)
            embed = discord.Embed(
                title="Maximum Usable Frequency Map",
                colour=0x31a896,
                timestamp=datetime.now()
            )
            embed.set_image(url=f'attachment://{jpg_name}')
            async with aiofiles.open(jpg_name, 'rb') as f:
                file = discord.File(f.name, jpg_name)
                await ctx.respond(embed=embed, file=file)
        except Exception as ex:
            await ctx.respond(f"Failed to fetch MUF map: {ex}", ephemeral=True)

    @slash_command(name="call", description="Display information about a callsign")
    async def call(self, ctx, callsign: str):
        await ctx.trigger_typing()
        logger.info(
            f"/call used by {ctx.author} (ID: {ctx.author.id}) "
            f"for {callsign} in "
            f"{getattr(ctx.guild, 'name', 'DM')}#{getattr(ctx.channel, 'name', str(ctx.channel.id))}"
        )
        result = await self.lookup(callsign)
        if result is None:
            await ctx.respond("No callsign information found.", ephemeral=True)
            return
        embed_desc = (
            self.format_for_callook(result) if result.source == "Callook"
            else self.format_for_hamqth(result)
            if result.source == "HamQTH" else "No data available."
        )
        embed = discord.Embed(
            title=result.callsign,
            description=embed_desc,
            colour=0x31a896,
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Source: {result.source}")
        await ctx.respond(embed=embed, ephemeral=True)


    async def lookup(self, callsign):
        """
        Try US (Callook) lookup first (async). Fall back to HamQTH (async), else None.
        """
        try:
            result = await self.callook.lookup(callsign)
        except olerror.LookupResultError:
            try:
                result = await self.hamqth.lookup(callsign)
            except Exception:
                return None
        return result

    def format_for_callook(self, r, hqr=None):
        about = f"\t**Name:** {r.name}\n"
        if not r.club:
            about += f"\t**Class:** {r.opclass}\n"
        if getattr(r, "prevcall", ""):
            about += f"\t**Previous Callsign:** {r.prevcall}\n"
        loc = (
            f"\t**Country:** {r.country}\n"
            f"\t**Grid Square:** {r.grid}\n"
            f"\t**State:** {r.state}\n"
            f"\t**City:** {r.city}\n"
        )
        club = ""
        if getattr(r, "club", False):
            club = (
                "\n**Club Info**\n"
                f"\t**Trustee:** {getattr(r, 'trusteename', '')} ({getattr(r, 'trusteecall', '')})\n"
            )
        links = (
            f"\t**QRZ:** https://qrz.com/db/{r.callsign}\n"
            f"\t**ULS:** {getattr(r, 'uls', '')}\n"
        )
        rets = (
            "**About**\n" + about +
            "\n**Location**\n" + loc +
            club + "\n**Links**\n" + links
        )
        return rets

    def format_for_hamqth(self, r):
        about = r.name if getattr(r, "name", "") else r.raw.get("nick", "no name given")
        about = f"**About**\n\t**Name:** {about}\n\n"
        loc = (
            f"**Location**\n\t**Country:** {getattr(r, 'country', '')}\n"
            f"\t**Grid Square:** {getattr(r, 'grid', '')}\n"
            f"\t**City:** {getattr(r, 'city', '')}\n\n"
        )
        links = f"**Links**\n\t**QRZ:** https://qrz.com/db/{getattr(r, 'callsign', '')}\n"
        return about + loc + links

def setup(bot):
    bot.add_cog(LookupCog(bot))
