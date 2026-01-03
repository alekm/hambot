import os
import time
import json
import logging
from discord.ext import commands
import discord
from reporter import BotReporter
from database.connection import init_pool, close_pool
from database.models import create_schema

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
    
    # Initialize database if configured
    if 'database_url' in config:
        try:
            # Check if pool exists, if not initialize it
            from database.connection import _pool
            if _pool is None:
                logger.info("Initializing database connection pool...")
                await init_pool(config['database_url'])
                logger.info("Database connection pool initialized")
                
                # Create schema
                await create_schema()
                logger.info("Database schema initialized")
            else:
                logger.info("Database pool already initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database in on_ready: {e}", exc_info=True)
    else:
        logger.info("Database not configured - alert features will be disabled")

    # Start reporter
    await reporter.start()
    
    # Ensure healthcheck starts (fallback if cog_load wasn't called)
    healthcheck_cog = bot.get_cog('HealthcheckCog')
    if healthcheck_cog:
        healthcheck_cog.start_heartbeat()
    
    # Ensure metrics autosave starts (fallback if cog_load wasn't called)
    metrics_cog = bot.get_cog('MetricsCog')
    if metrics_cog:
        await metrics_cog.start_autosave()
    
    # Ensure spot monitoring starts after database is ready
    spot_monitor_cog = bot.get_cog('SpotMonitorCog')
    if spot_monitor_cog and 'database_url' in config:
        # Check if task is already running
        if hasattr(spot_monitor_cog, 'monitor_task') and not spot_monitor_cog.monitor_task.is_running():
            try:
                # Re-check database availability now that it's initialized
                if spot_monitor_cog._check_database():
                    # Test provider connections
                    for source, provider in spot_monitor_cog.providers.items():
                        try:
                            connected = await provider.test_connection()
                            if connected:
                                logger.info(f"{source} provider connection test passed")
                            else:
                                logger.warning(f"{source} provider connection test failed")
                        except Exception as e:
                            logger.error(f"Error testing {source} provider connection: {e}")
                    
                    # Start monitoring task
                    spot_monitor_cog.monitor_task.change_interval(minutes=spot_monitor_cog.poll_interval)
                    spot_monitor_cog.monitor_task.start()
                    logger.info(f"Spot monitoring task started (interval: {spot_monitor_cog.poll_interval} minutes)")
            except Exception as e:
                logger.error(f"Failed to start spot monitoring task: {e}", exc_info=True)


@bot.event
async def on_application_command(ctx):
    """Track slash command usage for reporting."""
    if ctx.command and ctx.command.name != "metrics":
        reporter.record_command(ctx.command.name)


@bot.event
async def on_close():
    """Cleanup when bot shuts down."""
    await reporter.stop()
    # Close database pool
    await close_pool()
    logger.info("Bot shutdown complete")


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
    
    # Database configuration (optional - for alert features)
    database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
    if database_url and not database_url.startswith('${{'):
        config['database_url'] = database_url
    else:
        logger.info("DATABASE_URL not set - alert features will be disabled")
    
    # Alert configuration (optional)
    # PSKReporter recommends querying no more than once every 5 minutes
    # Default to 5 minutes to avoid rate limiting (503 errors)
    config['poll_interval'] = int(os.getenv('PSKREPORTER_POLL_INTERVAL', '5'))
    config['expiration_days'] = int(os.getenv('ALERT_EXPIRATION_DAYS', '30'))
    config['alert_cooldown_minutes'] = int(os.getenv('ALERT_COOLDOWN_MINUTES', '5'))
    config['max_alerts_per_user_per_hour'] = int(os.getenv('MAX_ALERTS_PER_USER_PER_HOUR', '20'))
    
    # Default modes
    default_modes_str = os.getenv('DEFAULT_MODES_PSKREPORTER', 'FT8,FT4,PSK31,CW,RTTY')
    config['default_modes_pskreporter'] = [m.strip().upper() for m in default_modes_str.split(',') if m.strip()]
    
    # Enabled data sources
    enabled_sources_str = os.getenv('ENABLED_DATA_SOURCES', 'pskreporter,dxcluster')
    config['enabled_data_sources'] = [s.strip().lower() for s in enabled_sources_str.split(',') if s.strip()]
    
    # DX Cluster configuration (optional)
    # Default: dxmaps.com:7300 (known working public server)
    # Note: Some servers may require registration or have access restrictions
    config['dxcluster_host'] = os.getenv('DXCLUSTER_HOST', 'dxmaps.com')
    config['dxcluster_port'] = int(os.getenv('DXCLUSTER_PORT', '7300'))
    config['dxcluster_callsign'] = os.getenv('DXCLUSTER_CALLSIGN')  # Optional
    
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
bot.version = "2.1.0"  # Bot version for reporting

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
    'modules.alerts',
    'modules.spot_monitor',
    'modules.expiration_service',
    'modules.dxspots',
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
finally:
    # Cleanup on exit - but only if we're in an event loop
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule cleanup
            asyncio.create_task(close_pool())
        else:
            asyncio.run(close_pool())
    except:
        pass