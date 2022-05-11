import time
from discord.ext import commands
from datetime import datetime, timedelta
from discord.commands import (  # Importing the decorator that makes slash commands.
    slash_command,
)

'''
TODO:
- Oof counter
  - Make this server specific
'''


class MiscCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed_service = bot.get_cog('EmbedCog')

    @slash_command(name="utc", description="Replies with Universal Coordinated Time")
    async def utc(self, ctx):
        full_time = str(datetime.utcnow())
        full_time_split = full_time.strip().split()
        date = full_time_split[0]
        time = full_time_split[1][0:8]

        await ctx.respond(embed=self.embed_service
            .generate(
                title='Universal Coordinated Time',
                description=f'**Date:** {date}\n**Time:** {time}'
            ), ephemeral=True
        )

    @slash_command(name="uptime", description="hambot uptime")
    async def uptime(self, ctx):
        await ctx.respond(f'I have been alive for {self.calc_uptime()}')

    @slash_command(name="help", description="hambot help")
    async def help(self, ctx):
        await ctx.respond(embed=self.embed_service
            .generate(
                title="Help",
                description=help_message
            ), ephemeral=True
        )

    @slash_command(name="about", description="hambot about")
    async def about(self, ctx):
        await ctx.respond(embed=self.embed_service
            .generate(
                title="Help",
                description=htm_about + self.calc_uptime(),
                footer='hambot 1.1.0 by N4OG\n'
                       '\tbased on HamTheMan by thisguyistotallyben'
            ), ephemeral=True
        )

    def calc_uptime(self):
        up = str(timedelta(seconds=(time.time() - self.bot.start_time)))

        # parse it pretty-like
        upsplit = up.split(',', 1)
        if len(upsplit) == 1:
            days = '0'
        else:
            days = upsplit[0].split()[0]
            upsplit[0] = upsplit[1]

        upsplit = upsplit[0].split(':')
        if len(upsplit) != 3:
            return ''

        hours = upsplit[0]
        minutes = upsplit[1]
        if minutes[0] == '0':
            minutes = minutes[1]
        seconds = upsplit[2].split('.', 1)[0]
        if seconds[0] == '0':
            seconds = seconds[1]

        # horribly complicated, but appeases my awful need for proper plurality

        rets = ''
        rets += f"{days} day{'' if days == '1' else 's'}, "
        rets += f"{hours} hour{'' if hours == '1' else 's'}, "
        rets += f"{minutes} minute{'' if minutes == '1' else 's'}, "
        rets += f"{seconds} second{'' if seconds == '1' else 's'}"

        return rets


def setup(bot):
    bot.add_cog(MiscCog(bot))


'''
STRINGS AND STUFF
'''


# help dialog
help_message = ('**Core commands**\n'
                '\t`/cond`: Solar conditions (Source: hamqsl.com)\n'
                '\t`/muf`: Maximum Usable Frequency information (Source: prop.kc2g.com)\n'
                '\t`/fof2`: Frequency of F2 Layer (NVIS) information (Source: prop.kc2g.com)\n '
                '\t`/drap`: D Region Absorption Prediction map\n'
                '\t`/utc`: Time in UTC\n'
                '\t`/call [callsign]`: Callsign information (Sources: HamQTH'
                ', callook.info)\n'
                '\t`/dx [prefix]`: DXCC information about a call prefix\n'
                '\n\t`/about`: About the bot\n'
                '\t`/uptime`: Bot uptime\n')


htm_about = ('**Author**\n'
             '\tAlek, N4OG\n'
             '\n**Tools**\n'
             '\tPython 3.10\n'
             '\tPy-Cord 2.0.0-beta.7\n'
             '\tlibrsvg2\n'
             '\n**Data Sources**\n'
             '\tSolar conditions from hamqsl.com\n'
             '\tOnline callsign lookups from HamQTH and callook.info\n'
             '\tMaximum Usable Frequency (MUF) data from prop.kc2g.com\n'
             '\n**Uptime**\n\t')
