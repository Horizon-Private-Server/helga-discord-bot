# bot.py
import os
import discord
from dotenv import load_dotenv

from streamfeed import streamfeed

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

streamfeed(client)
client.run(TOKEN)
