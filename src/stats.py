
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
from scavengerhunt import get_scavenger_hunt_dates, get_discord_string_from_date
from mediusapi import *
from datetime import timedelta

#
def get_dl_skill_level(rank):
  i = 0
  prestige = rank // 10000
  rank = rank % 10000
  if rank == 0 and rank > 0:
    prestige -= 1

  if rank <= constants.DEADLOCKED_SKILLS_TABLE[0] and prestige > 0:
    return prestige * 10
  if rank >= constants.DEADLOCKED_SKILLS_TABLE[9]:
    return 10 + (prestige * 10)
  if rank <= constants.DEADLOCKED_SKILLS_TABLE[0]:
    return 1 + (prestige * 10)

  while rank > constants.DEADLOCKED_SKILLS_TABLE[i]:
    i += 1
  
  return (prestige * 10) + i + (rank - constants.DEADLOCKED_SKILLS_TABLE[i-1]) / (constants.DEADLOCKED_SKILLS_TABLE[i] - constants.DEADLOCKED_SKILLS_TABLE[i-1])

def safe_ratio(num, denom):
  if denom == 0:
    return num
  
  return num/denom

def seconds_tostr(seconds):
  minutes = seconds // 60
  hours = minutes // 60

  return f'{hours}h {minutes % 60}m {seconds % 60}s'

def ms_tostr(milliseconds):
  if milliseconds is None:
    return None
  
  seconds = milliseconds // 1000
  minutes = seconds // 60

  return f'{minutes}m {seconds % 60}s'

def int_topercent(value, precision):
  ratio = value / precision
  return f'{ratio:.2%}'

def int_totime(ms):
  if ms is None:
    return None
  
  dt = timedelta(milliseconds= ms)
  return str(dt)

def create_embed(account, fields):
  account_id = account["AccountId"]
  embed = discord.Embed()

  for stat_field in fields:
    value = '' if 'DefaultValue' not in stat_field else stat_field['DefaultValue']
    if 'StatId' in stat_field:
      leaderboard = get_leaderboard(DEADLOCKED_API_NAME, account["AppId"], account_id, stat_field['StatId'], stat_field['Custom'])
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

        if 'StatId' in child_field and 'Custom' in child_field:
          leaderboard = get_leaderboard(DEADLOCKED_API_NAME, account["AppId"], account_id, child_field['StatId'], child_field['Custom'])
          value += f' (Rank {leaderboard["Index"]+1})'
      #value += '```'

    embed.add_field(name=stat_field['Name'], value=value, inline=inline)
  
  return embed

