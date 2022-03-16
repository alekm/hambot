import os
import requests
import importlib
import discord
import time
from discord.ext import commands
from onlinelookup import olresult, hamqth, callook, olerror


class LookupCog(commands.Cog):
    def __init__(self, bot):
        # reload any changes to the lookup classes
        importlib.reload(olresult)
        importlib.reload(olerror)
        importlib.reload(callook)
        importlib.reload(hamqth)

        self.bot = bot
        self.embed = bot.get_cog('EmbedCog')
        self.callook = callook.CallookLookup()
        self.hamqth = hamqth.HamQTHLookup(
            bot.config['hamqth']['username'],
            bot.config['hamqth']['password'])

    @commands.command()
    async def cond(self, ctx):
        await ctx.trigger_typing()

        # remove possibly conficting old file
        if os.path.isfile("conditions.gif"):
            os.remove("conditions.gif")

        # download the latest conditions
        r = requests.get('https://www.hamqsl.com/solar101pic.php')
        open('conditions.gif', 'wb').write(r.content)

        with open('conditions.gif', 'rb') as f:
            await ctx.send(file=discord.File(f, 'conditions.gif'))

    @commands.command()
    async def muf(self,ctx):
        await ctx.trigger_typing()

        #if the muf image already exists and is less than 15 minutes old, send it
        if os.path.isfile("muf.jpg") and int(time.time()-os.path.getmtime("muf.jpg"))/60<15:
                with open('muf.jpg', 'rb') as f:
                    await ctx.send(file=discord.File(f, 'muf.jpg'))
        #if the muf image does not exist or the image is older than 15 minutes, cleanup files and grab a new one
        elif not os.path.isfile("muf.jpg") or int(time.time()-os.path.getmtime("muf.jpg"))/60>=15:
            if os.path.isfile("muf.jpg"):
                os.remove("muf.jpg")
            if os.path.isfile("muf.svg"):
                os.remove("muf.svg")
            #download the latest muf map
            r = requests.get('https://prop.kc2g.com/renders/current/mufd-normal-now.svg')
            open('muf.svg', 'wb').write(r.content)
            #convert svg to jpg
            convert_svg = os.system("rsvg-convert muf.svg > muf.jpg")
            #cleanup svg because we don't need it hanging around once we have a jpg
            if os.path.isfile("muf.svg"):
                os.remove("muf.svg")
            with open('muf.jpg', 'rb') as f:
                await ctx.send(file=discord.File(f, 'muf.jpg'))

    @commands.command()
    async def call(self, ctx, callsign: str):
        await ctx.trigger_typing()

        result = self.lookup(callsign)
        result_embed_desc = ''
        if result == None:
            await ctx.send('oof no callsign found')
            return
        elif result.source == 'Callook':
            result_embed_desc += self.format_for_callook(result)
        elif result.source == 'HamQTH':
            result_embed_desc += self.format_for_hamqth(result)

        await ctx.send(embed=self.embed
            .generate(
                title=result.callsign,
                description=result_embed_desc,
                footer=f'Source: {result.source}'
            ))

    def lookup(self, callsign):
        '''
        Try US callsigns first
        If that fails, try for all calls
        '''
        try:
            result = self.callook.lookup(callsign)
        except olerror.LookupResultError:
            try:
                result = self.hamqth.lookup(callsign)
            except:
                return None

        return result

    ''' lookup formatting '''

    def format_for_callook(self, r, hqr=None):
        rets = ''

        # extra info if neccessary
        if hqr is not None:
            itu = hqr.itu
            cq = hqr.cq

        # about field
        about = ''
        about += f'\t**Name:** {r.name}\n'
        if not r.club:
            about += f'\t**Class:** {r.opclass}\n'
        if r.prevcall != '':
            about += f'\t**Previous Callsign:** {r.prevcall}\n'

        # location field
        loc = ''
        loc += f'\t**Country:** {r.country}\n'
        loc += f'\t**State:** {r.state}\n'

        # club field
        club = ''
        if r.club:
            club = '**Club Info**\n'
            club += f'\t**Trustee:** {r.trusteename} ({r.trusteecall})\n\n'

        # links
        links = ''
        links += f'\t**QRZ:** https://qrz.com/db/{r.callsign}\n'
        links += f'\t**ULS:** {r.uls}\n'

        # build magical string
        rets = ('**About**\n'
                f'{about}'
                '\n**Location**\n'
                f'{loc}'
                '\n'
                f'{club}'
                '**Links**\n'
                f'{links}')

        return rets

        em = discord.Embed(title=r.callsign, url=f'https://qrz.com/db/{r.callsign}', description=rets, colour=0x00c0ff)
        em = em.set_footer(text='Source: callook.info')

        # return
        return em

    def format_for_hamqth(self, r):
        rets = ''

        # about field
        if r.name != '':
            rets = r.name
        elif 'nick' in r.raw:
            rets = r.raw['nick']
        else:
            rets = 'no name given'

        rets = f'**About**\n\t**Name:** {rets}\n\n'

        # location
        rets += f'**Location**\n\t**Country:** {r.country}\n'
        rets += f'\t**Grid Square:** {r.grid}\n'
        rets += f'\t**City:** {r.city}\n\n'

        # links
        rets += f'**Links**\n\t**QRZ:** https://qrz.com/db/{r.callsign}\n'

        return rets


def setup(bot):
    bot.add_cog(LookupCog(bot))
