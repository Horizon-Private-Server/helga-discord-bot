from datetime import date
import os
from venv import create
import discord
import requests
import random
import json
import datetime
import traceback
import constants
from discord.ext import commands
from dotenv import load_dotenv

headers = None

load_dotenv()
USERNAME = os.getenv('MIDDLEWARE_USERNAME')
PASSWORD = os.getenv('MIDDLEWARE_PASSWORD')
MIDDLEWARE_ENDPOINT = os.getenv('MIDDLEWARE_ENDPOINT')

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
def get_dl_skill_level(rank):
  i = 0
  if rank >= constants.DEADLOCKED_SKILLS_TABLE[9]:
    return 10
  if rank <= constants.DEADLOCKED_SKILLS_TABLE[0]:
    return 1

  while rank > constants.DEADLOCKED_SKILLS_TABLE[i]:
    i += 1
  
  return i + (rank - constants.DEADLOCKED_SKILLS_TABLE[i-1]) / (constants.DEADLOCKED_SKILLS_TABLE[i] - constants.DEADLOCKED_SKILLS_TABLE[i-1])

def safe_ratio(num, denom):
  if denom == 0:
    return num
  
  return num/denom

def seconds_tostr(seconds):
  minutes = seconds // 60
  hours = minutes // 60

  return f'{hours}h {minutes % 60}m {seconds % 60}s'

def create_embed(account, fields):
  account_id = account["AccountId"]
  embed = discord.Embed()

  for stat_field in fields:
    value = ''
    if 'StatId' in stat_field:
      leaderboard = get_leaderboard(account_id, stat_field['StatId'], stat_field['Custom'])
      value = leaderboard["StatValue"]
      if not 'FormatValue' in stat_field:
        value = f'{get_dl_skill_level(value):.2f}'
      else:
        value = stat_field['FormatValue'](value)

      value = f'Rank {leaderboard["Index"]+1}' + (f' [{value}]' if value is not None else '')
    

    inline = True if 'Inline' not in stat_field else stat_field['Inline']

    if 'Children' in stat_field:
      #value += '```'
      for child_field in stat_field['Children']:
        value += f'\n{child_field["Name"]}: {child_field["Value"]()}'
      #value += '```'

    embed.add_field(name=stat_field['Name'], value=value, inline=inline)
  
  return embed


