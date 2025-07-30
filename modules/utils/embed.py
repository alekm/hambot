import discord
from discord.ext import commands

class EmbedCog(commands.Cog):
    """
    Cog providing a reusable embed generator for consistent embed formatting across hambot.
    """

    def __init__(self, bot):
        self.bot = bot

    def generate(self, title='', description='', footer=''):
        """
        Generate a Discord Embed with consistent coloring and optional footer.
        Accepts title, description, and footer as keyword arguments.

        Example usage:
            embed = self.embed_service.generate(
                title="Some Title",
                description="Some body text",
                footer="Footer info"
            )
        """
        embed = discord.Embed(
            title=title,
            description=description,
            colour=self.bot.config.get('embedcolor', discord.Color.blue())
        )
        if footer:
            embed.set_footer(text=footer)
        return embed

def setup(bot):
    bot.add_cog(EmbedCog(bot))
