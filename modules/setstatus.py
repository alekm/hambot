from discord.ext import commands, tasks
import discord
import random

class StatusCog(commands.Cog):
    """
    Periodically updates bot presence/status to a random amateur frequency.
    """

    STATUSES = [
        '7.200',
        '14.313',
        '3.927',
        '3.860'
    ]

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Make sure we don't start the loop more than once
        if not self.status_change.is_running():
            self.status_change.start()

    @tasks.loop(minutes=10)
    async def status_change(self):
        """
        Select a random frequency from the list and set as the bot's Listening activity.
        """
        freq = random.choice(self.STATUSES)
        # Now more descriptive: "Listening to 7.200" etc.
        activity = discord.Activity(type=discord.ActivityType.listening, name=f"{freq}")
        await self.bot.change_presence(activity=activity)

def setup(bot):
    bot.add_cog(StatusCog(bot))
