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
                footer='hambot 1.2 by N4OG\n'
                       '\tbased on HamTheMan by thisguyistotallyben'
            ), ephemeral=True
        )

    @slash_command(name="study", description="License Study Information")
    async def study(self, ctx):
        embed=discord.Embed(title="Study using the Ham.Study app or Website",description=study_text, colour=0x31a896, timestamp=datetime.now())
        embed.set_image(url='https://blog.hamstudy.org/wp-content/uploads/2013/10/hamstudy_blue.png')
        await ctx.respond(embed=embed)

    @slash_command(name="testing", description="License Testing Information")
    async def testing(self, ctx):
        await ctx.respond(embed=self.embed_service
                .generate(
                    title="Taking your ham license test with HRCC",
                    description=hb_testing
                    ), ephemeral=False
                )
    @slash_command(name="hamlive", description="Ham.Live Net Information")
    async def hamlive(self,ctx):
            await ctx.respond(embed=self.embed_service
                .generate(
                    title="Ham.Live",
                    description=hamlive_text
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
                '\t`/study`: Studying for your ham license test\n'
                '\t`/testing`: How to take your ham license test\n'
                '\t`/hamlive`: Information on using Ham.Live for the HRCC HF Net\n'
                '\n\t`/about`: About the bot\n'
                '\t`/uptime`: Bot uptime\n')


hb_about = ('**Author**\n'
             '\tAlek, N4OG\n\n'
             '\tAdd me to your server! https://discordapp.com/oauth2/authorize?client_id=947361185878147082&scope=bot&permissions=67488832\n\n'
             '\n**Tools**\n'
             '\tPython 3.10\n'
             '\tPy-Cord 2.0.0-beta.7\n'
             '\tlibrsvg2\n'
             '\n**Data Sources**\n'
             '\tSolar conditions from hamqsl.com\n'
             '\tOnline callsign lookups from HamQTH and callook.info\n'
             '\tMaximum Usable Frequency (MUF) data from prop.kc2g.com\n'
             '\n**Uptime**\n\t')

study_text = ("Ham Radio Crash Course Technician License Prep (2022-2026): https://www.youtube.com/watch?v=DdzQS10JnHU&list=PL1KAjn5rGhixvvb_jMZFWmbP97-t9Kyxk&index=1 \n\n"
        "A good way to study is with the https://ham.study application. You can install the application on a phone or tablet, or you can use it on-line. So, if you don't want to pay the $4 for the application, you can just access it through a browser from any device, even if you're not connected to the Internet. If you access hamstudy with a browser, it's always free, but you do need to Register with your email address for it to keep track of your progress.\n\n"
'In either case, you should create an account by "Registering" on hamstudy.org. Do not use Google or Facebook - register with an email address. This creates a free account that keeps track of your progress.\n\n '
"Once you've Registered for your account:\n\n"
"   • Login to ham.study using your username and password.\n"
"   • Choose the Technician exam by clicking on Technician (Starting Jul 1, 2022):\n"
"   • Click on Study Mode:\n"
"   • Use the drop-down option in the top bar to change from All Questions to just T1\n"
"   • Click on T1.\n"
"   • Go through each question in T1, until you've Seen 100% of the questions.\n"
"   • Go to the next Sub element (T2) when your aptitude is at 85% or more.\n"
"   • Continue doing this with each sub element.\n"
"   • Do not skip sub elements.\n"
"   • Do not take practice exams until you've Seen 100% of each sub element and your Aptitude is 85% or more in each sub element.\n"
"   • The bar graph on the right will display your Seen and Aptitude.\n\n"
"There's an explanation of the answer when you're in Study Mode. Just click on I don't know. The reason for I don't know instead of guessing is the app is designed to give you questions more frequently if you select I don't know instead of getting it wrong.\n\n"
"Once you are done studying for Technician, you can do the same for General and Extra. Substitute the appropriate element you are studying. All credit for this method goes to Norm, K6YXH.")

hb_testing = ("For more information about getting your ham license with the HRCC VE team, check this link: "
                "\n\nhttps://hrcc.wiki/en/home/VETesting")

hamlive_text = ("Ham.Live allows for a more interactive experience, by providing real-time signal reporting "
                "between net attendees and the ability to visually watch the net progress.\n\n"

                "To get setup with Ham.Live, please click on the dedicated HRCC HF Net Link\n" 
                "https://www.ham.live/views/livenet/637836da8531e399631ee065\n\n"

                "If you’re not logged in, you will be prompted to either login or set up an account. Account "
                "setup is easy. Either login via Google (preferred) or via an “email link”. Once "
                "authenticated, you will be prompted to accept terms and conditions and provide your "
                "callsign and location. Once enrolled, go back the aforementioned link:\n\n"

                "https://www.ham.live/views/livenet/637836da8531e399631ee065\n\n"

                "This is the net “waiting area” for the HRCC HF Net. If the net is running, you will "
                "immediately be placed into the live running net.\n\n"

                "If the net is not running, you’ll see “HRCC HF Net - Waiting for Net Start”. Be sure to "
                "click the purple star next to “HRCC HF Net” (so it’s solid purple) this will ensure that "
                "you’re following the net ongoing.\n\n"

                "If you arrive early, the “waiting area” will change to the live/running net screen "
                "automatically once Net Control starts the net.\n\n"

                "During the net you’re encouraged to provide signal reports to other attendees (assuming "
                "Net Control has the feature enabled). Adjacent to each attendee’s name you’ll see an input "
                "text box which looks like [  RS  ]. You can give anyone (other than yourself) a signal "
                "report, as long as they’re checked-in to the net. Reports are averaged in real-time. So "
                "if you receive a 59 and a 57 your RS field will indicate 58. You can give another station "
                "multiple signal reports, but doing so only replaces the prior report *you gave them (in "
                "other words you can’t skew the average by giving someone a 59 10 times in a row, for example. "
                "Each station gets one ‘vote’ to influence another station's overall report, so to speak). At "
                "the end of the net the finalized signal reports will be included in Net Control’s report "
                "and can be sent out to the group discord, if desired.\n\n"

                "The system allows for additional interactivity, for instance attendees can raise their hands "
                "(NCS can lower your hand). Stations can be highlighted by NCS. You can see another member’s "
                "location simply by hovering your mouse over their name.\n\n"

                "If you login via Google, your profile picture is whatever you happen to use with Google. "
                "If you login via the “Email Link” option, you can change your profile pic via the following "
                "URL:\n\n"

                "https://en.gravatar.com\n\n"

                "If you encounter any technical issues with the system feel free to contact support@ham.live")
