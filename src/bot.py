# bot.py
import os
import discord
from discord.commands import Option, SlashCommandGroup
from dotenv import load_dotenv

from streamfeed import streamfeed
from stats import get_dl_stats, DEADLOCKED_GET_STATS_CHOICES

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Bot()
stats = SlashCommandGroup("stats", "Commands related to game stats.")

@client.event
async def on_ready():
  print(f'{client.user} has connected to Discord!')

@stats.command(name="deadlocked", description="Query an account's stats.")
async def cmd_stats(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat category", choices=list(DEADLOCKED_GET_STATS_CHOICES.keys())),
  name: Option(str, "Enter the username")
  ):
  await get_dl_stats(ctx, stat, name)

streamfeed(client)
client.add_application_command(stats)
client.run(TOKEN)
