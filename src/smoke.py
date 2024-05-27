import os
import string
import discord
import asyncio
import urllib.parse
import random
import constants
import traceback
from datetime import datetime
from config import *
from mediusapi import get_active_games, get_players_online, DEADLOCKED_API_NAME, UYA_API_NAME
from uya_parsers import mapParser, timeParser, gamerulesParser, weaponParserNew

def parse_icon(icon, object):
  if icon["Emoji"] is not None:
    field = icon["Field"]

    # check mask
    if field is not None and "Mask" in icon and (object[field] & icon["Mask"]) == 0:
      return None

    # check equality
    if field is not None and "Value" in icon and object[field] != icon["Value"]:
      return None

    return f'{icon["Emoji"]} \u200B '

  return None

def get_player_region_dl(smoke_config, player):
  app_id = player['AppId']

  # if logged into the NTSC server (dbuser SYSTEM)
  # and player has metadata
  # check if client is logged in from DZO client
  if 'Metadata' in player and player['DatabaseUser'] == 'SYSTEM':
    metadata = json.loads(player['Metadata'])
    if 'LastLoginClientType' in metadata and metadata['LastLoginClientType'] == 1:
      return '[DZO] '
    if 'LastLoginClientType' in metadata and metadata['LastLoginClientType'] == 2:
      return '[EMU] '
    
    return '[PS2] '

  # map app id to respective name
  app_id_key = str(app_id)
  if app_id_key in smoke_config["AppIds"]:
    return f'[{smoke_config["AppIds"][app_id_key]}]'.ljust(6, ' ')

  return None

def get_player_region(smoke_config, app_id):
  app_id_key = str(app_id)
  if app_id_key in smoke_config["AppIds"]:
    return f'[{smoke_config["AppIds"][app_id_key]}]'.ljust(6, ' ')

  return None

def get_game_location(smoke_config, location_id):
  if "Locations" in smoke_config and smoke_config["Locations"] is not None and location_id < len(smoke_config["Locations"]):
    return smoke_config["Locations"][location_id]

  return None

def filter_by_config(smoke_config, game_or_player):
  return str(game_or_player["AppId"]) in smoke_config["AppIds"] and game_or_player["DatabaseUser"] in smoke_config["Servers"]