#
async def get_dl_overall_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Overall Rank',
      'StatId': constants.ACCOUNT_STAT_OVERALL_RANK,
      'Custom': False,
      'Inline': False,
      'Children': [
        {
          'Name': 'Games Played',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_GAMES_PLAYED]}'
        },
        {
          'Name': 'Disconnects',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_DISCONNECTS]}'
        },
        {
          'Name': 'Wins (W/L)',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_WINS]} ({safe_ratio(stats[constants.ACCOUNT_STAT_WINS],stats[constants.ACCOUNT_STAT_LOSSES]):.02f})'
        },
        {
          'Name': 'Kills (K/D)',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_KILLS]} ({safe_ratio(stats[constants.ACCOUNT_STAT_KILLS],stats[constants.ACCOUNT_STAT_DEATHS]):.02f})'
        },
        {
          'Name': 'Squats',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_SQUATS]}'
        }
      ]
    },
    {
      'Name': 'Conquest Rank',
      'StatId': constants.ACCOUNT_STAT_CONQUEST_RANK,
      'Custom': False
    },
    {
      'Name': 'CTF Rank',
      'StatId': constants.ACCOUNT_STAT_CTF_RANK,
      'Custom': False
    },
    {
      'Name': 'Deathmatch Rank',
      'StatId': constants.ACCOUNT_STAT_DEATHMATCH_RANK,
      'Custom': False
    },
    {
      'Name': 'Juggernaut Rank',
      'StatId': constants.ACCOUNT_STAT_JUGGERNAUT_RANK,
      'Custom': False
    },
    {
      'Name': 'KOTH Rank',
      'StatId': constants.ACCOUNT_STAT_KOTH_RANK,
      'Custom': False
    },
    {
      'Name': 'Payload Rank',
      'StatId': constants.CUSTOM_STAT_PAYLOAD_RANK,
      'Custom': True
    },
    {
      'Name': 'SND Rank',
      'StatId': constants.CUSTOM_STAT_SND_RANK,
      'Custom': True
    },
    {
      'Name': 'Survival Rank',
      'StatId': constants.CUSTOM_STAT_SURVIVAL_RANK,
      'Custom': True
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Overall Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_cq_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Conquest Rank',
      'StatId': constants.ACCOUNT_STAT_CONQUEST_RANK,
      'Custom': False,
      'Inline': False,
      'Children': [
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CONQUEST_WINS]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CONQUEST_LOSSES]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CONQUEST_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CONQUEST_DEATHS]}'
        },
        {
          'Name': 'Nodes Captured',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CONQUEST_NODES_TAKEN]}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Conquest Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_ctf_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'CTF Rank',
      'StatId': constants.ACCOUNT_STAT_CTF_RANK,
      'Custom': False,
      'Inline': False,
      'Children': [
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CTF_WINS]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CTF_LOSSES]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CTF_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CTF_DEATHS]}'
        },
        {
          'Name': 'Flags Captured',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_CTF_FLAGS_CAPTURED]}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'CTF Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_dm_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Deathmatch Rank',
      'StatId': constants.ACCOUNT_STAT_DEATHMATCH_RANK,
      'Custom': False,
      'Inline': False,
      'Children': [
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_DEATHMATCH_WINS]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_DEATHMATCH_LOSSES]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_DEATHMATCH_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_DEATHMATCH_DEATHS]}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Deathmatch Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_koth_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'KOTH Rank',
      'StatId': constants.ACCOUNT_STAT_KOTH_RANK,
      'Custom': False,
      'Inline': False,
      'Children': [
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_KOTH_WINS]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_KOTH_LOSSES]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_KOTH_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_KOTH_DEATHS]}'
        },
        {
          'Name': 'Hill Time',
          'Value': lambda : f'{seconds_tostr(stats[constants.ACCOUNT_STAT_KOTH_TIME])}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'KOTH Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_juggy_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Juggernaut Rank',
      'StatId': constants.ACCOUNT_STAT_JUGGERNAUT_RANK,
      'Custom': False,
      'Inline': False,
      'Children': [
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_JUGGERNAUT_WINS]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_JUGGERNAUT_LOSSES]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_JUGGERNAUT_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_JUGGERNAUT_LOSSES]}'
        },
        {
          'Name': 'Juggernaut Time',
          'Value': lambda : f'{seconds_tostr(stats[constants.ACCOUNT_STAT_JUGGERNAUT_TIME])}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Juggernaut Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_weapons_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Wrench',
      'StatId': constants.ACCOUNT_STAT_WRENCH_KILLS,
      'FormatValue': lambda x: None,
      'Custom': False,
      'Inline': True,
      'Children': [
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_WRENCH_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_WRENCH_DEATHS]}'
        }
      ]
    },
    {
      'Name': 'Dual Vipers',
      'StatId': constants.ACCOUNT_STAT_DUAL_VIPER_KILLS,
      'FormatValue': lambda x: None,
      'Custom': False,
      'Inline': True,
      'Children': [
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_DUAL_VIPER_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_DUAL_VIPER_DEATHS]}'
        }
      ]
    },
    {
      'Name': 'Magma Cannon',
      'StatId': constants.ACCOUNT_STAT_MAGMA_CANNON_KILLS,
      'FormatValue': lambda x: None,
      'Custom': False,
      'Inline': True,
      'Children': [
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_MAGMA_CANNON_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_MAGMA_CANNON_DEATHS]}'
        }
      ]
    },
    {
      'Name': 'Arbiter',
      'StatId': constants.ACCOUNT_STAT_ARBITER_KILLS,
      'FormatValue': lambda x: None,
      'Custom': False,
      'Inline': True,
      'Children': [
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_ARBITER_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_ARBITER_DEATHS]}'
        }
      ]
    },
    {
      'Name': 'Fusion Rifle',
      'StatId': constants.ACCOUNT_STAT_FUSION_RIFLE_KILLS,
      'FormatValue': lambda x: None,
      'Custom': False,
      'Inline': True,
      'Children': [
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_FUSION_RIFLE_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_FUSION_RIFLE_DEATHS]}'
        }
      ]
    },
    {
      'Name': 'Mine Launcher',
      'StatId': constants.ACCOUNT_STAT_HUNTER_MINE_KILLS,
      'FormatValue': lambda x: None,
      'Custom': False,
      'Inline': True,
      'Children': [
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_HUNTER_MINE_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_HUNTER_MINE_DEATHS]}'
        }
      ]
    },
    {
      'Name': 'B6 Obliterator',
      'StatId': constants.ACCOUNT_STAT_B6_OBLITERATOR_KILLS,
      'FormatValue': lambda x: None,
      'Custom': False,
      'Inline': True,
      'Children': [
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_B6_OBLITERATOR_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_B6_OBLITERATOR_DEATHS]}'
        }
      ]
    },
    {
      'Name': 'Scorpion Flail',
      'StatId': constants.ACCOUNT_STAT_SCORPION_FLAIL_KILLS,
      'FormatValue': lambda x: None,
      'Custom': False,
      'Inline': True,
      'Children': [
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_SCORPION_FLAIL_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_SCORPION_FLAIL_DEATHS]}'
        }
      ]
    },
    {
      'Name': 'Holoshield',
      'StatId': constants.ACCOUNT_STAT_HOLOSHIELD_KILLS,
      'FormatValue': lambda x: None,
      'Custom': False,
      'Inline': True,
      'Children': [
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_HOLOSHIELD_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats[constants.ACCOUNT_STAT_HOLOSHIELD_DEATHS]}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Weapon Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_spleef_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Spleef Rank',
      'StatId': constants.CUSTOM_STAT_SPLEEF_RANK,
      'Custom': True,
      'Inline': False,
      'Children': [
        {
          'Name': 'Rounds Played',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SPLEEF_ROUNDS_PLAYED]}'
        },
        {
          'Name': 'Time Played',
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_SND_TIME_PLAYED])}'
        },
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SPLEEF_WINS]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SPLEEF_LOSSES]}'
        },
        {
          'Name': 'Points',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SPLEEF_POINTS]}'
        },
        {
          'Name': 'Boxes Broken',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SPLEEF_BOXES_BROKEN]}'
        },
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Spleef Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_climber_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Climber Rank',
      'StatId': constants.CUSTOM_STAT_CLIMBER_RANK,
      'Custom': True,
      'Inline': False,
      'Children': [
        {
          'Name': 'Games Played',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_CLIMBER_GAMES_PLAYED]}'
        },
        {
          'Name': 'Time Played',
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_CLIMBER_TIME_PLAYED])}'
        },
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_CLIMBER_WINS]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_CLIMBER_LOSSES]}'
        },
        {
          'Name': 'High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_CLIMBER_HIGH_SCORE]}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Climber Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_gungame_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Gun Game Rank',
      'StatId': constants.CUSTOM_STAT_GUNGAME_RANK,
      'Custom': True,
      'Inline': False,
      'Children': [
        {
          'Name': 'Games Played',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_GUNGAME_GAMES_PLAYED]}'
        },
        {
          'Name': 'Time Played',
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_GUNGAME_TIME_PLAYED])}'
        },
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_GUNGAME_WINS]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_GUNGAME_LOSSES]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_GUNGAME_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_GUNGAME_DEATHS]}'
        },
        {
          'Name': 'Promotions',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_GUNGAME_TIMES_PROMOTED]}'
        },
        {
          'Name': 'Demotions',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_GUNGAME_TIMES_DEMOTED]}'
        },
        {
          'Name': 'Humiliations',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_GUNGAME_DEMOTIONS]}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Gun Game Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_infected_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Infected Rank',
      'StatId': constants.CUSTOM_STAT_INFECTED_RANK,
      'Custom': True,
      'Inline': False,
      'Children': [
        {
          'Name': 'Games Played',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_INFECTED_GAMES_PLAYED]}'
        },
        {
          'Name': 'Time Played',
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_INFECTED_TIME_PLAYED])}'
        },
        {
          'Name': 'Wins as Survivor',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_INFECTED_WINS_AS_SURVIVOR]}'
        },
        {
          'Name': 'Wins as First Infected',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_INFECTED_WINS_AS_FIRST_INFECTED]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_INFECTED_LOSSES]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_INFECTED_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_INFECTED_DEATHS]}'
        },
        {
          'Name': 'Infections',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_INFECTED_INFECTIONS]}'
        },
        {
          'Name': 'Infected',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_INFECTED_TIMES_INFECTED]}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Infected Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_payload_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Payload Rank',
      'StatId': constants.CUSTOM_STAT_PAYLOAD_RANK,
      'Custom': True,
      'Inline': False,
      'Children': [
        {
          'Name': 'Games Played',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_PAYLOAD_GAMES_PLAYED]}'
        },
        {
          'Name': 'Time Played',
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_PAYLOAD_TIME_PLAYED])}'
        },
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_PAYLOAD_WINS]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_PAYLOAD_LOSSES]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_PAYLOAD_KILLS]}'
        },
        {
          'Name': 'Kills on Escorts',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_PAYLOAD_KILLS_ON_HOT]}'
        },
        {
          'Name': 'Kills while Escorting',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_PAYLOAD_KILLS_WHILE_HOT]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_PAYLOAD_DEATHS]}'
        },
        {
          'Name': 'Escort Time',
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_PAYLOAD_POINTS])}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Payload Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_snd_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'SND Rank',
      'StatId': constants.CUSTOM_STAT_SND_RANK,
      'Custom': True,
      'Inline': False,
      'Children': [
        {
          'Name': 'Games Played',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_GAMES_PLAYED]}'
        },
        {
          'Name': 'Time Played',
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_SND_TIME_PLAYED])}'
        },
        {
          'Name': 'Wins',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_WINS]}'
        },
        {
          'Name': 'Wins Attacking',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_WINS_ATTACKING]}'
        },
        {
          'Name': 'Wins Defending',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_WINS_DEFENDING]}'
        },
        {
          'Name': 'Losses',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_LOSSES]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_DEATHS]}'
        },
        {
          'Name': 'Plants',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_PLANTS]}'
        },
        {
          'Name': 'Defuses',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_DEFUSES]}'
        },
        {
          'Name': 'Ninja Defuses',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SND_NINJA_DEFUSES]}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'SND Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)

