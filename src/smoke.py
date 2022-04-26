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
from mediusapi import get_active_games, get_players_online

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

# creates a discord embed from a twitch stream
def update_embed(smoke_config, players, games, embed: discord.Embed):
  
  # base
  embed.color = int(smoke_config["Color"], 0)
  embed.description = ' '
  embed.title = f'Players Online - {len(players)}'
  embed.timestamp = datetime.now()
  embed.set_thumbnail(url=smoke_config['Thumbnail'])
  embed.clear_fields()
  embed.set_footer(text= 'Last Updated')

  # description
  if len(players) > 0:
    names = [x["AccountName"] for x in players]
    names.sort()
    names = [f'\n  {x}  ' for x in names]
    embed.description = '```'
    for name in names:
      embed.description += name
    embed.description += '```'

  # games
  embed.add_field(name= '\u200B', value= 'Active Games:', inline= False)

  # active games
  games.sort(key=lambda x: x["GameName"])
  for game in games:
    if game["WorldStatus"] == 'WorldActive' or game["WorldStatus"] == 'WorldStaging':
      metadata = json.loads(game["Metadata"])
      in_game = game["WorldStatus"] == 'WorldActive'
      time_started: datetime = datetime.strptime(game["GameStartDt"][:26], '%Y-%m-%dT%H:%M:%S.%f') if in_game and game["GameStartDt"] is not None else None
      seconds_since_started: datetime = (datetime.utcnow() - time_started).total_seconds() if time_started is not None else None
      game_players = list(filter(lambda x: x["GameId"] is not None and x["GameId"] == game["GameId"], players))

      embed_name = ''
      embed_value = '\u200B'

      # in game tag
      if in_game:
        embed_name += '[IG] \u200B '
      
      # icons
      for icon in smoke_config["Icons"]:
        icon_value = parse_icon(icon, game)
        if icon_value is not None:
          embed_name += icon_value

      # game name
      embed_name += f'{game["GameName"]} - ({len(game_players)}/10)'

      # in game timer
      if in_game:
        embed_name += f' @{int(seconds_since_started//3600):02}:{int(seconds_since_started//60)%60:02}:{int(seconds_since_started%60):02}'

      # sub icons
      for icon in smoke_config["SubIcons"]:
        icon_value = parse_icon(icon, game)
        if icon_value is not None:
          embed_value += icon_value
      
      # game mode
      embed_value += '```\n'
      if metadata["CustomGameMode"] is not None:
        embed_value += metadata["CustomGameMode"] + ' at '
      elif str(game["RuleSet"]) in smoke_config["Rulesets"]:
        embed_value += smoke_config["Rulesets"][str(game["RuleSet"])] + ' at '

      # level
      if metadata["CustomMap"] is not None:
        embed_value += metadata["CustomMap"]
      elif str(game["GameLevel"]) in smoke_config["Levels"]:
        embed_value += smoke_config["Levels"][str(game["GameLevel"])]
      
      # game info
      if metadata["GameInfo"] is not None:
        embed_value += "\n" + metadata["GameInfo"]

      embed_value += '\n```\n'
      embed_value += '```\n'
      if "GameState" in metadata and "Teams" in metadata["GameState"] and metadata["GameState"]["Teams"] is not None:
        teams = metadata["GameState"]["Teams"]
        teams.sort(key= lambda x: x["Score"], reverse= True)
        teams_enabled = metadata["GameState"]["TeamsEnabled"]
        for team in teams:
          score = team["Score"]
          team_players = team["Players"] if team["Players"] is not None else []
          team_players.sort()
          if not teams_enabled and len(team_players) > 0:
            embed_value += f'\n{team_players[0]}{(f" - {score}" if in_game else "")}'
          else:
            embed_value += f'\n{team["Name"]}{(f" - {score}" if in_game else "")}'
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

# background task that polls api and creates/updates respective smoke messages in discord
async def smoke_task(client: discord.Client, smoke_config):
  await client.wait_until_ready()
  channel: discord.TextChannel = client.get_channel(smoke_config["ChannelId"])
  message: discord.Message = None
  embed: discord.Embed = discord.Embed()

  # try and get message to reuse
  if "MessageId" in smoke_config and smoke_config["MessageId"] > 0:
    message = await channel.fetch_message(smoke_config["MessageId"])

  while not client.is_closed():
    if not client.is_ws_ratelimited():
      try:
        games = get_active_games()
        players = get_players_online()
        embed = update_embed(smoke_config, players, games, embed)
        if message is None:
          message = await channel.send(content= None, embed= embed)
        else:
          await message.edit(content= None, embed= embed)

      except Exception as e:
        print(traceback.format_exc())
    await asyncio.sleep(smoke_config["Interval"])

#
def smoke(client):
  smokes = config_get(['Smoke'])
  for smoke in smokes:
    if smoke["Enabled"]:
      client.loop.create_task(smoke_task(client, smoke))

