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

# tipoftheday path
_tipoftheday_path = 'tipoftheday.txt'

#
def generate_tip_embed(tipoftheday_config, tip):
  
  embed: discord.Embed = discord.Embed()
  
  # base
  embed.color = int(tipoftheday_config["Color"], 0)
  embed.title = f'Tip of the Day'
  embed.timestamp = datetime.now()
  embed.description = tip
  embed.set_thumbnail(url=tipoftheday_config['Thumbnail'])
  embed.clear_fields()
  #embed.set_footer(text= 'Last Updated')

  #embed.add_field(name= '\u200B', value= 'Active Games:', inline= False)
  return embed

#
def get_next_tip_datetime(last_datetime: datetime):
  now = datetime.utcnow()
  next = now

  # send at 9AM EST
  target_hour = 24 - 5

  # either the next tip will be sent a day after the last
  # or it will be sent at the next available target_hour,
  # be that today's target_hour, or tomorrows
  if last_datetime is None:
    if now.hour > target_hour:
      next = next + timedelta(days=1)
  else:
    next = last_datetime + timedelta(days=1)

  return datetime(year= next.year, month= next.month, day= next.day, hour= target_hour)

# background task that prints out the tip of the day every day
async def tipoftheday_task(client: discord.Client, tipoftheday_config, tips):
  await client.wait_until_ready()
  channel: discord.TextChannel = client.get_channel(tipoftheday_config["ChannelId"])
  message: discord.Message = None
  embed: discord.Embed = discord.Embed()
  round_robin = []
  datetime_sendnexttip: datetime = get_next_tip_datetime(None)

  while not client.is_closed():
    if not client.is_ws_ratelimited():
      try:
        
        # send once a day
        now = datetime.utcnow()
        if not datetime_sendnexttip or now > datetime_sendnexttip:

          # get next time
          datetime_sendnexttip = get_next_tip_datetime(datetime_sendnexttip)

          # generate random order 
          if not round_robin:
            round_robin = [x for x in range(len(tips))]
            random.shuffle(round_robin)

          # send first in round robin list
          tip_index = round_robin[0]
          tip = tips[tip_index]
          message = await channel.send(content= None, embed=generate_tip_embed(tipoftheday_config, tip))

          # remove tip from round_robin list
          round_robin.remove(tip_index)

      except Exception as e:
        print(traceback.format_exc())
    await asyncio.sleep(0)

#
def read_tips():
  
  # if config file doesn't exist, create new with defaults
  if os.path.exists(_tipoftheday_path):
    print("Found tipoftheday!!! ")
    with open(_tipoftheday_path, 'r') as f:
      tips = [line.strip() for line in f.read().split(sep= ';')]
      tips = list(filter(lambda x: x, tips))
      return tips
  else:
    print("No tipoftheday found!")

#
def tipoftheday(client):
  i = 0
  tipoftheday_config = config_get(['TipOfTheDay'])
  client.loop.create_task(tipoftheday_task(client, tipoftheday_config, read_tips()))