# creates a discord embed from a twitch stream
def update_embed_DL(smoke_config, players, games, embed: discord.Embed):
  
  # base
  embed.color = int(smoke_config["Color"], 0)
  embed.description = ' '
  embed.title = f'{smoke_config["Name"]} Server'
  embed.timestamp = datetime.now()
  embed.description = '' #f'Players Online - {len(players)}'
  embed.set_thumbnail(url=smoke_config['Thumbnail'])
  embed.clear_fields()
  embed.set_footer(text= 'Last Updated')

  # filter players by appid and server
  players = list(filter(lambda x: filter_by_config(smoke_config, x), players))
  games = list(filter(lambda x: filter_by_config(smoke_config, x), games))

  # description
  if len(players) > 0:
    players.sort(key=lambda x: x["AccountName"])
    names = [f'\n{get_player_region_dl(smoke_config, player)}  {player["AccountName"]}  ' for player in players]
    embed_value = '```'
    for name in names:
      embed_value += name
    embed_value += '```'

    embed.add_field(name= f'Players Online - {len(players)}', value= embed_value, inline= False)

  # games
  embed.add_field(name= '\u200B', value= 'Active Games:', inline= False)

  # active games
  games.sort(key=lambda x: x["GameName"])
  for game in games:
    game_players = list(filter(lambda x: x["GameId"] is not None and x["GameId"] == game["GameId"], players))
    game_active = game["WorldStatus"] == 'WorldActive' or game["WorldStatus"] == 'WorldStaging'
    game_end_scoreboard = game["WorldStatus"] == 'WorldClosed' and len(game_players) > 0
    if game_active or game_end_scoreboard:
      metadata = None
      if game["Metadata"] is not None:
        metadata = json.loads(game["Metadata"])
      in_game = game["WorldStatus"] == 'WorldActive'
      end_game = game["WorldStatus"] == 'WorldClosed'
      has_stats = in_game or end_game
      time_started: datetime = datetime.strptime(game["GameStartDt"][:26], '%Y-%m-%dT%H:%M:%S.%f') if has_stats and game["GameStartDt"] is not None else None
      seconds_since_started: datetime = (datetime.utcnow() - time_started).total_seconds() if time_started is not None else None
      game_players = list(filter(lambda x: x["GameId"] is not None and x["GameId"] == game["GameId"], players))
      location_name = None
      
      if metadata is not None and metadata["Location"] is not None:
        location_name = get_game_location(smoke_config, metadata["Location"])

      embed_name = ''
      embed_value = '\u200B'

      # in game tag
      if in_game:
        embed_name += '[IG] \u200B '
      elif end_game:
        embed_name += '[END] \u200B '
      
      # icons
      for icon in smoke_config["Icons"]:
        icon_value = parse_icon(icon, game)
        if icon_value is not None:
          embed_name += icon_value

      # game name
      embed_name += f'{game["GameName"]} - ({len(game_players)}/10)'

      # location
      if location_name is not None:
        embed_name += f' [{location_name}]'

      # in game timer
      if has_stats and seconds_since_started is not None:
        embed_name += f' @{int(seconds_since_started//3600):02}:{int(seconds_since_started//60)%60:02}:{int(seconds_since_started%60):02}'

      # sub icons
      for icon in smoke_config["SubIcons"]:
        icon_value = parse_icon(icon, game)
        if icon_value is not None:
          embed_value += icon_value
      
      # game mode
      embed_value += '```\n'
      if metadata is not None and metadata["CustomGameMode"] is not None:
        embed_value += metadata["CustomGameMode"] + ' at '
      elif str(game["RuleSet"]) in smoke_config["Rulesets"]:
        embed_value += smoke_config["Rulesets"][str(game["RuleSet"])] + ' at '

      # level
      if metadata is not None and metadata["CustomMap"] is not None:
        embed_value += metadata["CustomMap"]
      elif str(game["GameLevel"]) in smoke_config["Levels"]:
        embed_value += smoke_config["Levels"][str(game["GameLevel"])]
      
      # game info
      if metadata is not None and metadata["GameInfo"] is not None:
        embed_value += "\n" + metadata["GameInfo"]

      embed_value += '\n```\n'
      embed_value += '```\n'
      if metadata is not None and "GameState" in metadata and "Teams" in metadata["GameState"] and metadata["GameState"]["Teams"] is not None:
        teams = metadata["GameState"]["Teams"]
        teams.sort(key= lambda x: x["Score"], reverse= True)
        teams_enabled = metadata["GameState"]["TeamsEnabled"]
        for team in teams:
          score = team["Score"]
          team_players = team["Players"] if team["Players"] is not None else []
          team_players.sort()
          if not teams_enabled and len(team_players) > 0:
            embed_value += f'\n{team_players[0]}{(f" - {score}" if has_stats else "")}'
          else:
            embed_value += f'\n{team["Name"]}{(f" - {score}" if has_stats else "")}'
            for player in team_players:
              embed_value += f'\n  {player}  '
            
      else:
        if len(game_players) > 0:
          names = [x["AccountName"] for x in game_players]
          names.sort()
          names = [f'\n  {x}  ' for x in names]
          for name in names:
            embed_value += name
      embed_value += '```'

      embed.add_field(name= embed_name, value= embed_value, inline= False)
  
  # no games
  if len(games) < 1:
    embed.add_field(name= 'No Games', value= '\u200B', inline= False)
  
  return embed

