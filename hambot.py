import os
import time
import json
import logging
from discord.ext import commands
import discord
from reporter import BotReporter

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
# Events
# =======================
@bot.event
async def on_ready():
    logger.info(f'Username: {bot.user}')
    logger.info(f'Servers: {len(bot.guilds)}')
    logger.info('Ready...')
    logger.info('WELCOME TO HAMBOT\n-----\n')

    # Start reporter
    await reporter.start()


@bot.event
async def on_application_command(ctx):
    """Track slash command usage for reporting."""
    if ctx.command:
        reporter.record_command(ctx.command.name)


@bot.event
async def on_close():
    """Cleanup when bot shuts down."""
    await reporter.stop()


# =======================
# Load Configuration from Environment Variables
# =======================
def load_config_from_env():
    """Load configuration from environment variables with validation."""
    config = {}
    
    # Required environment variables
    required_vars = {
        'DISCORD_TOKEN': 'token',
        'DISCORD_OWNER_ID': 'ownerId',
        'DISCORD_CLIENT_ID': 'clientID',
        'HAMQTH_USERNAME': 'hamqth_username',
        'HAMQTH_PASSWORD': 'hamqth_password'
    }
    
    # Check for required variables
    missing_vars = []
    for env_var, config_key in required_vars.items():
        value = os.getenv(env_var)
        if not value:
            missing_vars.append(env_var)
        else:
            config[config_key] = value
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise SystemExit(1)
    
    # Optional environment variables with defaults
    config['embedcolor'] = int(os.getenv('EMBED_COLOR', '0x31a896'), 16)
    config['guildId'] = os.getenv('DISCORD_GUILD_ID', '')
    
    # HamQTH configuration
    config['hamqth'] = {
        'username': config['hamqth_username'],
        'password': config['hamqth_password']
    }
    # Remove the individual keys since they're now in hamqth dict
    del config['hamqth_username']
    del config['hamqth_password']
    
    logger.info('Configuration loaded from environment variables.')
    return config

try:
    config = load_config_from_env()
except Exception as ex:
    logger.error(f"Failed to load configuration: {ex}")
    raise SystemExit(1)

# Apply config properties to bot
bot.owner_id = int(config['ownerId'])
bot.start_time = time.time()
bot.config = config
bot.version = "2.0.0"  # Bot version for reporting

# Initialize reporter
reporter = BotReporter(bot)

# =======================
# Extension (Cog) Loading
# =======================
cogs = [
    'modules.lookup',
    'modules.dxcc',
    'modules.utils.embed',
    'modules.setstatus',
    'modules.misc',
    'modules.metrics',
    'modules.healthcheck',
    'modules.owner',
]

logger.info('Loading extensions...')
for cog in cogs:
    try:
        bot.load_extension(cog)
        logger.info(f'Loaded {cog}')
    except Exception as e:
        logger.error(f'Failed to load {cog}: {str(e)}')
        logger.error(f'Error type: {type(e).__name__}')
        import traceback
        logger.error(f'Traceback: {traceback.format_exc()}')
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
