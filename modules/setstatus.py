from discord.ext import commands, tasks
import discord
import random
import logging
import aiohttp
from defusedxml import ElementTree as ET

logger = logging.getLogger(__name__)

SOLAR_URL = 'https://www.hamqsl.com/solarxml.php'
USER_AGENT = 'hambot (+https://hambot.net)'


class StatusCog(commands.Cog):
    """
    Periodically updates bot presence, rotating between amateur frequencies
    and current solar indices from hamqsl.com (N0NBH).

    Solar data is refreshed on a slow loop and cached; the presence rotation
    reads from that cache. If the feed is unavailable the rotation silently
    falls back to frequencies only.
    """

    FREQUENCIES = [
        '7.200',
        '14.313',
        '3.927',
        '3.860'
    ]

    def __init__(self, bot):
        self.bot = bot
        self.solar = {}
        self._last_status = None

    @commands.Cog.listener()
    async def on_ready(self):
        # Make sure we don't start the loops more than once
        if not self.solar_update.is_running():
            self.solar_update.start()
        if not self.status_change.is_running():
            self.status_change.start()

    def cog_unload(self):
        self.status_change.cancel()
        self.solar_update.cancel()

    @tasks.loop(minutes=45)
    async def solar_update(self):
        """
        Refresh cached solar indices. Solar data updates roughly hourly, so
        this runs far less often than the presence rotation.
        """
        try:
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            headers = {'User-Agent': USER_AGENT}
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(SOLAR_URL) as resp:
                    if resp.status != 200:
                        logger.warning(f"Solar feed returned HTTP {resp.status}")
                        return
                    text = await resp.text()

            root = ET.fromstring(text)
            data = root.find('solardata')
            if data is None:
                logger.warning("Solar feed missing solardata element")
                return

            values = {}
            for key in ('solarflux', 'kindex', 'aindex', 'sunspots'):
                node = data.find(key)
                if node is None or not node.text:
                    continue
                value = node.text.strip()
                # Fields occasionally carry "No Report" instead of a number
                if value.isdigit():
                    values[key] = value

            if values:
                self.solar = values
                logger.info(f"Solar indices updated: {values}")
        except Exception as e:
            # Never let a third-party outage stop the loop
            logger.warning(f"Failed to update solar indices: {e}")

    @tasks.loop(minutes=10)
    async def status_change(self):
        """
        Pick a status from the frequency list and any cached solar indices,
        and set it as the bot's presence.
        """
        try:
            options = self._status_options()
            if len(options) > 1 and self._last_status in options:
                options = [o for o in options if o != self._last_status]

            activity_type, name = random.choice(options)
            self._last_status = (activity_type, name)

            activity = discord.Activity(type=activity_type, name=name)
            await self.bot.change_presence(activity=activity)
        except Exception as e:
            logger.warning(f"Failed to update presence: {e}")

    def _status_options(self):
        """Build the rotation from frequencies plus whatever solar data we have."""
        options = [
            (discord.ActivityType.listening, freq)
            for freq in self.FREQUENCIES
        ]

        sfi = self.solar.get('solarflux')
        kindex = self.solar.get('kindex')
        aindex = self.solar.get('aindex')
        sunspots = self.solar.get('sunspots')

        if sfi and kindex:
            options.append((discord.ActivityType.watching, f"SFI {sfi} · K{kindex}"))
        if sunspots and aindex:
            options.append((discord.ActivityType.watching, f"SSN {sunspots} · A{aindex}"))

        return options

    @solar_update.before_loop
    @status_change.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(StatusCog(bot))
