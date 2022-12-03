import os
from sqlite3 import Timestamp
import traceback
import logging
import string
import discord
import asyncio
import urllib.parse
import random
import constants
import traceback
from datetime import datetime, timedelta
import googleapiclient.discovery
from pprint import pprint
from dotenv import load_dotenv
from config import *

load_dotenv()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBEFEED_POLL_DELAY = int(os.getenv('YOUTUBEFEED_POLL_DELAY'))
YOUTUBEFEED_CHANNEL_ID = os.getenv('YOUTUBEFEED_CHANNEL_ID')
#
last_query_date = datetime.utcnow()
youtube = None

# API information
api_service_name = "youtube"
api_version = "v3"
try:
  # API client
  youtube = googleapiclient.discovery.build(
    api_service_name, api_version, developerKey = YOUTUBE_API_KEY)
except Exception as e:
  print('unable to authenticate with youtube')
  logging.error(traceback.format_exc())
  pass

#
def parse_gamename(string):
  lower_string = string.lower()
  games = config_get(['Games'])
  for game in games:
    if game['Game'].lower() in lower_string:
      return game

    for filter in game['Filters']:
      if filter.lower() == lower_string:
        return game

  return None

# returns latest youtube videos since last request
def get_latest_videos():
  global last_query_date

  try:
    # build query
    request = youtube.search().list(
      part="snippet",
      channelId="UCqtDa52wBLmQs8fyAkeb8wg",
      order="date",
      type="video",
      publishedAfter=last_query_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z') + 'Z',
    )

    # execute
    response = request.execute()

    # update last date
    last_query_date = datetime.utcnow()
    last_query_date_str = last_query_date.isoformat()
    config_get(['YoutubeFeed'])['LastUpdated'] = last_query_date_str
    config_save()


    # return response
    return response
  except Exception as e:
    print('unable to get latest videos from youtube')
    logging.error(traceback.format_exc())
    pass

  return None

# creates a discord embed from a twitch stream
def update_embed(item, embed: discord.Embed):
  if item is not None:
    videoId = item['id']['videoId']
    videoUrl = f'https://www.youtube.com/watch?v={videoId}'
    videoTitle = item['snippet']['title']
    videoDescription = item['snippet']['description']
    videoThumbnailUrl = item['snippet']['thumbnails']['high']['url']
    game = parse_gamename(videoTitle)
    if game is None:
      return None

    gamename = game['Game']
    embed.color = int(game['Color'], 16)
    embed.description = f'{videoDescription}\n[youtube.com/watch?v={videoId}]({videoUrl})'
    embed.url = videoUrl
    embed.timestamp = datetime.now()
    embed.set_author(name= videoTitle, icon_url= f'https://avatar.glue-bot.xyz/youtube-avatar/q?url={urllib.parse.quote(videoUrl)}')
    #embed.set_thumbnail(url= f'https://avatar.glue-bot.xyz/twitch-boxart/{urllib.parse.quote(gamename)}')
    #embed.set_image(url=videoThumbnailUrl)
    embed.set_thumbnail(url=videoThumbnailUrl)
    embed.clear_fields()
    embed.set_footer(text= 'Posted')

    return videoUrl

  return None

# background task that polls youtube and creates video embed messages in discord
async def youtubefeed_task(client: discord.Client):
  global last_query_date
  await client.wait_until_ready()

  if YOUTUBEFEED_CHANNEL_ID is None:
    return

  channel: discord.TextChannel = client.get_channel(YOUTUBEFEED_CHANNEL_ID)
  last_updated = config_get(['YoutubeFeed'])['LastUpdated']

  if last_updated is not None:
    last_query_date = datetime.fromisoformat(last_updated)

  while not client.is_closed():
    if not client.is_ws_ratelimited():
      try:
        # get latest list of videos
        response = get_latest_videos()
        if response is not None:
          for item in response['items']:
            kind = item['id']['kind']
            if kind != 'youtube#video':
              continue

            # create message
            if False:
              embed = discord.Embed()
              content = update_embed(item, embed)
              if content is not None:
                await channel.send(content= content, embed= embed)
            else:
              videoId = item['id']['videoId']
              videoUrl = f'https://www.youtube.com/watch?v={videoId}'
              videoTitle = item['snippet']['title']
              videoDescription = item['snippet']['description']
              await channel.send(content= f'**New Youtube Video!**\n{videoUrl}\n\n*{videoDescription}*')

      except Exception as e:
        print(traceback.format_exc())
    await asyncio.sleep(YOUTUBEFEED_POLL_DELAY)

#
def youtubefeed(client):
  if youtube is None:
    return

  client.loop.create_task(youtubefeed_task(client))
