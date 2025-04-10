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
    #print(f"Authenticated: {response}")
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
    return "Success"
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    return "Error 401"
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

#
def reset_account_password(api, accountName):
  global headers
  if api not in headers:
    authenticate(api)

  if api == DEADLOCKED_API_NAME:
    appId = APPID_DEADLOCKED
  elif api == UYA_API_NAME:
    appId = APPID_RC3
  
  request = {
    'AccountName': accountName,
    'AppId': appId
  }
  route =  f"Account/resetAccountPassword"
  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], json=request, verify=False)

  if response.status_code == 200:
    return f"Success! Reset {api} account for {accountName}"
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    return "Got 401. Try again"
  elif response.status_code == 404:
    return f"{api} account not found: {accountName}"
  else:
    raise ValueError(f"{route} returned {response.status_code}")


def change_account_name(api, current_account_name, new_account_name):
  global headers
  if api not in headers:
    authenticate(api)

  if api == DEADLOCKED_API_NAME:
    appId = APPID_DEADLOCKED
  elif api == UYA_API_NAME:
    appId = APPID_RC3
  
  request = {
    'AccountName': current_account_name,
    'NewAccountName': new_account_name,
    'AppId': appId
  }
  route =  f"Account/changeAccountName"
  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], json=request, verify=False)

  if response.status_code == 200:
    return f"Success! {api} Changed account name changed from {current_account_name} to {new_account_name}"
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    return "Got 401. Try again"
  elif response.status_code == 404:
    return f"{api} account not found: {current_account_name}"
  elif response.status_code == 403:
    return f"{api} new account name already exists: {new_account_name}. Or > 14 character name or special characters in the name."
  else:
    raise ValueError(f"{route} returned {response.status_code}")

def combine_account_stats(api, account_name_from, account_name_to):
  global headers
  if api not in headers:
    authenticate(api)

  if api == DEADLOCKED_API_NAME:
    appId = APPID_DEADLOCKED
  elif api == UYA_API_NAME:
    appId = APPID_RC3
  
  request = {
    'AccountNameFrom': account_name_from,
    'AccountNameTo': account_name_to,
    'AppId': appId
  }
  route =  f"Stats/combineAccountStat"
  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], json=request, verify=False)

  if response.status_code == 200:
    return f"Success! {api} Added stats from {account_name_from} to {account_name_to}"
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    return "Got 401. Try again"
  elif response.status_code == 404:
    return f"{api} account not found"
  elif response.status_code == 403:
    return f"{api} error 403, {response.text}"
  else:
    raise ValueError(f"{route} returned {response.status_code}")


#
def get_announcements(api, app_id):
  global headers
  if api not in headers:
    authenticate(api)

  route = f"api/Keys/getAnnouncementsList?AppId={app_id}"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  elif response.status_code == 204:
    return response.json()
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    raise ValueError(f"{route} returned {response.status_code}")
  else:
    raise ValueError(f"{route} returned {response.status_code}")

def delete_announcements(api, app_id, id):
  global headers
  if api not in headers:
    authenticate(api)

  route = f"api/Keys/deleteAnnouncement?Id={id}"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return "Success"
  elif response.status_code == 204:
    return "Success"
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    raise ValueError(f"{route} returned {response.status_code}")
  else:
    raise ValueError(f"{route} returned {response.status_code}")