def get_phrase(stat_name, account_name):
  return random.choice(constants.StatsPhrases) \
      .replace("{STATNAME}", stat_name) \
      .replace("{USERNAME}", account_name)

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
        },
        {
          'Name': 'Horizon Bolts',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_CURRENT_HORIZON_BOLTS]}'
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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Overall Stats for {account_name}'
  await ctx.respond(content=get_phrase('deadlocked', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Conquest Stats for {account_name}'
  await ctx.respond(content=get_phrase('conquest', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'CTF Stats for {account_name}'
  await ctx.respond(content=get_phrase('capture the flag', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Deathmatch Stats for {account_name}'
  await ctx.respond(content=get_phrase('deathmatch', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'KOTH Stats for {account_name}'
  await ctx.respond(content=get_phrase('king of the hill', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Juggernaut Stats for {account_name}'
  await ctx.respond(content=get_phrase('juggernaut', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Weapon Stats for {account_name}'
  await ctx.respond(content=get_phrase('deadlocked', account["AccountName"]), embed=embed)

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
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_SPLEEF_TIME_PLAYED])}'
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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Spleef Stats for {account_name}'
  await ctx.respond(content=get_phrase('spleef', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Climber Stats for {account_name}'
  await ctx.respond(content=get_phrase('climber', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Gun Game Stats for {account_name}'
  await ctx.respond(content=get_phrase('gun game', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Infected Stats for {account_name}'
  await ctx.respond(content=get_phrase('infected', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Payload Stats for {account_name}'
  await ctx.respond(content=get_phrase('payload', account["AccountName"]), embed=embed)

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
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'SND Stats for {account_name}'
  await ctx.respond(content=get_phrase('search and destroy', account["AccountName"]), embed=embed)

#
async def get_dl_survival_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]
  xp_to_rank = lambda xp : get_dl_skill_level(max(100, min(10000, 100 + (xp) / 5000)))

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
      'Name': 'Orxon',
      'Inline': True,
      'Children': [
        {
          'Name': 'Rank',
          'Value': lambda : f'{xp_to_rank(stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP1_XP]) + (10 * stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP1_PRESTIGE]):.2f}',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP1_XP,
          'Custom': True
        },
        {
          'Name': 'Solo High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP1_SOLO_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP1_SOLO_HIGH_SCORE,
          'Custom': True
        },
        {
          'Name': 'Coop High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP1_COOP_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP1_COOP_HIGH_SCORE,
          'Custom': True
        },
      ]
    },
    {
      'Name': ' ',
      'DefaultValue': ' ',
      'Inline': False
    },
    {
      'Name': 'Mountain Pass',
      'Inline': True,
      'Children': [
        {
          'Name': 'Rank',
          'Value': lambda : f'{xp_to_rank(stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP2_XP]) + (10 * stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP2_PRESTIGE]):.2f}',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP2_XP,
          'Custom': True
        },
        {
          'Name': 'Solo High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP2_SOLO_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP2_SOLO_HIGH_SCORE,
          'Custom': True
        },
        {
          'Name': 'Coop High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP2_COOP_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP2_COOP_HIGH_SCORE,
          'Custom': True
        },
      ]
    },
    {
      'Name': 'Veldin',
      'Inline': True,
      'Children': [
        {
          'Name': 'Rank',
          'Value': lambda : f'{xp_to_rank(stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP3_XP]) + (10 * stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP3_PRESTIGE]):.2f}',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP3_XP,
          'Custom': True
        },
        {
          'Name': 'Solo High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP3_SOLO_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP3_SOLO_HIGH_SCORE,
          'Custom': True
        },
        {
          'Name': 'Coop High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP3_COOP_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP3_COOP_HIGH_SCORE,
          'Custom': True
        },
      ]
    },
    {
      'Name': 'Valix Lighthouse',
      'Inline': True,
      'Children': [
        {
          'Name': 'Rank',
          'Value': lambda : f'{xp_to_rank(stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP4_XP]) + (10 * stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP4_PRESTIGE]):.2f}',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP4_XP,
          'Custom': True
        },
        {
          'Name': 'Solo High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP4_SOLO_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP4_SOLO_HIGH_SCORE,
          'Custom': True
        },
        {
          'Name': 'Coop High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP4_COOP_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP4_COOP_HIGH_SCORE,
          'Custom': True
        },
      ]
    },
    {
      'Name': 'Torval Ruins',
      'Inline': True,
      'Children': [
        {
          'Name': 'Rank',
          'Value': lambda : f'{xp_to_rank(stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP5_XP]) + (10 * stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP5_PRESTIGE]):.2f}',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP5_XP,
          'Custom': True
        },
        {
          'Name': 'Solo High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP5_SOLO_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP5_SOLO_HIGH_SCORE,
          'Custom': True
        },
        {
          'Name': 'Coop High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_SURVIVAL_MAP5_COOP_HIGH_SCORE]} rounds',
          'StatId': constants.CUSTOM_STAT_SURVIVAL_MAP5_COOP_HIGH_SCORE,
          'Custom': True
        },
      ]
    },
    {
      'Name': ' ',
      'DefaultValue': ' ',
      'Inline': False
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
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Survival Stats for {account_name}'
  await ctx.respond(content=get_phrase('survival', account["AccountName"]), embed=embed)

#
async def get_dl_training_stats(ctx: discord.ApplicationContext, account):
  account_id = account["AccountId"]
  account_name = account["AccountName"]
  stats = account["AccountWideStats"]
  stats_custom = account["AccountCustomWideStats"]

  fusion_leaderboard = get_leaderboard(DEADLOCKED_API_NAME, account["AppId"], account_id, constants.CUSTOM_STAT_TRAINING_FUSION_BEST_POINTS, True)
  cycle_leaderboard = get_leaderboard(DEADLOCKED_API_NAME, account["AppId"], account_id, constants.CUSTOM_STAT_TRAINING_CYCLE_BEST_POINTS, True)

  fields = [
    {
      'Name': 'Training Rank',
      #'StatId': constants.CUSTOM_STAT_TRAINING_RANK,
      'Custom': True,
      'Inline': True,
      'Children': [
        {
          'Name': 'Games Played',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_TRAINING_GAMES_PLAYED]}'
        },
        {
          'Name': 'Time Played',
          'Value': lambda : f'{seconds_tostr(stats_custom[constants.CUSTOM_STAT_TRAINING_TIME_PLAYED])}'
        },
        {
          'Name': 'Targets Killed',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_TRAINING_TOTAL_KILLS]}'
        }
      ]
    },
    {
      'Name': 'Fusion Rifle',
      'Inline': True,
      'Children': [
        {
          'Name': 'High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_TRAINING_FUSION_BEST_POINTS]} (#{fusion_leaderboard["Index"]+1})'
        },
        {
          'Name': 'Best Combo',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_TRAINING_FUSION_BEST_COMBO]}'
        },
        {
          'Name': 'Targets Killed',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_TRAINING_FUSION_KILLS]}'
        },
        {
          'Name': 'Accuracy',
          'Value': lambda : f'{int_topercent(stats_custom[constants.CUSTOM_STAT_TRAINING_FUSION_ACCURACY], 100*100)}'
        }
      ]
    },
    {
      'Name': 'Cycle',
      'Inline': True,
      'Children': [
        {
          'Name': 'High Score',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_TRAINING_CYCLE_BEST_POINTS]} (#{cycle_leaderboard["Index"]+1})'
        },
        {
          'Name': 'Best Combo',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_TRAINING_CYCLE_BEST_COMBO]}'
        },
        {
          'Name': 'Total Kills',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_TRAINING_CYCLE_KILLS]}'
        },
        {
          'Name': 'Total Deaths',
          'Value': lambda : f'{stats_custom[constants.CUSTOM_STAT_TRAINING_CYCLE_DEATHS]}'
        },
        {
          'Name': 'Fusion Accuracy',
          'Value': lambda : f'{int_topercent(stats_custom[constants.CUSTOM_STAT_TRAINING_CYCLE_FUSION_ACCURACY], 100*100)}'
        }
      ]
    }
  ]

  embed = create_embed(account, fields)
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'Training Stats for {account_name}'
  await ctx.respond(content=get_phrase('training', account["AccountName"]), embed=embed)


#
async def build_dl_leaderboard(ctx: discord.ApplicationContext, group, stat, leaderboard, additional_embed_title= None, additional_embed_message= None):
  
  lb_str = ''
  pad_str = ' '
  transform_value = lambda x : x
  count = len(leaderboard)

  if 'Accuracy' in stat:
    transform_value = lambda x : int_topercent(x, 100 * 100)
  if 'Best Time' in stat:
    transform_value = lambda x : int_totime(x)

  for i in range(0, count):
    s = f'{i+1}. {leaderboard[i]["AccountName"]}'
    while len(s) < 20:
      s += pad_str
    lb_str += f'{s}{transform_value(leaderboard[i]["StatValue"])}\n'


  embed = discord.Embed()
  embed.add_field(name= f'Top {count}', value=f'```\n{lb_str}```', inline=True)
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'{group} {stat}'
  if additional_embed_title is not None and additional_embed_message is not None:
    embed.add_field(name= additional_embed_title, value= additional_embed_message, inline= False)

  await ctx.respond(content='', embed=embed)


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
  #"Survival": get_dl_survival_stats,
  "Training": get_dl_training_stats,
  "Weapons": get_dl_weapons_stats
}

DEADLOCKED_STATS_ASC = [
  294,
  295,
  302,
  303,
  304,
  305,
  306,
  307,
  353,
  354
]

#
DEADLOCKED_STATS = {
  "Capture the Flag": {
    "Rank": 25,
    "Wins": 26,
    "Losses": 27,
    "Kills": 29,
    "Deaths": 30,
    "Flags Captured": 31,
  },
  "Conquest": {
    "Rank": 18,
    "Wins": 19,
    "Losses": 20,
    "Kills": 22,
    "Deaths": 23,
    "Nodes Taken": 24,
  },
  "Deathmatch": {
    "Rank": 12,
    "Wins": 13,
    "Losses": 14,
    "Kills": 16,
    "Deaths": 17,
  },
  "Gun Game": {
    "Rank": 231,
    "Wins": 232,
    "Losses": 233,
    "Games Played": 234,
    "Kills": 235,
    "Deaths": 236,
    "Demotions": 237,
    "Times Demoted": 238,
    "Times Promoted": 239,
    "Time Played": 240,
  },
  "Infected": {
    "Rank": 211,
    "Wins": 212,
    "Losses": 213,
    "Games Played": 214,
    "Kills": 215,
    "Deaths": 216,
    "Infections": 217,
    "Times Infected": 218,
    "Time Played": 219,
    "Wins as Survivor": 220,
    "Wins as First Infected": 221,
  },
  "Infinite Climber": {
    "Rank": 251,
    "Wins": 252,
    "Losses": 253,
    "Games Played": 254,
    "High Score": 255,
    "Time Played": 256,
  },
  "Juggernaut": {
    "Rank": 39,
    "Wins": 40,
    "Losses": 41,
    "Kills": 43,
    "Deaths": 44,
    "Time": 45,
  },
  "King of the Hill": {
    "Rank": 32,
    "Wins": 33,
    "Losses": 34,
    "Kills": 36,
    "Deaths": 37,
    "Time": 38,
  },
  "Overall": {
    "Rank": 3,
    "Wins": 4,
    "Losses": 5,
    "Disconnects": 6,
    "Kills": 7,
    "Deaths": 8,
    "Games Played": 9,
    "Vehicle Squats": 72,
    "Squats": 73,
  },
  "Payload": {
    "Rank": 171,
    "Wins": 172,
    "Losses": 173,
    "Games Played": 174,
    "Kills": 175,
    "Deaths": 176,
    "Points": 177,
    "Kills while Hot": 178,
    "Kills on Hot": 179,
    "Time Played": 180,
  },
  "Search and Destroy": {
    "Rank": 151,
    "Wins": 152,
    "Losses": 153,
    "Games Played": 154,
    "Kills": 155,
    "Deaths": 156,
    "Plants": 157,
    "Defuses": 158,
    "Ninja Defuses": 159,
    "Wins Attacking": 160,
    "Wins Defending": 161,
    "Time Played": 162,
  },
  "Spleef": {
    "Rank": 191,
    "Wins": 192,
    "Losses": 193,
    "Games Played": 194,
    "Rounds Played": 195,
    "Points": 196,
    "Time Played": 197,
    "Boxes Broken": 198,
  },
  "Survival General": {
    "Rank": 271,
    "XP": 291,
    # "Orxon Solo High Score": 278,
    # "Orxon Solo 50 Rounds Best Time": 302,
    # "Orxon Coop High Score": 279,
    # "Orxon Coop 50 Rounds Best Time": 303,
    # "Mountain Pass Solo High Score": 280,
    # "Mountain Pass Solo 50 Rounds Best Time": 304,
    # "Mountain Pass Coop High Score": 281,
    # "Mountain Pass Coop 50 Rounds Best Time": 305,
    # "Veldin Solo High Score": 282,
    # "Veldin Solo 50 Rounds Best Time": 306,
    # "Veldin Coop High Score": 296,
    # "Veldin Coop 50 Rounds Best Time": 307,
    # "Valix Solo High Score": 292,
    # "Valix Solo 50 Rounds Best Time": 294,
    # "Valix Coop High Score": 293,
    # "Valix Coop 50 Rounds Best Time": 295,
    # "Torval Solo High Score": 351,
    # "Torval Solo 50 Rounds Best Time": 353,
    # "Torval Coop High Score": 352,
    # "Torval Coop 50 Rounds Best Time": 354,
    "Games Played": 272,
    "Time Played": 273,
    "Kills": 274,
    "Deaths": 275,
    "Revives": 276,
    "Times Revived": 277,
    #"Times Rolled Mystery Box": 292,
    #"Times Activated Demon Bell": 293,
    #"Times Activated Power": 294,
    #"Tokens Used On Gates": 295,
    "Wrench Kills": 283,
    "Dual Viper Kills": 284,
    "Magma Cannon Kills": 285,
    "Arbiter Kills": 286,
    "Fusion Rifle Kills": 287,
    "Mine Launcher Kills": 288,
    "B6 Obliterator Kills": 289,
    "Scorpion Flail Kills": 290,
  },
  "Survival High Scores": {
    "Orxon Solo High Score": 278,
    "Orxon Solo 50 Rounds Best Time": 302,
    "Orxon Coop High Score": 279,
    "Orxon Coop 50 Rounds Best Time": 303,
    "Mountain Pass Solo High Score": 280,
    "Mountain Pass Solo 50 Rounds Best Time": 304,
    "Mountain Pass Coop High Score": 281,
    "Mountain Pass Coop 50 Rounds Best Time": 305,
    "Veldin Solo High Score": 282,
    "Veldin Solo 50 Rounds Best Time": 306,
    "Veldin Coop High Score": 296,
    "Veldin Coop 50 Rounds Best Time": 307,
    "Valix Solo High Score": 292,
    "Valix Solo 50 Rounds Best Time": 294,
    "Valix Coop High Score": 293,
    "Valix Coop 50 Rounds Best Time": 295,
    "Torval Solo High Score": 351,
    "Torval Solo 50 Rounds Best Time": 353,
    "Torval Coop High Score": 352,
    "Torval Coop 50 Rounds Best Time": 354,
  },
  "Training": {
    "Games Played": 312,
    "Time Played": 313,
    "Total Kills": 314,
    "Fusion Rifle: High Score": 315,
    "Fusion Rifle: Best Combo": 321,
    "Fusion Rifle: Total Kills": 317,
    "Fusion Rifle: Accuracy": 320,
    "Cycle: High Score": 322,
    "Cycle: Best Combo": 323,
    "Cycle: Total Kills": 324,
    "Cycle: Total Deaths": 325,
    "Cycle: Fusion Accuracy": 328,
  },
  "Weapons": {
    "Wrench Kills": 46,
    "Wrench Deaths": 47,
    "Dual Viper Kills": 49,
    "Dual Viper Deaths": 50,
    "Magma Cannon Kills": 52,
    "Magma Cannon Deaths": 53,
    "Arbiter Kills": 55,
    "Arbiter Deaths": 56,
    "Fusion Rifle Kills": 58,
    "Fusion Rifle Deaths": 59,
    "Hunter Mine Kills": 61,
    "Hunter Mine Deaths": 62,
    "B6 Obliterator Kills": 64,
    "B6 Obliterator Deaths": 65,
    "Scorpion Flail Kills": 67,
    "Scorpion Flail Deaths": 68,
    "Roadkills": 71,
    "Holoshield Kills": 74,
    "Holoshield Deaths": 75,
  },
}

#
async def get_dl_stats(ctx: discord.ApplicationContext, stat: str, name: str):
  try:
    account = get_account(DEADLOCKED_API_NAME, APPID_DEADLOCKED, name)
    if stat in DEADLOCKED_GET_STATS_CHOICES:
      await DEADLOCKED_GET_STATS_CHOICES[stat](ctx, account)
    else:
      await ctx.respond('Invalid stat.')
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Account `{name}` not found.')
  
#
async def get_dl_leaderboard(ctx: discord.ApplicationContext, group: str, stat: str):
  try:
    if group in DEADLOCKED_STATS:
      group_values = DEADLOCKED_STATS[group]
      if stat in group_values:
        stat_id = group_values[stat]
        if stat_id > 100:
          orderAsc = stat_id in DEADLOCKED_STATS_ASC
          leaderboard = get_leaderboard_top10(DEADLOCKED_API_NAME, APPID_DEADLOCKED, stat_id - 100, custom=True, orderAsc= orderAsc)
        else:
          leaderboard = get_leaderboard_top10(DEADLOCKED_API_NAME, APPID_DEADLOCKED, stat_id, custom=False)

        await build_dl_leaderboard(ctx, group, stat, leaderboard)
    else:
      await ctx.respond('Invalid stat.')
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Leaderboard `{leaderboard}` not found.')

#
async def get_dl_scavenger_hunt_leaderboard(ctx: discord.ApplicationContext):
  try:
    prefix = ''
    now = datetime.datetime.now().astimezone(datetime.timezone.utc)
    begin_date, end_date = get_scavenger_hunt_dates(DEADLOCKED_API_NAME, APPID_DEADLOCKED)
    if begin_date is None or end_date is None:
      await ctx.respond(content="Looks like there is no scavenger hunt! Keep an eye out in <#936415070299226152> for the next one!")
      return
    
    if now < begin_date:
      await ctx.respond(content=f'The hunt begins {get_discord_string_from_date(begin_date)}!')
      return
    
    if now > end_date:
      prefix = 'Past '

    leaderboard = get_leaderboard_top(DEADLOCKED_API_NAME, APPID_DEADLOCKED, constants.CUSTOM_STAT_CURRENT_HORIZON_BOLTS+1, 10, custom=True)
    await build_dl_leaderboard(ctx
                               , f'{prefix}Scavenger Hunt', 'Horizon Bolts'
                               , leaderboard
                               , additional_embed_title='Event Dates'
                               , additional_embed_message=f'{get_discord_string_from_date(begin_date)} - {get_discord_string_from_date(end_date)}')
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Leaderboard `{leaderboard}` not found.')


##############################################
#                     UYA                    #
##############################################
async def build_uya_leaderboard(ctx: discord.ApplicationContext, group, stat, leaderboard, additional_embed_title= None, additional_embed_message= None):
  
  lb_str = ''
  pad_str = ' '
  transform_value = lambda x : x
  count = len(leaderboard)

  for i in range(0, count):
    s = f'{i+1}. {leaderboard[i]["AccountName"]}'
    while len(s) < 24:
      s += pad_str
    lb_str += f'{s}{transform_value(leaderboard[i]["StatValue"])}\n'

  embed = discord.Embed()
  embed.add_field(name= f'Top {count}', value=f'```\n{lb_str}```', inline=True)
  # embed.set_thumbnail(url=constants.UYA_ICON_URL)
  embed.title = f'{group} {stat}'

  if additional_embed_title is not None and additional_embed_message is not None:
    embed.add_field(name= additional_embed_title, value= additional_embed_message, inline= False)

  await ctx.respond(content='', embed=embed)


#
async def get_uya_scavenger_hunt_leaderboard(ctx: discord.ApplicationContext):
  try:
    prefix = ''
    now = datetime.datetime.now().astimezone(datetime.timezone.utc)
    begin_date, end_date = get_scavenger_hunt_dates(UYA_API_NAME, APPID_UYA)
    if begin_date is None or end_date is None:
      await ctx.respond(content="Looks like there is no scavenger hunt! Keep an eye out in <#936415070299226152> for the next one!")
      return
    
    if now < begin_date:
      await ctx.respond(content=f'The hunt begins {get_discord_string_from_date(begin_date)}!')
      return
    
    if now > end_date:
      prefix = 'Past '

    leaderboard = get_leaderboard_top(UYA_API_NAME, APPID_UYA, constants.CUSTOM_STAT_CURRENT_HORIZON_BOLTS+1, 10, custom=True)
    await build_uya_leaderboard(ctx
                               , f'{prefix}Scavenger Hunt', 'Horizon Bolts'
                               , leaderboard
                               , additional_embed_title='Event Dates'
                               , additional_embed_message=f'{get_discord_string_from_date(begin_date)} - {get_discord_string_from_date(end_date)}')
  except Exception as e:
    print(traceback.format_exc())
    await ctx.respond(f'Leaderboard `{leaderboard}` not found.')
