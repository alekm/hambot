# hambot

hambot (hb) is a Discord bot for amateur radio lookups: callsigns (globally with HamQTH), solar conditions, Maximum Usable Frequencies, UTC/time, and a morse code translator. Adapted from thisguyistotallben/hamtheman.

## Features
- Global callsign lookups (HamQTH)
- Solar weather/maps
- MUF charts
- UTC/time tools
- Morse code helper

## Getting Started

You’ll need:
- A Discord bot [developer token](https://discordapp.com/developers/applications/)
- A [HamQTH account](https://hamqth.com)

**Setup:**
1. Copy the sample config and edit your details:
        
```cp config/config.json.example config/config.json```

2. Edit your Discord bot token, Discord user id (numeric), and HamQTH credentials into `config.json`.

## Running in Docker

Build and start with:

```docker build -t hambot .
docker run -v $PWD/config:/app/config hambot```


By default, hambot responds to slash commands (registered globally). It may take a few minutes for new Discord commands to appear.

## Example Slash Commands
- `/call <callsign>`
- `/dx <prefix>`
- `/cond`
- `/fof2`
- `/utc`

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).  
See [LICENSE](LICENSE) for the full legal text.


---
For questions, support, or to report issues, visit: [https://github.com/alekm/hambot/issues]




