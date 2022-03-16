# hambot
hambot (hb) is a Discord bot based on thisguyistotallben/hamtheman for various amateur radio related lookups, including callsigns (globally with HamQTH), solar conditions, Maximum Usable Frequencies, time, and a morse code translator.

# Getting started
This bot is designed to run in a docker container.

## API Keys
You will first need an API Key for your bot from discord (https://discordapp.com/developers/applications/) and a HamQTH aaccount (https://hamqth.com)

You can then copy config_default.json to config.json and edit the required parameters with your API and account information.  Your discord user-id will be a number, not your username.  You can search on how to find this using discord developer mode.

## Running in docker
Build the docker container using the included Dockerfile (ex. docker build -t hambot .)
Once built, the container can be executed from docker or docker-compose

By default, the bot answers to the keyword "hb" (ex. "hb help").

Only Bot -> Send Messages is required for the bot to operate in a Discord Server
