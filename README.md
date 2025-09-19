# hambot

hambot (hb) is a Discord bot for amateur radio lookups: callsigns (globally with HamQTH), solar conditions, Maximum Usable Frequencies, UTC/time, and more. Adapted from thisguyistotallben/hamtheman.

## Features
- Global callsign lookups (HamQTH)
- Solar weather/maps
- MUF charts
- UTC/time tools

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

## Example Slash Commands
- `/call <callsign>`
- `/dx <prefix>`
- `/muf`
- `/cond`
- `/fof2`
- `/utc`

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).  
See [LICENSE](LICENSE) for the full legal text.


---
For questions, support, or to report issues, visit: [https://github.com/alekm/hambot/issues]




