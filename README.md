# hambot
hambot (hb) is a Discord bot based on thisguyistotallben/hamtheman for various amateur radio related lookups, including callsigns (globally with HamQTH), solar conditions, Maximum Usable Frequencies, D-Region Absorption Predictions (d-rap) and Frequency of F2 Layer (foF2)

# Getting started
This bot is designed to run in a docker container.

## API Keys
You will first need an API Key for your bot from discord (https://discordapp.com/developers/applications/) and a HamQTH aaccount (https://hamqth.com)

You can then copy config_default.json to /config/config.json and edit the required parameters with your API and account information.  Your discord user-id will be a number, not your username.  You can search on how to find this using discord developer mode.

## Running in docker
Build the docker container using the included Dockerfile (ex. "docker build -t hambot .")
Once built, the container can be executed from docker or docker-compose

By default, the bot answers to slash commands, which will be registered globaly automatically.

## Usage

Use the /help and /about commands once added to your server to see available options.


Add me to your server! https://discordapp.com/oauth2/authorize?client_id=947361185878147082&scope=bot&permissions=67488832