# creates a discord embed from a twitch stream
def update_embed_UYA(smoke_config, players, games, embed: discord.Embed):
  
  # base
  embed.color = int(smoke_config["Color"], 0)
  embed.title = f'{smoke_config["Name"]} Server'
  embed.timestamp = datetime.now()
  embed.description = '' #f'Players Online - {len(players)}'
  embed.set_thumbnail(url=smoke_config['Thumbnail'])
  embed.clear_fields()
  embed.set_footer(text= 'Last Updated')

  # filter players by appid and server
  players = list(filter(lambda x: filter_by_config(smoke_config, x), players))
  games = list(filter(lambda x: filter_by_config(smoke_config, x), games))
  # description
  if len(players) > 0:
    players_online = [player for player in players if not player["AccountName"].lower().startswith("cpu-")]
    players_online.sort(key=lambda x: x["AccountName"])
    names = [f'\n{get_player_region(smoke_config, player["AppId"])}  {player["AccountName"]}  ' for player in players_online]
    embed_value = '```'
    for name in names:
      embed_value += name
    embed_value += '```'

    embed.add_field(name= f'Players Online - {len(players_online)}', value= embed_value, inline= False)

  # games
  embed.add_field(name= '\u200B', value= 'Active Games:', inline= False)

  # active games
  games.sort(key=lambda x: x["GameName"])
  for game in games:
    if game["WorldStatus"] == 'WorldActive' or game["WorldStatus"] == 'WorldStaging':
      metadata = None
      if game["Metadata"] is not None:
        metadata = json.loads(game["Metadata"])
      in_game = game["WorldStatus"] == 'WorldActive'
      time_started: datetime = datetime.strptime(game["GameStartDt"][:26], '%Y-%m-%dT%H:%M:%S.%f') if in_game and game["GameStartDt"] is not None else None
      seconds_since_started: datetime = (datetime.utcnow() - time_started).total_seconds() if time_started is not None else None
      game_players = list(filter(lambda x: x["GameId"] is not None and x["GameId"] == game["GameId"], players))

      embed_name = ''
      embed_value = '\u200B'

      # in game tag
      if in_game:
        embed_name += '\u200B '
      
      # icons
      for icon in smoke_config["Icons"]:
        icon_value = parse_icon(icon, game)
        if icon_value is not None:
          embed_name += icon_value

      # game name
      game['GameName'] = game['GameName'].strip('000000280000').strip()
      embed_name += f'{game["GameName"]} - ({len(game_players)}/8)'

      # in game timer
      if in_game:
        embed_name += f' @{int(seconds_since_started//3600):02}:{int(seconds_since_started//60)%60:02}:{int(seconds_since_started%60):02}'

      # sub icons
      for icon in smoke_config["SubIcons"]:
        icon_value = parse_icon(icon, game)
        if icon_value is not None:
          embed_value += icon_value

      #print("Game:", game)
      #print("Metadata:", metadata)
      
      # game mode
      embed_value += '```\n'
      # if metadata is not None and metadata["CustomGameMode"] is not None:
      #   embed_value += metadata["CustomGameMode"] + ' at '
      # elif str(game["RuleSet"]) in smoke_config["Rulesets"]:
      #   embed_value += smoke_config["Rulesets"][str(game["RuleSet"])] + ' at '
      game_mode, game_type = gamerulesParser(game['GenericField3'])
      embed_value += f'{game_mode} ({game_type}) at '

      # level
      if metadata is not None and metadata["CustomMap"] is not None:
        embed_value += metadata["CustomMap"]
      else:
        embed_value += mapParser(game['GenericField3'])

      # game info
      timelimit = timeParser(game['GenericField3'])
      embed_value += "\n" + timelimit
      embed_value += '\n' + weaponParserNew(game['PlayerSkillLevel'])

      # if metadata is not None and metadata["GameInfo"] is not None:
      #   embed_value += "\n" + metadata["GameInfo"]

      embed_value += '\n```\n'
      embed_value += '```\n'
      # if metadata is not None and "GameState" in metadata and "Teams" in metadata["GameState"] and metadata["GameState"]["Teams"] is not None:
      #   teams = metadata["GameState"]["Teams"]
      #   teams.sort(key= lambda x: x["Score"], reverse= True)
      #   teams_enabled = metadata["GameState"]["TeamsEnabled"]
      #   for team in teams:
      #     score = team["Score"]
      #     team_players = team["Players"] if team["Players"] is not None else []
      #     team_players.sort()
      #     if not teams_enabled and len(team_players) > 0:
      #       embed_value += f'\n{team_players[0]}{(f" - {score}" if in_game else "")}'
      #     else:
      #       embed_value += f'\n{team["Name"]}{(f" - {score}" if in_game else "")}'
      #       for player in team_players:
      #         embed_value += f'\n  {player}  '
            
      if len(game_players) > 0:
        names = [x["AccountName"] for x in game_players]
        names.sort()
        names = [f'\n  {x}  ' for x in names]
        for name in names:
          embed_value += name
      embed_value += '```'

      embed.add_field(name= embed_name, value= embed_value, inline= False)
  
  # no games
  if len(games) < 1:
    embed.add_field(name= 'No Games', value= '\u200B', inline= False)
  
  return embed

# background task that polls api and creates/updates respective smoke messages in discord
async def smoke_task(client: discord.Client, smoke_config, index):
  await client.wait_until_ready()
  channel: discord.TextChannel = client.get_channel(smoke_config["ChannelId"])
  message: discord.Message = None
  embed: discord.Embed = discord.Embed()
  api = smoke_config["API"]

  # stagger smokes
  await asyncio.sleep(5 * index)

  # try and get message to reuse
  if "MessageId" in smoke_config and smoke_config["MessageId"] > 0:
    message = await channel.fetch_message(smoke_config["MessageId"])

  while not client.is_closed():
    if not client.is_ws_ratelimited():
      try:
        games = get_active_games(api)
        players = get_players_online(api)

        # update embed by game
        if api == DEADLOCKED_API_NAME: embed = update_embed_DL(smoke_config, players, games, embed)
        elif api == UYA_API_NAME: embed = update_embed_UYA(smoke_config, players, games, embed)

        if message is None:
          message = await channel.send(content= None, embed= embed)
        else:
          await message.edit(content= None, embed= embed)

      except Exception as e:
        print(traceback.format_exc())
    await asyncio.sleep(smoke_config["Interval"])

#
def smoke(client):
  i = 0
  smokes = config_get(['Smoke'])
  for smoke in smokes:
    if smoke["Enabled"]:
      client.loop.create_task(smoke_task(client, smoke, i))
      i += 1

