
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
import base64
from io import BytesIO
from PIL import Image
from discord.ext import commands
from mediusapi import *

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

#
async def set_dl_banner_image(game: str, image_url: str):

  image = None

  # load image from url
  image_png_base64 = None
  if image_url is not None:
    image_png_buffered = BytesIO()
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))
    image = image.resize((256, 64))
    image.save(image_png_buffered, format="PNG")
    image_b64 = base64.b64encode(image_png_buffered.getvalue())
    image_png_base64 = image_b64.decode()

  api_name = get_api_from_game_name(game)
  acc_name = get_account_name_from_api(api_name)
  settings = {
    f'{acc_name}_BannerImageBase64': image_png_base64,
  }

  # set
  appids = get_appids_from_game_name(game)
  for appid in appids:
    set_settings(api_name, appid, settings)

  return image
