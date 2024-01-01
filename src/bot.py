# bot.py
import os
import discord
import traceback
from discord.commands import Option, SlashCommandGroup

from dotenv import load_dotenv

from scavengerhunt import activate_scavenger_hunt, print_scavenger_hunt, reset_leaderboard_scavenger_hunt, kill_scavenger_hunt, set_spawn_rate_scavenger_hunt
from config import *
from smoke import smoke
from tipoftheday import tipoftheday
from streamfeed import streamfeed
from stats import get_dl_stats, get_dl_leaderboard, get_dl_scavenger_hunt_leaderboard, get_uya_scavenger_hunt_leaderboard, DEADLOCKED_GET_STATS_CHOICES, DEADLOCKED_STATS
from skins import get_dl_skins, get_uya_skins
from youtubefeed import youtubefeed
#from uya import *

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

config_load()

intents = discord.Intents.default()
intents.members = True
intents.reactions = True

client = discord.Bot(intents=intents)

# create Slash Command group with bot.create_group
deadlocked = client.create_group("deadlocked", "Commands related to deadlocked.", guild_ids=config_get(['Stats', 'GuildIds']))
dl_leaderboard = client.create_group("deadlocked-leaderboard", "Commands related to game leaderboards.", guild_ids=config_get(['Stats', 'GuildIds']))
dl_custom_leaderboard = client.create_group("deadlocked-custom-leaderboard", "Commands related to custom game leaderboards.", guild_ids=config_get(['Stats', 'GuildIds']))
uya = client.create_group("uya", "Commands related to UYA.", guild_ids=config_get(['Stats', 'GuildIds']))
scavenger_hunt = client.create_group("scavenger-hunt", "Commands for Horizon staff.", guild_ids=config_get(['Stats', 'GuildIds']))
mod = client.create_group("mod", "Commands for Horizon staff.", guild_ids=config_get(['Stats', 'GuildIds']))

#uya_manager = UYAManager(client, config_get_full())

@client.event
async def on_ready():
  print(f'{client.user} has connected to Discord!')

@client.event
async def on_raw_reaction_add(payload):
  user_id = payload.user_id
  message_id = payload.message_id
  emoji = payload.emoji

  # print("user:",user_id)
  # print("message:",message_id)
  # print("emoji:",emoji)
  # print("emoji_id:",emoji.id)

  if message_id != config_get(["ReactionRoles", "MessageId"]):
    return

  user = get(client.get_all_members(), id=user_id)
  if not user:
    return # no user found

  for emoji_id, role_id in config_get(["ReactionRoles", "EmojisToRoles"]).items():
    if emoji_id == str(emoji):
      # Add the role
      await user.add_roles(user.guild.get_role(int(role_id)))

@client.event
async def on_raw_reaction_remove(payload):
  user_id = payload.user_id
  message_id = payload.message_id
  emoji = payload.emoji

  # print("user:",user_id)
  # print("message:",message_id)
  # print("emoji:",emoji)
  # print("emoji_id:",emoji.id)

  if message_id != config_get(["ReactionRoles", "MessageId"]):
    return

  user = get(client.get_all_members(), id=user_id)
  if not user:
    return # no user found

  for emoji_id, role_id in config_get(["ReactionRoles", "EmojisToRoles"]).items():
    if emoji_id == str(emoji):
      # Add the role
      await user.remove_roles(user.guild.get_role(int(role_id)))

@client.event
async def on_raw_reaction_clear(payload):
  user_id = payload.user_id
  message_id = payload.message_id
  emoji = payload.emoji

  # print("user:",user_id)
  # print("message:",message_id)
  # print("emoji:",emoji)
  # print("emoji_id:",emoji.id)

  if message_id != config_get(["ReactionRoles", "MessageId"]):
    return

  user = get(client.get_all_members(), id=user_id)
  if not user:
    return # no user found

  for emoji_id, role_id in config_get(["ReactionRoles", "EmojisToRoles"]).items():
    if emoji_id == str(emoji):
      # Add the role
      await user.remove_roles(user.guild.get_role(int(role_id)))

@uya.command(name="skins", description="Generate UYA multiplayer skins.")
async def cmd_stats(
  ctx: discord.ApplicationContext,
  name: Option(str, "Enter the username")
  ):
  await get_uya_skins(ctx, name)

@uya.command(name="scavenger-hunt", description="See the current scavenger hunt leaderboard.")
async def cmd_stats(
  ctx: discord.ApplicationContext
  ):
  await get_uya_scavenger_hunt_leaderboard(ctx)

# @uya.command(name='alt', description="Find accounts tied to this account.")
# async def cmd_stats(
#   ctx: discord.ApplicationContext,
#   name: Option(str, "Enter the username")
#   ):
#   await uya_manager.alt(ctx, name)


# @uya.command(name='clan', description="Get Clan info from a clan name.")
# async def cmd_stats(
#   ctx: discord.ApplicationContext,
#   name: Option(str, "Enter the Clan name")
#   ):
#   await uya_manager.clan(ctx, name)


@scavenger_hunt.command(name="reset", description="Resets the current scavenger hunt leaderboard.")
async def cmd_admin_print_scavenger_hunt(
  ctx: discord.ApplicationContext,
  game: Option(str, "Choose a game", choices=["Deadlocked", "UYA"])
  ):
  await reset_leaderboard_scavenger_hunt(ctx, game)

@scavenger_hunt.command(name="print", description="Prints the current scavenger hunt settings.")
async def cmd_admin_print_scavenger_hunt(
  ctx: discord.ApplicationContext,
  game: Option(str, "Choose a game", choices=["Deadlocked", "UYA"])
  ):
  await print_scavenger_hunt(ctx, game)

