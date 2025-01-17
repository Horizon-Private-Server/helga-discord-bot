import os
import string
import discord
import asyncio
import urllib.parse
import random
import constants
import traceback
from datetime import datetime, timedelta
from config import *
from mediusapi import get_active_games, get_players_online, DEADLOCKED_API_NAME, UYA_API_NAME
from uya_parsers import mapParser, timeParser, gamerulesParser, weaponParserNew

# background task that polls api and creates/updates respective smoke messages in discord
async def uyacomppingertask(client: discord.Client, config):
  await client.wait_until_ready()
  channel: discord.TextChannel = client.get_channel(config["ChannelId"])

  cooldown_2v2 = datetime.now() - timedelta(hours=1)
  cooldown_3v3 = datetime.now() - timedelta(hours=1)
  cooldown_4v4 = datetime.now() - timedelta(hours=1)

  ping_cooldown = config['ping_wait_time_minutes']
  role_id_2v2 = config["2v2_role"]
  role_id_3v3 = config["3v3_role"]
  role_id_4v4 = config["4v4_role"]
  role_channel = config['role_channel']

  with open('uya_comp_playernames.txt', 'r') as f:
    comp_players = f.read()
    comp_players = comp_players.split("\n")
    comp_players = set([player.lower().strip() for player in comp_players if player.lower().strip()])

  while not client.is_closed():
    if not client.is_ws_ratelimited():
      try:
        players = get_players_online("UYA")
        players = comp_players.intersection(set([player['AccountName'].lower().strip() for player in players]))

        if len(players) == 3 and ((datetime.now() - cooldown_2v2).total_seconds() / 60) > ping_cooldown:
          help_msg = f'<@&{role_id_2v2}>, theres 3 online! need 1 for 2v2!\n (to get tagged in future pings, add yourself in <#{role_channel}>)'
          await channel.send(help_msg)
          cooldown_2v2 = datetime.now()
        elif len(players) == 5 and ((datetime.now() - cooldown_3v3).total_seconds() / 60) > ping_cooldown:
          help_msg = f'<@&{role_id_3v3}>, theres 5 online! need 1 for 3v3!\n (to get tagged in future pings, add yourself in <#{role_channel}>)'
          await channel.send(help_msg)
          cooldown_3v3 = datetime.now()
        elif len(players) == 7 and ((datetime.now() - cooldown_4v4).total_seconds() / 60) > ping_cooldown:
          help_msg = f'<@&{role_id_4v4}>, theres 7 online! need 1 for 4v4!\n (to get tagged in future pings, add yourself in <#{role_channel}>)'
          await channel.send(help_msg)
          cooldown_4v4 = datetime.now()

      except Exception as e:
        print(traceback.format_exc())
    await asyncio.sleep(config["Interval"])

#
def uyacomppinger(client):
  config = config_get(['UyaCompOnlinePinger'])
  client.loop.create_task(uyacomppingertask(client, config))


