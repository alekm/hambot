import time
import json
from turtle import done
import discord
import logging
from discord.ext import commands, tasks
import random

intents = discord.Intents(
    guilds=True,
    members=True,
    messages=True,
    reactions=True
)

bot = discord.Bot(
    description="Hambot",
    intents=intents,
)

#logging.basicConfig(level=logging.INFO)


async def on_ready(self):
    print(f'  Username: {self.user}')
    print(f'  Servers:  {len(self.guilds)}')
    print('-----\nReady...')

    

print('WELCOME TO HAMBOT\n-----\n')

config = {}
with open('config.json', 'r') as f:
    print('loading config...')
    config = json.load(f)
    config['embedcolor'] = int(config['embedcolor'], 16)
    print('  config loaded.')

bot.owner_id = config['ownerId']
bot.start_time = time.time()
bot.config = config

#Load modules
cogs =  [
            'modules.lookup',
            'modules.dxcc',
            'modules.utils.embed',
            'modules.setstatus',
            'modules.misc',
        ]

print('loading extensions...')
for cog in cogs:
    bot.load_extension(cog)
print('  done.')
print('starting bot...')


try:
    bot.run(config['token'])
except discord.LoginFailure as ex:
    raise SystemExit("Error: Failed to authenticate: {}".format(ex))
except discord.ConnectionClosed as ex:
    raise SystemExit("Error: Discord gateway connection closed: [Code {}] {}".format(ex.code, ex.reason))
except ConnectionResetError as ex:
    raise SystemExit("ConnectionResetError: {}".format(ex))    
