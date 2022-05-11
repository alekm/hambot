import time
import discord
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
                description=hb_about + self.calc_uptime(),
                footer='hambot 1.1.0 by N4OG\n'
                       '\tbased on HamTheMan by thisguyistotallyben'
            ), ephemeral=True
        )

    @slash_command(name="study", description="License Study Information")
    async def study(self, ctx):
        embed=discord.Embed(title="Study using the Ham.Study app or Website",description=study_text, colour=0x31a896, timestamp=datetime.now())
        embed.set_image(url='https://blog.hamstudy.org/wp-content/uploads/2013/10/hamstudy_blue.png')
        await ctx.respond(embed=embed)


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


hb_about = ('**Author**\n'
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

study_text = ("A good way to study is with the ham.study application. You can install the "
              "application on a phone or tablet, or you can use it on-line. So, if you don't want to "
              "pay the $4 for the application, you can just access it through a browser from any "
              "device, even if you're not connected to the Internet. If you access hamstudy with a "
              "browser, it's always free, but you do need to Register with your email address for it "
              "to keep track of your progress.\n"
              'In either case, you should create an account by "Registering" on hamstudy.org. Do '
              'not use Google or Facebook - register with an email address. This creates a free '
              "account that keeps track of your progress.\n"
              "Once you've Registered for your account, do this:\n"
              "Login to ham.study using your username and password.\n"
              "Choose the Technician (2018 - 2022) exam by clicking on Technician (2018 - 2022):\n"
              "Click on Study Mode:\n"
              "Use the drop-down option in the top bar to change from All Questions to just T1:\n"
              "Click on T1.\n"
              "Now go through each question in T1, until you've Seen 100% of the questions, and "
              "your Aptitude is 85% or more.\n"
              "Only then go to the next Sub element (T2).\n"
              "Continue doing this with each sub element.\n"
              "Do not skip sub elements.\n"
              "Do not take practice exams until you've Seen 100% of each sub element and your "
              "Aptitude is 85% or more in each sub element.\n"
              "The bar graph on the right will display your Seen and Aptitude.\n"
              "If you have any questions about how to use hamstudy, or questions about the "
              "questions and answers, just reply to this email. There's an explanation of the answer "
              "when you're in Study Mode. Just click on I don't know. The reason for I don't know "
              "instead of guessing is the app is designed to give you questions more frequently if "
              "you select I don't know instead of getting it wrong.\n\n"

              "Once you are done studying for Technician you can do the same for General and "
              "Extra when ready. You would just substitute the appropriate element you are "
              "studying. All credit for this method goes to Norm K6YXH\n")