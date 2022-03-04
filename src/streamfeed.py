from glob import glob
import os
import string
import discord
import asyncio
import urllib.parse
from datetime import datetime
from twitchAPI.twitch import Twitch
from pprint import pprint
from dotenv import load_dotenv

load_dotenv()
TWITCH_APPKEY = os.getenv('TWITCH_APPKEY')
TWITCH_SECRET = os.getenv('TWITCH_SECRET')
STREAMFEED_CHANNEL_ID = int(os.getenv('STREAMFEED_CHANNEL_ID'))
STREAMFEED_POLL_DELAY = int(os.getenv('STREAMFEED_POLL_DELAY'))
STREAMFEED_UPDATE_EXISTING_DELAY = int(os.getenv('STREAMFEED_UPDATE_EXISTING_DELAY'))

# initialize twitch and get list of games
twitch: Twitch = None
try:
  twitch = Twitch(TWITCH_APPKEY, TWITCH_SECRET)
  games = twitch.get_games(names= [ 
    "Ratchet: Deadlocked", 
    "Ratchet and Clank: Up Your Arsenal",
    ])
except:
  print('unable to authenticate with twitch')
  pass

# creates a discord embed from a twitch stream
def create_embed(stream):
  thumbnail: string = stream["thumbnail_url"].replace("{width}", "360").replace("{height}", "240")

  embed = discord.Embed(
      url= f'https://twitch.tv/{stream["user_name"]}', 
      description= stream["title"],
      timestamp= datetime.utcnow(),
      color= 0xFFFF00
      )
  embed.set_author(name= f'{stream["user_name"]} is now streaming [{stream["language"].upper()}]', url= f'https://twitch.tv/{stream["user_name"]}', icon_url= f'https://avatar.glue-bot.xyz/twitch/{urllib.parse.quote(stream["user_name"])}')
  embed.set_thumbnail(url= f'https://avatar.glue-bot.xyz/twitch-boxart/{urllib.parse.quote(stream["game_name"])}')
  embed.set_image(url=thumbnail)
  embed.add_field(name= ':joystick: Game', value= f'{stream["game_name"]}', inline= True)
  embed.add_field(name= ':busts_in_silhouette: Viewers', value= f'{stream["viewer_count"]}', inline= True)
  embed.set_footer(text= 'Last Live')
  return embed

# background task that polls twitch and creates/updates stream messages in discord
async def streamfeed_task(client: discord.Client):
  await client.wait_until_ready()
  channel: discord.TextChannel = client.get_channel(id=STREAMFEED_CHANNEL_ID)
  live_channels = {}
  update_ticker = 0

  while not client.is_closed():
    if not client.is_ws_ratelimited():
      leftover_ids = list(live_channels.keys())
          
      # get latest list of streamers
      response = twitch.get_streams(game_id= [game['id'] for game in games['data']], first= 6)
      streams = list(response['data'])

      # update or create stream messages
      for stream in streams:
        id = stream['id']
        embed = create_embed(stream)

        # create new
        if not id in live_channels:
          message = await channel.send(content= '', embed= embed)
          if message is not None:
            live_channels[id] = message

        # update existing
        else:
          leftover_ids.remove(id)
          message: discord.Message = live_channels[id]
          if message is None:
            live_channels.pop(id)

          # only run update periodically to prioritize new streams
          elif update_ticker > STREAMFEED_UPDATE_EXISTING_DELAY:
            await message.edit(embed= embed)
        
      # remove streams if they are no longer live
      for id in leftover_ids:
        live_channels.pop(id)

      if update_ticker > STREAMFEED_UPDATE_EXISTING_DELAY:
        update_ticker = 0
      else:
        update_ticker += STREAMFEED_POLL_DELAY
    await asyncio.sleep(STREAMFEED_POLL_DELAY)

#
def streamfeed(client):
  if twitch is None:
    return

  client.loop.create_task(streamfeed_task(client))
  