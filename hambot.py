import os
import time
import json
import logging
from discord.ext import commands
import discord

# =======================
# Logging Setup
# =======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hambot")

# =======================
# Discord Intents
# =======================
intents = discord.Intents(
    guilds=True,
    members=True,
    messages=True,
    reactions=True,
    message_content=True  # Set true if your bot reads messages' content
)

# =======================
# Bot Setup
# =======================
bot = commands.Bot(
    description="Hambot",
    command_prefix="/",  # Or consider using "/" or configurable
    intents=intents,
)

# =======================
# Event: on_ready
# =======================
@bot.event
async def on_ready():
    logger.info(f'Username: {bot.user}')
    logger.info(f'Servers: {len(bot.guilds)}')
    logger.info('Ready...')
    logger.info('WELCOME TO HAMBOT\n-----\n')


# =======================
# Load Configuration
# =======================
CONFIG_PATH = os.getenv("HAMBOT_CONFIG", "./config/config.json")
try:
    with open(CONFIG_PATH, 'r') as f:
        logger.info('Loading config...')
        config = json.load(f)
        config['embedcolor'] = int(config['embedcolor'], 16)
        logger.info('Config loaded.')
except FileNotFoundError:
    logger.error(f"Config file not found at {CONFIG_PATH}")
    raise SystemExit(1)
except Exception as ex:
    logger.error(f"Failed to load config: {ex}")
    raise SystemExit(1)

# Apply config properties to bot
bot.owner_id = config['ownerId']
bot.start_time = time.time()
bot.config = config

# =======================
# Extension (Cog) Loading
# =======================
cogs = [
    'modules.lookup',
    'modules.dxcc',
    'modules.utils.embed',
    'modules.setstatus',
    'modules.misc',
]

logger.info('Loading extensions...')
for cog in cogs:
    try:
        bot.load_extension(cog)
        logger.info(f'Loaded {cog}')
    except Exception as e:
        logger.error(f'Failed to load {cog}: {e}')
logger.info('All extensions attempted.')

# =======================
# Run Bot
# =======================
logger.info('Starting bot...')
try:
    bot.run(config['token'])
except discord.LoginFailure as ex:
    logger.critical(f"Failed to authenticate: {ex}")
    raise SystemExit("Error: Failed to authenticate with Discord")
except discord.ConnectionClosed as ex:
    logger.critical(f"Discord gateway connection closed: [Code {ex.code}] {ex.reason}")
    raise SystemExit(f"Error: Discord gateway connection closed: [Code {ex.code}] {ex.reason}")
except ConnectionResetError as ex:
    logger.critical(f"ConnectionResetError: {ex}")
    raise SystemExit(f"ConnectionResetError: {ex}")
except Exception as ex:
    logger.critical(f"Unexpected error: {ex}")
    raise SystemExit(f"Critical unexpected error: {ex}")
