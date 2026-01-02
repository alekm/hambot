# hambot

hambot (hb) is a Discord bot for amateur radio lookups: callsigns (globally with HamQTH), solar conditions, Maximum Usable Frequencies, UTC/time, and more. Adapted from thisguyistotallben/hamtheman.

## Features
- Global callsign lookups (HamQTH)
- Solar weather/maps
- MUF charts
- UTC/time tools
- **Spot alerts** - Get notified when specific callsigns or prefixes are spotted on digital modes (FT8, FT4, PSK31, CW, RTTY, etc.)
- **Automatic expiration** - Alerts automatically expire after a configurable period
- **Rate limiting** - Built-in throttling to prevent alert spam

## Getting Started

You'll need:
- A Discord bot [developer token](https://discordapp.com/developers/applications/)
- A [HamQTH account](https://hamqth.com)

**Setup:**
1. Copy the environment variables template and edit your details:
        
```cp env.example .env```

2. Edit your Discord bot token, Discord user ID (numeric), Discord client ID (numeric), and HamQTH credentials into `.env`.

**Required Environment Variables:**
- `DISCORD_TOKEN`: Your Discord bot token
- `DISCORD_OWNER_ID`: Your Discord user ID (numeric)
- `DISCORD_CLIENT_ID`: Your Discord bot's client ID (numeric)
- `HAMQTH_USERNAME`: Your HamQTH username
- `HAMQTH_PASSWORD`: Your HamQTH password

**Optional Environment Variables (for Alert Features):**
- `DATABASE_URL`: PostgreSQL connection string (required for alerts)
- `PSKREPORTER_POLL_INTERVAL`: Minutes between spot checks (default: 2)
- `ALERT_EXPIRATION_DAYS`: Days before alerts auto-expire (default: 30)
- `DEFAULT_MODES_PSKREPORTER`: Comma-separated modes to monitor (default: FT8,FT4,PSK31,CW,RTTY)
- `ENABLED_DATA_SOURCES`: Comma-separated sources (default: pskreporter)
- `ALERT_COOLDOWN_MINUTES`: Minutes between alerts for same pattern (default: 5)
- `MAX_ALERTS_PER_USER_PER_HOUR`: Max alerts per user per hour (default: 20)

## Running in Docker

**Using Docker Compose (Recommended):**

1. Copy the environment template:
```bash
cp env.example .env
```

2. Edit `.env` with your configuration values

3. Start the bot:
```bash
docker-compose up -d
```

**Using Docker directly:**

Build and start with:

```bash
docker build -t hambot .
docker run --env-file .env -v $PWD/config:/app/config hambot
```

By default, hambot responds to slash commands (registered globally). It may take a few minutes for new Discord commands to appear.

## Alert System

hambot can monitor digital mode spots (via PSKReporter) and send you DM alerts when specific callsigns or prefixes are spotted. 

**Features:**
- Monitor callsigns or prefixes (e.g., "N4" matches "N4OG", "N4ABC", etc.)
- Support for multiple digital modes (FT8, FT4, PSK31, CW, RTTY, and more)
- Automatic expiration after configurable period
- Rate limiting to prevent spam (per-alert cooldown and per-user limits)
- Direct database integration for reporting

**Setup:**
1. Configure `DATABASE_URL` with a PostgreSQL connection string
2. The bot will automatically create the required database schema on startup
3. Use `/addalert` to create alerts, `/listalerts` to view them, `/removealert` to delete

**Throttling:**
- Each alert has a cooldown period (default: 5 minutes) to prevent duplicate notifications
- Users are limited to a maximum number of alerts per hour (default: 20)
- Discord rate limits are automatically handled

## Example Slash Commands
- `/call <callsign>` - Lookup a callsign
- `/dx <prefix>` - DXCC prefix lookup
- `/muf` - Maximum Usable Frequency chart
- `/cond` - Solar conditions
- `/fof2` - FOF2 propagation chart
- `/utc` - Current UTC time
- `/addalert <callsign> <modes>` - Add a spot alert (e.g., `/addalert N4OG FT8,FT4`)
- `/removealert <id>` - Remove an alert by ID
- `/listalerts` - List your active alerts
- `/about` - Bot information and invite link

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).  
See [LICENSE](LICENSE) for the full legal text.


---
For questions, support, or to report issues, visit: [https://github.com/alekm/hambot/issues]




