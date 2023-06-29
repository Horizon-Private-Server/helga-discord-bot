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
from dotenv import load_dotenv
from typing import List

DEADLOCKED_API_NAME = 'DL'
UYA_API_NAME = 'UYA'

load_dotenv()

headers = {}

#
def authenticate(api):
  global headers
  data = {
    "AccountName": os.getenv(f'MIDDLEWARE_USERNAME_{api}'),
    "Password": os.getenv(f'MIDDLEWARE_PASSWORD_{api}')
  }

  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + "Account/authenticate", json=data, verify=False)
  if response.status_code == 200:
    print(response.json())
    token = response.json()["Token"]
    headers[api] = { "Authorization": f"Bearer {token}" }
    return True
  else:
    return None

#
def get_account(api, app_id, account_name):
  global headers
  if api not in headers:
    authenticate(api)

  route = f"Account/searchAccountByName?AccountName={account_name}&AppId={app_id}"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_leaderboard(api, app_id, account_id, stat_id, custom = False):
  global headers
  if api not in headers:
    authenticate(api)
  
  optional_custom = 'Custom' if custom else ''

  route =  f"Stats/getPlayerLeaderboardIndex{optional_custom}?AccountId={account_id}&{optional_custom}StatId={stat_id+1}&AppId={app_id}"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_leaderboard_top5(api, app_id, stat_id, custom = False):
  global headers
  if api not in headers:
    authenticate(api)
  
  optional_custom = 'Custom' if custom else ''

  route =  f"Stats/getLeaderboard{optional_custom}?{optional_custom}StatId={stat_id}&StartIndex={0}&Size={5}&AppId={app_id}"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_players_online(api):
  global headers
  if api not in headers:
    authenticate(api)
  
  route =  f"Account/getOnlineAccounts"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_active_games(api):
  global headers
  if api not in headers:
    authenticate(api)
  
  route =  f"api/Game/list"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
