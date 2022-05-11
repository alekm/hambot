from discord.ext import commands, tasks
import discord
import random


statuses = [    '7.200',
                '14.313',
                '3.927',
                '3.860'
            ]

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.status_change.start()
    
    @tasks.loop(minutes=10)
    async def status_change(self): 
        botStatus = random.choice(statuses)
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=botStatus))


def setup(bot):
    bot.add_cog(StatusCog(bot))

