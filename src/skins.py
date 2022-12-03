
import os
import discord
import requests
import random
import json
import datetime
import traceback
import constants
import urllib3
from discord.ext import commands
from mediusapi import *


skins = {
    'UYA - Nefarious': 0xe1234567,
    'UYA - Dan': 0xe76b492c,
    'DL - Mr. Sunshine': 0x14202239,
    'DL - Jak': 0x02050710,
    'DL - Renegade': 0x26e41939,
    'DL - Eugene': 0x2dafbf84,
    'DL - Vernon': 0xcc97b7af,
}

code_map = {
    '0': 'Up',
    '1': 'Up',
    '2': 'Up',
    '3': 'Up',
    '4': 'Down',
    '5': 'Down',
    '6': 'Down',
    '7': 'Down',
    '8': 'Left',
    '9': 'Left',
    'a': 'Left',
    'b': 'Left',
    'c': 'Right',
    'd': 'Right',
    'e': 'Right',
    'f': 'Right',
}

def get_skin_codes(username: str):

    username = username.strip().upper()

    username_hex_code = 0

    for i in range(len(username)):
        letter_hex = ord(username[i]) * (i + 1)
        username_hex_code += letter_hex

    #print(username_hex_code)

    skin_codes = []
    for skin_name, skin_hex in skins.items():
        cheat_value = skin_hex * username_hex_code
        cheat_value = str(hex(cheat_value))[2:]
        #print(cheat_value)
        cheat_value = cheat_value[-8:]
        #print(cheat_value)
        cheat_value = list(reversed(list(str(cheat_value))))
        #print(cheat_value)

        # Get the cheat
        full_code = ''
        for code in cheat_value:
            full_code += code_map[code] + ' '
        full_code = full_code.strip()

        #print(skin_name + ': ', full_code)
        skin_codes.append([skin_name, full_code])

    return skin_codes


async def get_dl_skins(ctx: discord.ApplicationContext, username):
  skin_codes = get_skin_codes(username)
  embed = discord.Embed()
  for skin_name, skin_code in skin_codes:
    if skin_name.startswith("DL -"):
      skin_name = skin_name.strip("DL - ")
      embed.add_field(name=skin_name, value=skin_code, inline=False)
  #embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'DL Skin Codes for {username}'
  await ctx.respond(content="Here's your Skins! That'll be 1,000 bolts.", embed=embed)


async def get_uya_skins(ctx: discord.ApplicationContext, username):
  skin_codes = get_skin_codes(username)
  embed = discord.Embed()
  for skin_name, skin_code in skin_codes:
    if skin_name.startswith("UYA -"):
      skin_name = skin_name.strip("UYA - ")
      embed.add_field(name=skin_name, value=skin_code, inline=False)
  #embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'UYA Skin Codes for {username}'
  await ctx.respond(content="Here's your Skins! That'll be 1,000 bolts.", embed=embed)
