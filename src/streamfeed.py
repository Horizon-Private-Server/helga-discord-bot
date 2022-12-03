from glob import glob
import os
import string
import discord
import asyncio
import urllib.parse
import random
import constants
import traceback
from datetime import datetime
from twitchAPI.twitch import Twitch
from pprint import pprint
from dotenv import load_dotenv

load_dotenv()
TWITCH_APPKEY = os.getenv('TWITCH_APPKEY')
TWITCH_SECRET = os.getenv('TWITCH_SECRET')
STREAMFEED_CHANNEL_ID = os.getenv('STREAMFEED_CHANNEL_ID')
STREAMFEED_POLL_DELAY = int(os.getenv('STREAMFEED_POLL_DELAY'))
STREAMFEED_UPDATE_EXISTING_DELAY = int(os.getenv('STREAMFEED_UPDATE_EXISTING_DELAY'))

SupportedGames = [
  "Ratchet: Deadlocked",
  "Ratchet and Clank: Up Your Arsenal",
]

GameColors = {
  "Ratchet: Deadlocked": 0xFF0000,
  "Ratchet and Clank: Up Your Arsenal": 0xFFFF00
}

TitleWhitelistFilters = [
  "online"
]

# initialize twitch and get list of games
twitch: Twitch = None
try:
  twitch = Twitch(TWITCH_APPKEY, TWITCH_SECRET)
  games = twitch.get_games(names= SupportedGames)
except:
  print('unable to authenticate with twitch')
  pass

# whether or not a given stream matches the filter
def is_match(stream):
  title = stream["title"].lower()
  for filter in TitleWhitelistFilters:
    if filter in title:
      return True

  return False

# creates a discord embed from a twitch stream
def update_embed(stream, embed: discord.Embed, peak_viewer_count = 0):
  if stream is not None:
    thumbnail: string = stream["thumbnail_url"].replace("{width}", "360").replace("{height}", "240") + f'?v={random.randrange(10000000)}'

    if stream["game_name"] in GameColors:
      embed.color = GameColors[stream["game_name"]]
    else:
      embed.color = 0xFFFF00
    embed.description = stream["title"]
    embed.url = f'https://twitch.tv/{stream["user_name"]}'
    embed.timestamp = datetime.now()
    embed.set_author(name= f'{stream["user_name"]} is now streaming [{stream["language"].upper()}]', url= f'https://twitch.tv/{stream["user_name"]}', icon_url= f'https://avatar.glue-bot.xyz/twitch/{urllib.parse.quote(stream["user_name"])}')
    embed.set_thumbnail(url= f'https://avatar.glue-bot.xyz/twitch-boxart/{urllib.parse.quote(stream["game_name"])}')
    embed.set_image(url=thumbnail)
    embed.clear_fields()
    embed.add_field(name= ':joystick: Game', value= f'{stream["game_name"]}', inline= True)
    embed.add_field(name= ':busts_in_silhouette: Viewers', value= f'{stream["viewer_count"]}', inline= True)
    embed.set_footer(text= 'Live')
  else:
    embed.set_field_at(index= 1, name= ':busts_in_silhouette: Peak Viewers', value= f'{peak_viewer_count}', inline= True)
    embed.set_footer(text= 'Offline')

  return embed

# background task that polls twitch and creates/updates stream messages in discord
async def streamfeed_task(client: discord.Client):
  await client.wait_until_ready()

  if STREAMFEED_CHANNEL_ID is None:
    return

  channel: discord.TextChannel = client.get_channel(int(STREAMFEED_CHANNEL_ID))
  live_channels = {}
  update_ticker = 0

  while not client.is_closed():
    if not client.is_ws_ratelimited():
      try:
        leftover_ids = list(live_channels.keys())
        is_update = update_ticker >= STREAMFEED_UPDATE_EXISTING_DELAY

        # get latest list of streamers
        response = twitch.get_streams(game_id= [game['id'] for game in games['data']], first= 6)
        streams = filter(is_match, list(response['data']))

        # update or create stream messages
        for stream in streams:
          id = stream['id']

          # create new
          if not id in live_channels:
            embed = update_embed(stream, discord.Embed())
            message = await channel.send(content= random.choice(constants.StreamPhrases), embed= embed)
            if message is not None:
              live_channels[id] = {
                "message": message,
                "embed": embed,
                "peak_viewers": stream["viewer_count"]
              }

          # update existing
          else:
            leftover_ids.remove(id)
            message: discord.Message = live_channels[id]["message"]
            if message is None:
              live_channels.pop(id)
            elif id in live_channels:
              # compute peak viewer count
              live_channels[id]["peak_viewers"] = max(live_channels[id]["peak_viewers"], stream["viewer_count"])

            # only run update periodically to prioritize new streams
            if message is not None and is_update:
              try:
                embed = update_embed(stream, live_channels[id]["embed"])
                await message.edit(embed= embed)
              except:
                live_channels.pop(id) # couldn't update message, so just remove

        # remove streams if they are no longer live
        for id in leftover_ids:
          data = live_channels.pop(id)
          message: discord.Message = data["message"]
          try:
            if message is not None:
              embed = update_embed(None, data["embed"], peak_viewer_count= data["peak_viewers"])
              await message.edit(embed= embed)
          except:
            pass

        if is_update:
          update_ticker = 0
        else:
          update_ticker += STREAMFEED_POLL_DELAY
      except Exception as e:
        print(traceback.format_exc())
    await asyncio.sleep(STREAMFEED_POLL_DELAY)

#
def streamfeed(client):
  if twitch is None:
    return

  client.loop.create_task(streamfeed_task(client))
