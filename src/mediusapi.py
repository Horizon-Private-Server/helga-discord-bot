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
DEADLOCKED_ACC_NAME = 'SYSTEM'
APPID_DEADLOCKED = 11184
APPID_GLADIATOR = 11354

UYA_API_NAME = 'UYA'
UYA_ACC_NAME = 'admin'
APPID_RC3 = 10683
APPID_UYA = 10684

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
    #print(response.json())
    token = response.json()["Token"]
    headers[api] = { "Authorization": f"Bearer {token}" }
    #print("HEADERS!", headers)
    return True
  else:
    print(response.status_code)
    print("ERROR AUTHENTICATING!")
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
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
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
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_leaderboard_top(api, app_id, stat_id, count, custom = False, orderAsc = False):
  global headers
  if api not in headers:
    authenticate(api)
  
  optional_custom = 'Custom' if custom else ''

  route =  f"Stats/getLeaderboard{optional_custom}?{optional_custom}StatId={stat_id}&StartIndex={0}&Size={count}&AppId={app_id}&orderAsc={orderAsc}"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_leaderboard_top10(api, app_id, stat_id, custom = False, orderAsc = False):
  return get_leaderboard_top(api, app_id, stat_id, count=10, custom= custom, orderAsc= orderAsc)

#
def get_players_online(api):
  global headers
  if api not in headers:
    authenticate(api)
  
  route =  f"Account/getOnlineAccounts"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_active_games(api):
  global headers
  if api not in headers:
    authenticate(api)
  
  #print("HEADERS:", headers)
  route =  f"api/Game/list"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_settings(api, appId):
  global headers
  if api not in headers:
    authenticate(api)
  
  route =  f"api/Keys/getSettings?appId={appId}"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def set_settings(api, appId, settings):
  global headers
  if api not in headers:
    authenticate(api)
  
  route =  f"api/Keys/setSettings?appId={appId}"
  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], json=settings, verify=False)

  if response.status_code == 200:
    return
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def reset_custom_leaderboard(api, appId, statId):
  global headers
  if api not in headers:
    authenticate(api)
  
  request = {
    'AppId': appId,
    'StatId': statId
  }
  route =  f"Stats/resetLeaderboardCustom"
  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], json=request, verify=False)

  if response.status_code == 200:
    return
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
  else:
    raise ValueError(f"{route} returned {response.status_code}")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
