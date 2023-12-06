
import os
import discord
import requests
import random
import json
import datetime
import dateutil
import traceback
import constants
import urllib3
from discord.ext import commands
from mediusapi import *

#
def get_leaderboard_top(api, app_id, stat_id, count, custom = False):
  global headers
  if api not in headers:
    authenticate(api)
  
  optional_custom = 'Custom' if custom else ''

  route =  f"Stats/getLeaderboard{optional_custom}?{optional_custom}StatId={stat_id}&StartIndex={0}&Size={count}&AppId={app_id}"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

def get_discord_string_from_date(datetime: datetime.datetime):
  if datetime is None:
    return 'None'
  # return datetime.strftime('%B %d, %Y %H:%M:%S %Z')
  return f'<t:{round(datetime.timestamp())}:F>'

def get_string_from_date(datetime: datetime.datetime):
  return datetime.strftime('%Y-%m-%dT%H:%M:%S.%f Z')

def get_date_from_string(datetime_str: str):
  if datetime_str is None:
    return None
  
  return dateutil.parser.parse(datetime_str)

def get_account_name_from_api(api: str):
  if api == DEADLOCKED_API_NAME:
    return DEADLOCKED_ACC_NAME
  elif api == UYA_API_NAME:
    return UYA_ACC_NAME
  
  return None

def get_api_from_game_name(game: str):
  if game.lower() == 'deadlocked':
    return DEADLOCKED_API_NAME
  elif game.lower() == 'uya':
    return UYA_API_NAME
  
  return None

def get_appids_from_game_name(game: str):
  if game.lower() == 'deadlocked':
    return [ APPID_DEADLOCKED ]
  elif game.lower() == 'uya':
    return [ APPID_RC3, APPID_UYA ]
  
  return None

def get_scavenger_hunt_dates(api: str, appid: int):
  settings = get_settings(api, appid)
  acc_name = get_account_name_from_api(api)
  
  begin_date = get_date_from_string(settings[f'{acc_name}_ScavengerHuntBeginDate'])
  end_date = get_date_from_string(settings[f'{acc_name}_ScavengerHuntEndDate'])

  return (begin_date, end_date)

def get_scavenger_hunt_settings_embed(game: str, begin_date: datetime.datetime, end_date: datetime.datetime, spawn_factor: float):
  embed = discord.Embed()
  embed.add_field(name='Begin Date', value=get_discord_string_from_date(begin_date), inline=False)
  embed.add_field(name='End Date', value=get_discord_string_from_date(end_date), inline=False)
  embed.add_field(name='Spawn Rate', value=str(spawn_factor), inline=False)
  embed.title = f'{game} Scavenger Hunt Settings'
  return embed

#
def set_scavenger_hunt_settings(game: str, settings):

  api_name = get_api_from_game_name(game)
  appids = get_appids_from_game_name(game)
  acc_name = get_account_name_from_api(api_name)

  # set
  for appid in appids:
    set_settings(api_name, appid, settings)
  
  # get
  settings = get_settings(api_name, appids[0])
  begin_date = get_date_from_string(settings[f'{acc_name}_ScavengerHuntBeginDate'])
  end_date = get_date_from_string(settings[f'{acc_name}_ScavengerHuntEndDate'])
  spawn_factor = settings[f'{acc_name}_ScavengerHuntSpawnRateFactor']
  return get_scavenger_hunt_settings_embed(game, begin_date, end_date, spawn_factor)

#
def append_leaderboard_embed(embed: discord.Embed, leaderboard):
  
  lb_str = ''
  pad_str = ' '
  transform_value = lambda x : x
  count = len(leaderboard)

  for i in range(0, count):
    s = f'{i+1}. {leaderboard[i]["AccountName"]}'
    while len(s) < 24:
      s += pad_str
    lb_str += f'{s}{transform_value(leaderboard[i]["StatValue"])}\n'

  embed.add_field(name= f'Top {count}', value=f'```\n{lb_str}```', inline=True)
  return embed

#
async def print_scavenger_hunt(ctx: discord.ApplicationContext, game: str):
  try:
    api_name = get_api_from_game_name(game)
    appids = get_appids_from_game_name(game)
    acc_name = get_account_name_from_api(api_name)
    settings = get_settings(api_name, appids[0])
    begin_date = get_date_from_string(settings[f'{acc_name}_ScavengerHuntBeginDate'])
    end_date = get_date_from_string(settings[f'{acc_name}_ScavengerHuntEndDate'])
    spawn_factor = settings[f'{acc_name}_ScavengerHuntSpawnRateFactor']
    leaderboard = get_leaderboard_top(api_name, appids[0], constants.CUSTOM_STAT_CURRENT_HORIZON_BOLTS+1, 10, custom=True)

    embed = get_scavenger_hunt_settings_embed(game, begin_date, end_date, spawn_factor)
    append_leaderboard_embed(embed, leaderboard)
    await ctx.respond('', embed=embed)
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Error.')

#
async def set_spawn_rate_scavenger_hunt(ctx: discord.ApplicationContext, game: str, spawn_rate: float):
  try:
    api_name = get_api_from_game_name(game)
    acc_name = get_account_name_from_api(api_name)
    embed = set_scavenger_hunt_settings(game, {
      f'{acc_name}_ScavengerHuntSpawnRateFactor': str(spawn_rate),
    })
    await ctx.respond('', embed=embed)
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Error.')
  
#
async def kill_scavenger_hunt(ctx: discord.ApplicationContext, game: str):
  try:
    api_name = get_api_from_game_name(game)
    acc_name = get_account_name_from_api(api_name)
    embed = set_scavenger_hunt_settings(game, {
      f'{acc_name}_ScavengerHuntBeginDate': None,
      f'{acc_name}_ScavengerHuntEndDate': None,
      f'{acc_name}_ScavengerHuntSpawnRateFactor': str(1.0)
    })
    await ctx.respond('', embed=embed)
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Error.')
  
#
async def activate_scavenger_hunt(ctx: discord.ApplicationContext, game: str, delayMinutes: float, durationHours: float):
  try:
    api_name = get_api_from_game_name(game)
    acc_name = get_account_name_from_api(api_name)
    now = datetime.datetime.utcnow()
    begin = now + datetime.timedelta(minutes = delayMinutes)
    end = begin + datetime.timedelta(hours = durationHours)

    embed = set_scavenger_hunt_settings(game, {
      f'{acc_name}_ScavengerHuntBeginDate': get_string_from_date(begin),
      f'{acc_name}_ScavengerHuntEndDate': get_string_from_date(end),
    })
    await ctx.respond('', embed=embed)
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Error.')
  
#
async def set_spawn_rate_scavenger_hunt(ctx: discord.ApplicationContext, game: str, spawnRate: float):
  try:
    api_name = get_api_from_game_name(game)
    acc_name = get_account_name_from_api(api_name)
    embed = set_scavenger_hunt_settings(game, {
      f'{acc_name}_ScavengerHuntSpawnRateFactor': str(spawnRate),
    })
    await ctx.respond('', embed=embed)
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Error.')
  
#
async def reset_leaderboard_scavenger_hunt(ctx: discord.ApplicationContext, game: str):
  try:
    api_name = get_api_from_game_name(game)
    appids = get_appids_from_game_name(game)

    # set
    for appid in appids:
      reset_custom_leaderboard(api_name, appid, 2)
    await ctx.respond(f'{game} scavenger hunt leaderboard reset')
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Error.')
  