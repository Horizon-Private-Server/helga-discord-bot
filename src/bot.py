# bot.py
import os
import discord
from discord.commands import Option, SlashCommandGroup
from dotenv import load_dotenv

from config import *
from smoke import smoke
from streamfeed import streamfeed
from stats import get_dl_stats, get_dl_leaderboard, DEADLOCKED_GET_STATS_CHOICES, DEADLOCKED_STATS
from skins import get_dl_skins, get_uya_skins
from youtubefeed import youtubefeed

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

config_load()

client = discord.Bot()
#deadlocked = SlashCommandGroup("deadlocked", "Commands related to deadlocked.", guild_ids=['918360025829900298'])
#uya = SlashCommandGroup("uya", "Commands related to Up Your Arsenal.", guild_ids=['918360025829900298'])
#leaderboard = deadlocked.create_subgroup("leaderboard", "Commands related to game leaderboards.")

# create Slash Command group with bot.create_group
deadlocked = client.create_group("deadlocked", "Commands related to deadlocked.")
leaderboard = deadlocked.create_subgroup("leaderboard", "Commands related to game leaderboards.")
uya = client.create_group("uya", "Commands related to UYA.")

@client.event
async def on_ready():
  print(f'{client.user} has connected to Discord!')


@uya.command(name="skins", description="Generate UYA multiplayer skins.")
async def cmd_stats(
  ctx: discord.ApplicationContext,
  name: Option(str, "Enter the username")
  ):
  await get_uya_skins(ctx, name)



@deadlocked.command(name="skins", description="Generate DL multiplayer skins.")
async def cmd_stats(
  ctx: discord.ApplicationContext,
  name: Option(str, "Enter the username")
  ):
  await get_dl_skins(ctx, name)

@deadlocked.command(name="stats", description="Query an account's stats.")
async def cmd_stats(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat category", choices=list(DEADLOCKED_GET_STATS_CHOICES.keys())),
  name: Option(str, "Enter the username")
  ):
  await get_dl_stats(ctx, stat, name)

@leaderboard.command(name="climber", description="See the Top 5 in any Infinite Climber stat.")
async def cmd_climber_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Infinite Climber"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Infinite Climber", stat)

@leaderboard.command(name="ctf", description="See the Top 5 in any CTF stat.")
async def cmd_ctf_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Capture the Flag"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Capture the Flag", stat)

@leaderboard.command(name="cq", description="See the Top 5 in any Conquest stat.")
async def cmd_cq_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Conquest"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Conquest", stat)

@leaderboard.command(name="dm", description="See the Top 5 in any Deathmatch stat.")
async def cmd_dm_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Deathmatch"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Deathmatch", stat)

@leaderboard.command(name="gungame", description="See the Top 5 in any Gun Game stat.")
async def cmd_gungame_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Gun Game"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Gun Game", stat)

@leaderboard.command(name="infected", description="See the Top 5 in any Infected stat.")
async def cmd_infected_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Infected"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Infected", stat)

@leaderboard.command(name="juggernaut", description="See the Top 5 in any Juggernaut stat.")
async def cmd_juggernaut_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Juggernaut"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Juggernaut", stat)

@leaderboard.command(name="koth", description="See the Top 5 in any King of the Hill stat.")
async def cmd_koth_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["King of the Hill"].keys()))
  ):
  await get_dl_leaderboard(ctx, "King of the Hill", stat)

@leaderboard.command(name="overall", description="See the Top 5 in any Overall stat.")
async def cmd_overall_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Overall"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Overall", stat)

@leaderboard.command(name="payload", description="See the Top 5 in any Payload stat.")
async def cmd_payload_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Payload"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Payload", stat)

@leaderboard.command(name="snd", description="See the Top 5 in any Search and Destroy stat.")
async def cmd_snd_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Search and Destroy"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Search and Destroy", stat)

@leaderboard.command(name="spleef", description="See the Top 5 in any Spleef stat.")
async def cmd_spleef_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Spleef"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Spleef", stat)

@leaderboard.command(name="survival", description="See the Top 5 in any Survival stat.")
async def cmd_survival_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Survival"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Survival", stat)

@leaderboard.command(name="weapons", description="See the Top 5 in any Weapon stat.")
async def cmd_weapon_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Weapons"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Weapons", stat)

streamfeed(client)
youtubefeed(client)
smoke(client)
# client.remove_application_command(deadlocked)
# client.add_application_command(deadlocked)
# client.remove_application_command(uya)
# client.add_application_command(uya)
client.run(TOKEN)
