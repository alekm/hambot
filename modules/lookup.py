import importlib
import os
import time
from datetime import datetime
from pathlib import Path

import discord
import requests
from ctyparser import BigCty
from discord.commands import \
    slash_command  # Importing the decorator that makes slash commands.
from discord.ext import commands, tasks
from onlinelookup import callook, hamqth, olerror, olresult

cty_path = Path("cty.json")

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


    @slash_command(name="cond", description="Replies with Current Solar Conditions")  
    async def cond(self, ctx):
        await ctx.trigger_typing()
        # remove possibly conficting old file
        if os.path.isfile("conditions.jpg"):
            os.remove("conditions.jpg")
        # download the latest conditions
        r = requests.get('https://www.hamqsl.com/solar101vhf.php')
        open('conditions.jpg', 'wb').write(r.content)
        embed=discord.Embed(title=":sunny: Current Solar Conditions :sunny:",description='Images from https://hamqsl.com', colour=0x31a896, timestamp=datetime.now())
        embed.set_image(url='attachment://conditions.jpg')
        with open('conditions.jpg', 'rb') as f:
            #await ctx.send(file=discord.File(f, 'conditions.gif'))
            await ctx.respond(embed=embed, file=discord.File(f, 'conditions.jpg'))
    
    @slash_command(name="drap", description="D Region Absorption Predictions Map" )
    async def drap(self, ctx):
        await ctx.trigger_typing()
        # remove possibly conficting old file
        if os.path.isfile("d-rap.png"):
            os.remove("d-rap.png")
        # download the latest conditions
        r = requests.get('https://services.swpc.noaa.gov/images/animations/d-rap/global_f05/d-rap/latest.png')
        open('d-rap.png', 'wb').write(r.content)
        embed=discord.Embed(title=":globe_with_meridians: D Region Absorption Predictions Map :globe_with_meridians:",description='Images from https://www.swpc.noaa.gov/', colour=0x31a896, timestamp=datetime.now())
        embed.set_image(url='attachment://d-rap.png')
        with open('d-rap.png', 'rb') as f:
            await ctx.respond(embed=embed, file=discord.File(f, 'd-rap.png'))    

    @slash_command(name="fof2", description="Frequency of F2 Layer Map" )
    async def fof2(self, ctx):
        await ctx.trigger_typing()
        fileName="fof2.jpg"
        svgName="fof2.svg"
        url="https://prop.kc2g.com/renders/current/fof2-normal-now.svg"
        embed=discord.Embed(title="Frequency of F2 Layer Map", colour=0x31a896, timestamp=datetime.now())
        embed.set_image(url=f'attachment://{fileName}')
        #if the muf image already exists and is less than 15 minutes old, send it
        if os.path.isfile(fileName) and int(time.time()-os.path.getmtime(fileName))/60<15:
            with open(fileName, 'rb') as f:
                await ctx.respond(embed=embed, file=discord.File(f, fileName))
        #if the muf image does not exist or the image is older than 15 minutes, cleanup files and grab a new one
        elif not os.path.isfile(fileName) or int(time.time()-os.path.getmtime(fileName))/60>=15:
            if os.path.isfile(fileName):
                os.remove(fileName)
            if os.path.isfile(svgName):
                os.remove(svgName)
            #download the latest muf map
            r = requests.get(url)
            open(svgName, 'wb').write(r.content)
            #convert svg to jpg
            convert_svg = os.system(f"rsvg-convert {svgName} > {fileName}")
            #cleanup svg because we don't need it hanging around once we have a jpg
            if os.path.isfile(svgName):
                os.remove(svgName)
            with open(fileName, 'rb') as f:
                await ctx.respond(embed=embed, file=discord.File(f, fileName))       

    @slash_command(name="muf", description="Maximum Usable Frequency Map")
    async def muf(self, ctx):
        await ctx.trigger_typing()
        fileName="muf.jpg"
        svgName="muf.svg"
        url="https://prop.kc2g.com/renders/current/mufd-normal-now.svg"
        embed=discord.Embed(title="Maximum Usable Frequency Map", colour=0x31a896, timestamp=datetime.now())
        embed.set_image(url=f'attachment://{fileName}')
        #if the muf image already exists and is less than 15 minutes old, send it
        if os.path.isfile(fileName) and int(time.time()-os.path.getmtime(fileName))/60<15:
            with open(fileName, 'rb') as f:
                await ctx.respond(embed=embed, file=discord.File(f, fileName))
        #if the muf image does not exist or the image is older than 15 minutes, cleanup files and grab a new one
        elif not os.path.isfile(fileName) or int(time.time()-os.path.getmtime(fileName))/60>=15:
            if os.path.isfile(fileName):
                os.remove(fileName)
            if os.path.isfile(svgName):
                os.remove(svgName)
            #download the latest muf map
            r = requests.get(url)
            open(svgName, 'wb').write(r.content)
            #convert svg to jpg
            convert_svg = os.system(f"rsvg-convert {svgName} > {fileName}")
            #cleanup svg because we don't need it hanging around once we have a jpg
            if os.path.isfile(svgName):
                os.remove(svgName)
            with open(fileName, 'rb') as f:
                await ctx.respond(embed=embed, file=discord.File(f, fileName))

    @slash_command(name="call", description="Display information about a callsign")
    async def call(self, ctx, callsign: str):
        await ctx.trigger_typing()

        result = self.lookup(callsign)
        result_embed_desc = ''
        if result == None:
            await ctx.respond('oof no callsign found', ephemeral=True)
            return
        elif result.source == 'Callook':
            result_embed_desc += self.format_for_callook(result)
        elif result.source == 'HamQTH':
            result_embed_desc += self.format_for_hamqth(result)
        embed=discord.Embed(title=result.callsign,description=result_embed_desc, colour=0x31a896, timestamp=datetime.now())
        embed.set_footer(text=f'Source: {result.source}')
        await ctx.respond(embed=embed, ephemeral=True)

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
        loc += f'\t**Grid Square:** {r.grid}\n'
        loc += f'\t**State:** {r.state}\n'
        loc += f'\t**City:** {r.city}\n'

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
