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

load_dotenv()
USERNAME = os.getenv('MIDDLEWARE_USERNAME')
PASSWORD = os.getenv('MIDDLEWARE_PASSWORD')
MIDDLEWARE_ENDPOINT = os.getenv('MIDDLEWARE_ENDPOINT')

headers = None

#
def authenticate():
  global headers
  data = {
    "AccountName": USERNAME,
    "Password": PASSWORD
  }

  response = requests.post(MIDDLEWARE_ENDPOINT + "Account/authenticate", json=data, verify=False)
  if response.status_code == 200:
    print(response.json())
    token = response.json()["Token"]
    headers = { "Authorization": f"Bearer {token}" }
    return True
  else:
    return False

#
def get_account(app_id, account_name):
  global headers
  if headers is None:
    authenticate()

  route = f"Account/searchAccountByName?AccountName={account_name}&AppId={app_id}"
  response = requests.get(MIDDLEWARE_ENDPOINT + route, headers=headers, verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_leaderboard(account_id, stat_id, custom = False):
  global headers
  if headers is None:
    authenticate()
  
  optional_custom = 'Custom' if custom else ''

  route =  f"Stats/getPlayerLeaderboardIndex{optional_custom}?AccountId={account_id}&{optional_custom}StatId={stat_id+1}"
  response = requests.get(MIDDLEWARE_ENDPOINT + route, headers=headers, verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_leaderboard_top5(stat_id, custom = False):
  global headers
  if headers is None:
    authenticate()
  
  optional_custom = 'Custom' if custom else ''

  route =  f"Stats/getLeaderboard{optional_custom}?{optional_custom}StatId={stat_id}&StartIndex={0}&Size={5}&AppId={11184}"
  response = requests.get(MIDDLEWARE_ENDPOINT + route, headers=headers, verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_players_online():
  global headers
  if headers is None:
    authenticate()
  
  route =  f"Account/getOnlineAccounts"
  response = requests.get(MIDDLEWARE_ENDPOINT + route, headers=headers, verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

#
def get_active_games():
  global headers
  if headers is None:
    authenticate()
  
  route =  f"api/Game/list"
  response = requests.get(MIDDLEWARE_ENDPOINT + route, headers=headers, verify=False)

  if response.status_code == 200:
    return response.json()
  else:
    raise ValueError(f"{route} returned {response.status_code}")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