#
async def get_dl_survival_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fields = [
    {
      'Name': 'Survival Rank',
      'StatId': constants.CUSTOM_STAT_SURVIVAL_RANK,
      'Custom': True,
      'Inline': True,
      'Children': [
        {
          'Name': 'Games Played',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_GAMES_PLAYED]}'
        },
        {
          'Name': 'Time Played',
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_SURVIVAL_TIME_PLAYED])}'
        },
        {
          'Name': 'Experience',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_XP]}'
        },
        {
          'Name': 'Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_KILLS]}'
        },
        {
          'Name': 'Deaths',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_DEATHS]}'
        },
        {
          'Name': 'Revives',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_REVIVES]}'
        },
        {
          'Name': 'Revived',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_TIMES_REVIVED]}'
        }
      ]
    },
    {
      'Name': 'Weapons',
      'Inline': True,
      'Children': [
        {
          'Name': 'Wrench Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_WRENCH_KILLS]}'
        },
        {
          'Name': 'Dual Viper Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_DUAL_VIPER_KILLS]}'
        },
        {
          'Name': 'Magma Cannon Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAGMA_CANNON_KILLS]}'
        },
        {
          'Name': 'Arbiter Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_ARBITER_KILLS]}'
        },
        {
          'Name': 'Fusion Rifle Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_FUSION_RIFLE_KILLS]}'
        },
        {
          'Name': 'Mine Launcher Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MINE_LAUNCHER_KILLS]}'
        },
        {
          'Name': 'B6 Obliterator Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_B6_OBLITERATOR_KILLS]}'
        },
        {
          'Name': 'Scorpion Flail Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_SCORPION_FLAIL_KILLS]}'
        }
      ]
    },
    {
      'Name': 'Exterminator',
      'StatId': constants.CUSTOM_STAT_SURVIVAL_D5_HIGH_SCORE,
      'Custom': True,
      'FormatValue': lambda x: f'{x} rounds',
      'Inline': False
    },
    {
      'Name': 'Hero',
      'StatId': constants.CUSTOM_STAT_SURVIVAL_D4_HIGH_SCORE,
      'Custom': True,
      'FormatValue': lambda x: f'{x} rounds',
      'Inline': False
    },
    {
      'Name': 'Gladiator',
      'StatId': constants.CUSTOM_STAT_SURVIVAL_D3_HIGH_SCORE,
      'Custom': True,
      'FormatValue': lambda x: f'{x} rounds',
      'Inline': False
    },
    {
      'Name': 'Contestant',
      'StatId': constants.CUSTOM_STAT_SURVIVAL_D2_HIGH_SCORE,
      'Custom': True,
      'FormatValue': lambda x: f'{x} rounds',
      'Inline': False
    },
    {
      'Name': 'Couch Potato',
      'StatId': constants.CUSTOM_STAT_SURVIVAL_D1_HIGH_SCORE,
      'Custom': True,
      'FormatValue': lambda x: f'{x} rounds',
      'Inline': False
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url='https://rac-horizon.com/downloads/dreadzone.png')
  embed.title = f'Survival Stats for {account_name}'
  await ctx.respond(content=random.choice(constants.StatsPhrases), embed=embed)


#
DEADLOCKED_GET_STATS_CHOICES = {
  "Overall": get_dl_overall_stats,
  "Conquest": get_dl_cq_stats,
  "Climber": get_dl_climber_stats,
  "Capture the Flag": get_dl_ctf_stats,
  "Deathmatch": get_dl_dm_stats,
  "Gun Game": get_dl_gungame_stats,
  "Infected": get_dl_infected_stats,
  "King of the Hill": get_dl_koth_stats,
  "Payload": get_dl_payload_stats,
  "Search and Destroy": get_dl_snd_stats,
  "Juggernaut": get_dl_juggy_stats,
  "Spleef": get_dl_spleef_stats,
  "Survival": get_dl_survival_stats,
  "Weapons": get_dl_weapons_stats
}

#
async def get_dl_stats(ctx: discord.ApplicationContext, stat: str, name: str):
  try:
    account = get_account(11184, name)
    if stat in DEADLOCKED_GET_STATS_CHOICES:
      await DEADLOCKED_GET_STATS_CHOICES[stat](ctx, account)
    else:
      await ctx.respond('Invalid stat.')
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Account `{name}` not found.')
  
