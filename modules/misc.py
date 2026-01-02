from datetime import datetime, timedelta
from discord.ext import commands
from discord.commands import slash_command
import time

class MiscCog(commands.Cog):
    """Miscellaneous commands for hambot."""

    def __init__(self, bot):
        self.bot = bot
        # Will retrieve on-demand to avoid import loops, helpful if hot-reloading cogs
        self.embed_service = None

    async def cog_load(self):
        # Called when the cog is loaded/reloaded
        self.embed_service = self.bot.get_cog('EmbedCog')
        if not self.embed_service:
            print("Warning: EmbedCog not found. Embeds may not render correctly.")

    @slash_command(
        name="utc",
        description="Replies with Universal Coordinated Time."
    )
    async def utc(self, ctx):
        """Returns current UTC date and time."""
        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M:%S')
        desc = f'**Date:** {date_str}\n**Time:** {time_str} UTC'
        embed = self._embed("Universal Coordinated Time", desc)
        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(
        name="uptime",
        description="Show how long the bot has been running."
    )
    async def uptime(self, ctx):
        """Shows bot uptime."""
        up_seconds = int(time.time() - self.bot.start_time)
        uptime_str = self._format_uptime(up_seconds)
        embed = self._embed("Uptime", f"Online for: `{uptime_str}`")
        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(
            name="help", 
            description="hambot help"
    )
    async def help(self, ctx):
        """Shows help message and command list."""
        embed = self._embed(
            title="Help",
            description=(
                '**Core commands**\n'
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
                '\t`/uptime`: Bot uptime\n'
                '\n**Alert commands**\n'
                '\t`/addalert [callsign] [modes]`: Add a spot alert\n'
                '\t`/removealert [id]`: Remove an alert\n'
                '\t`/listalerts`: List your active alerts\n'
            )
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(
        name="about",
        description="Show info about hambot."
    )
    async def about(self, ctx):
        """Returns info about the bot."""
        embed = self._embed(
            title="About Hambot",
            description=(
                f"I'm Hambot, a helper for ham radio operators on Discord.\n\n"                

                f'\tAdd me to your server! https://discordapp.com/oauth2/authorize?client_id={self.bot.config["clientID"]}&scope=bot&permissions=2214972480\n\n'

                f"Owner: <@{self.bot.owner_id}>\n"
                f"[Source Code](https://github.com/alekm/hambot)\n"
                f"73!"
            )
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(
        name="study",
        description="Resources for ham radio study."
    )
    async def study(self, ctx):
        """Lists ham radio study resources."""
        embed = self._embed(
            title="Study Resources",
            description=(
                "Ham Radio Crash Course Technician License Prep (2022-2026): https://www.youtube.com/watch?v=DdzQS10JnHU&list=PL1KAjn5rGhixvvb_jMZFWmbP97-t9Kyxk&index=1 \n\n"
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
                "Once you are done studying for Technician, you can do the same for General and Extra. Substitute the appropriate element you are studying. All credit for this method goes to Norm, K6YXH."
            )
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(
        name="testing",
        description="Information about ham radio examinations."
    )
    async def testing(self, ctx):
        """Provides info about amateur radio testing options."""
        embed = self._embed(
            title="Testing Information",
            description=(
                "For more information about getting your ham license with the HRCC VE team, check this link: "
                "\n\nhttps://hrcc.wiki/en/home/VETesting"
            )
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(
        name="hamlive",
        description="Live event and webcast links for ham radio."
    )
    async def hamlive(self, ctx):
        """Shares live event and ham webcasts info."""
        embed = self._embed(
            title="Live Events & Webcasts",
            description=(
                "Ham.Live allows for a more interactive experience, by providing real-time signal reporting "
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

                "If you encounter any technical issues with the system feel free to contact support@ham.live"
            )
        )
        await ctx.respond(embed=embed, ephemeral=True)

    # ========== Helpers ==========

    def _embed(self, title: str, description: str):
        """Generate an embed using the embed service, or fallback if unavailable."""
        if self.embed_service and hasattr(self.embed_service, "generate"):
            # The embed service should be able to handle coloring/styling
            return self.embed_service.generate(title=title, description=description)
        # Fallback simple embed if embed service not loaded
        import discord
        color = self.bot.config.get("embedcolor", 0x31a896)
        if isinstance(color, str):
            color = int(color, 16) if color.startswith("0x") else int(color)
        embed = discord.Embed(title=title, description=description, color=color)
        return embed

    def _format_uptime(self, total_seconds: int) -> str:
        """Formats uptime in a human-readable way."""
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days: parts.append(f"{days}d")
        if hours: parts.append(f"{hours}h")
        if minutes: parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)


def setup(bot):
    bot.add_cog(MiscCog(bot))