def post_announcement(api, ntsc_or_pal, announcement):
  global headers
  if api not in headers:
    authenticate(api)

  if api == DEADLOCKED_API_NAME:
    if ntsc_or_pal == 'NTSC':
      appId = APPID_GLADIATOR
    elif ntsc_or_pal == 'PAL':
      appId = APPID_DEADLOCKED
  elif api == UYA_API_NAME:
    if ntsc_or_pal == 'NTSC':
      appId = APPID_UYA
    elif ntsc_or_pal == 'PAL':
      appId = APPID_RC3
  
  d = get_announcements(api, appId)
  ids = [x['Id'] for x in d]

  for id in ids:
    # Delete all current announcements
    delete_announcements(api, appId, id)

  request = {
    'AnnouncementTitle': datetime.datetime.now().strftime('%Y-%m-%d') + ':',
    'AnnouncementBody': announcement,
    'ToDt': (datetime.datetime.now() + datetime.timedelta(30)).strftime('%Y-%m-%d'),
    'AppId': appId
  }
  route =  f"api/Keys/postAnnouncement"
  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], json=request, verify=False)

  if response.status_code == 200:
    return f"Success! Added announcement {announcement}"
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    return "Got 401. Try again"
  elif response.status_code == 404:
    return f"{api} 404"
  elif response.status_code == 403:
    return f"{api} error 403, {response.text}"
  else:
    raise ValueError(f"{route} returned {response.status_code}")

def ban_account(api, ntsc_or_pal, account_name):
  global headers
  if api not in headers:
    authenticate(api)

  if api == DEADLOCKED_API_NAME:
    if ntsc_or_pal == 'NTSC':
      appId = APPID_GLADIATOR
    elif ntsc_or_pal == 'PAL':
      appId = APPID_DEADLOCKED
  elif api == UYA_API_NAME:
    if ntsc_or_pal == 'NTSC':
      appId = APPID_UYA
    elif ntsc_or_pal == 'PAL':
      appId = APPID_RC3

  request = {
    'AccountName': account_name,
    'AppId': appId
  }
  route =  f"Account/banAccount"
  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], json=request, verify=False)

  if response.status_code == 200:
    return f"Success! Banned {account_name}"
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    return "Got 401. Try again"
  elif response.status_code == 404:
    return f"{api} 404 Not Found"
  elif response.status_code == 403:
    return f"{api} error 403, {response.text}"
  else:
    raise ValueError(f"{route} returned {response.status_code}")


def ban_ip(api, ntsc_or_pal, account_name):
  global headers
  if api not in headers:
    authenticate(api)

  if api == DEADLOCKED_API_NAME:
    if ntsc_or_pal == 'NTSC':
      appId = APPID_GLADIATOR
    elif ntsc_or_pal == 'PAL':
      appId = APPID_DEADLOCKED
  elif api == UYA_API_NAME:
    if ntsc_or_pal == 'NTSC':
      appId = APPID_UYA
    elif ntsc_or_pal == 'PAL':
      appId = APPID_RC3

  request = {
    'AccountName': account_name,
    'AppId': appId
  }
  route =  f"Account/banIpByAccountName"
  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], json=request, verify=False)

  if response.status_code == 200:
    return f"Success! Banned {account_name}"
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    return "Got 401. Try again"
  elif response.status_code == 404:
    return f"{api} 404 Not Found"
  elif response.status_code == 403:
    return f"{api} error 403, {response.text}"
  else:
    raise ValueError(f"{route} returned {response.status_code}")


def ban_mac(api, ntsc_or_pal, account_name):
  global headers
  if api not in headers:
    authenticate(api)

  if api == DEADLOCKED_API_NAME:
    if ntsc_or_pal == 'NTSC':
      appId = APPID_GLADIATOR
    elif ntsc_or_pal == 'PAL':
      appId = APPID_DEADLOCKED
  elif api == UYA_API_NAME:
    if ntsc_or_pal == 'NTSC':
      appId = APPID_UYA
    elif ntsc_or_pal == 'PAL':
      appId = APPID_RC3

  request = {
    'AccountName': account_name,
    'AppId': appId
  }
  route =  f"Account/banMacByAccountName"
  response = requests.post(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], json=request, verify=False)

  if response.status_code == 200:
    return f"Success! Banned {account_name}"
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    return "Got 401. Try again"
  elif response.status_code == 404:
    return f"{api} 404 Not Found"
  elif response.status_code == 403:
    return f"{api} error 403, {response.text}"
  else:
    raise ValueError(f"{route} returned {response.status_code}")




urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
