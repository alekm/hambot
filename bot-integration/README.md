# Bot Integration

This directory contains the Python code to integrate hambot with the hambot.net reporting API.

## Installation

1. Copy `reporter.py` to your hambot repository

2. Install required dependencies (if not already installed):
```bash
pip install aiohttp
```

3. Add environment variables to your bot's configuration:

**docker-compose.yml:**
```yaml
environment:
  - REPORT_URL=https://hambot.net/api/bot
  - REPORT_API_KEY=your-secure-api-key-here
```

Or add to your `.env` file:
```
REPORT_URL=https://hambot.net/api/bot
REPORT_API_KEY=your-secure-api-key-here
```

4. Integrate the reporter into your bot's main file:

```python
from reporter import BotReporter

bot = commands.Bot(command_prefix='/', intents=intents)
bot.version = "1.0.0"  # Set your bot version

# Initialize reporter
reporter = BotReporter(bot)

# Track command usage
@bot.event
async def on_command_completion(ctx):
    reporter.record_command(ctx.command.name)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await reporter.start()

@bot.event
async def on_close():
    await reporter.stop()
```

## What it Does

The reporter module:
- Sends heartbeat updates every 5 minutes with bot status, version, uptime, and server count
- Tracks command usage and sends aggregated statistics every hour
- Authenticates with the API using the API key
- Handles errors gracefully and logs issues
- Can be disabled by not setting the environment variables

## API Key

The API key must match the `BOT_API_KEY` environment variable set on the hambot.net deployment. You can generate a secure key using:

```bash
openssl rand -hex 32
```

Make sure to use the same key in both:
1. The hambot bot configuration (REPORT_API_KEY)
2. The hambot.net website configuration (BOT_API_KEY)