@scavenger_hunt.command(name="spawn-rate", description="Configure scavenger hunt spawn rate.")
async def cmd_admin_activate_scavenger_hunt(
  ctx: discord.ApplicationContext,
  game: Option(str, "Choose a game", choices=["Deadlocked", "UYA"]),
  spawn_rate: Option(float, "Increases the frequency of bolt spawns. Default is 1.")
  ):
  await set_spawn_rate_scavenger_hunt(ctx, game, spawn_rate)

@scavenger_hunt.command(name="activate", description="Configure scavenger hunt settings.")
async def cmd_admin_activate_scavenger_hunt(
  ctx: discord.ApplicationContext,
  game: Option(str, "Choose a game", choices=["Deadlocked", "UYA"]),
  delay: Option(float, "Begin the hunt n minutes from now"),
  duration: Option(float, "How many hours the scavenger hunt should last")
  ):
  await activate_scavenger_hunt(ctx, game, delay, duration)

@scavenger_hunt.command(name="kill", description="Immediately ends the current scavenger hunt.")
async def cmd_admin_abort_scavenger_hunt(
  ctx: discord.ApplicationContext,
  game: Option(str, "Choose a game", choices=["Deadlocked", "UYA"])
  ):
  await kill_scavenger_hunt(ctx, game)

#
#
#

@mod.command(name="find-matching-nicknames", description="Searches list of users in the discord and reports any that have a matching name.")
async def cmd_admin_find_matching_nicknames(
  ctx: discord.ApplicationContext
  ):
  try:
    await ctx.respond(f'Processing request... this may take awhile...')
    lines = 'Results:\n'
    members = []
    async for memberA in ctx.guild.fetch_members():
      for memberB in members:
        if memberA.id == memberB.id: continue

        if memberA.display_name is not None and (memberA.display_name == memberB.display_name or memberA.display_name == memberB.nick):
          lines += f'<@{memberA.id}> & <@{memberB.id}> match nickname/name "{memberA.display_name}"' + '\n'
        elif memberA.nick is not None and (memberA.nick == memberB.nick or memberA.nick == memberB.display_name):
          lines += f'<@{memberA.id}> & <@{memberB.id}> match nickname/name "{memberA.nick}"' + '\n'

      members.append(memberA)

    await ctx.channel.send(lines)
    #await ctx.respond(lines)
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Error.')

#
#
#
  
@deadlocked.command(name="scavenger-hunt", description="See the current scavenger hunt leaderboard.")
async def cmd_stats(
  ctx: discord.ApplicationContext
  ):
  await get_dl_scavenger_hunt_leaderboard(ctx)

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

@dl_leaderboard.command(name="climber", description="See the Top 5 in any Infinite Climber stat.")
async def cmd_climber_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Infinite Climber"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Infinite Climber", stat)

@dl_leaderboard.command(name="ctf", description="See the Top 5 in any CTF stat.")
async def cmd_ctf_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Capture the Flag"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Capture the Flag", stat)

@dl_leaderboard.command(name="cq", description="See the Top 5 in any Conquest stat.")
async def cmd_cq_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Conquest"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Conquest", stat)

@dl_leaderboard.command(name="dm", description="See the Top 5 in any Deathmatch stat.")
async def cmd_dm_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Deathmatch"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Deathmatch", stat)

@dl_custom_leaderboard.command(name="gungame", description="See the Top 5 in any Gun Game stat.")
async def cmd_gungame_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Gun Game"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Gun Game", stat)

@dl_custom_leaderboard.command(name="infected", description="See the Top 5 in any Infected stat.")
async def cmd_infected_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Infected"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Infected", stat)

@dl_custom_leaderboard.command(name="juggernaut", description="See the Top 5 in any Juggernaut stat.")
async def cmd_juggernaut_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Juggernaut"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Juggernaut", stat)

@dl_custom_leaderboard.command(name="koth", description="See the Top 5 in any King of the Hill stat.")
async def cmd_koth_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["King of the Hill"].keys()))
  ):
  await get_dl_leaderboard(ctx, "King of the Hill", stat)

@dl_leaderboard.command(name="overall", description="See the Top 5 in any Overall stat.")
async def cmd_overall_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Overall"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Overall", stat)

@dl_custom_leaderboard.command(name="payload", description="See the Top 5 in any Payload stat.")
async def cmd_payload_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Payload"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Payload", stat)

@dl_custom_leaderboard.command(name="snd", description="See the Top 5 in any Search and Destroy stat.")
async def cmd_snd_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Search and Destroy"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Search and Destroy", stat)

@dl_custom_leaderboard.command(name="spleef", description="See the Top 5 in any Spleef stat.")
async def cmd_spleef_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Spleef"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Spleef", stat)

@dl_custom_leaderboard.command(name="survival", description="See the Top 5 in any Survival stat.")
async def cmd_survival_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Survival"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Survival", stat)

@dl_custom_leaderboard.command(name="training", description="See the Top 5 in any Training stat.")
async def cmd_training_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Training"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Training", stat)

@dl_leaderboard.command(name="weapons", description="See the Top 5 in any Weapon stat.")
async def cmd_weapon_leaderboard(
  ctx: discord.ApplicationContext,
  stat: Option(str, "Choose a stat", choices=list(DEADLOCKED_STATS["Weapons"].keys()))
  ):
  await get_dl_leaderboard(ctx, "Weapons", stat)

tipoftheday(client)
streamfeed(client)
youtubefeed(client)
smoke(client)
client.run(TOKEN)
