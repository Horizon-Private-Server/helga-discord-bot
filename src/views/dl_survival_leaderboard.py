import os
import discord
import requests
import urllib.parse
import traceback
import constants
from datetime import timedelta
from discord.ext import commands
from stats import create_embed, get_phrase, int_totime, int_topercent
from mediusapi import authenticate, get_account, APPID_DEADLOCKED, DEADLOCKED_API_NAME, headers

TOTAL_NAME = "Total"
OVERALL_NAME = "Overall"

API_MAP_LEADERBOARDS = {
    "Rank": "Rank",
    "Completion": "Completion",
    "Solo High Score": "SoloBestRound",
    "Solo Round 50 Best Time": "SoloBestTime50",
    "Coop High Score": "CoopBestRound",
    "Coop Round 50 Best Time": "CoopBestTime50",
}

API_TOTAL_LEADERBOARDS = {
    "Completion": "Completion",
    "Games Played": "GamesPlayed",
    "Time Played": "TimePlayed",
    "Kills": "Kills",
    "Deaths": "Deaths",
    "Revives": "Revives",
    "Times Revived": "TimesRevived",
    "Wrench Kills": "WrenchKills",
    "Dual Viper Kills": "DualViperKills",
    "Magma Cannon Kills": "MagmaCannonKills",
    "Arbiter Kills": "ArbiterKills",
    "Fusion Rifle Kills": "FusionKills",
    "Hunter Mine Launcher Kills": "MineLauncherKills",
    "B6 Obliterator Kills": "B6Kills",
    "Holoshield Kills": "HoloshieldKills",
    "Scorpion Flail Kills": "FlailKills",
}

survival_maps = []

class DLSurvivalLeaderboardForm(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=None)
        self.author = author
        
        # get maps
        maps = survival_get_maps()
        options = [item["Name"] for item in maps]
        options.insert(0, TOTAL_NAME)

        # 1. Setup the First Dropdown (Category)
        self.category_select = discord.ui.Select(
            placeholder="Step 1: Choose a Category",
            options=[discord.SelectOption(label=k) for k in options],
            row=0 # Explicitly set row
        )
        self.category_select.callback = self.category_callback
        
        # 2. Setup the Second Dropdown (Sub-category)
        # We start it as "disabled" or with a placeholder until a category is picked
        self.sub_select = discord.ui.Select(
            placeholder="Step 2: Waiting for category...",
            options=[discord.SelectOption(label="Select a category first", value="none")],
            disabled=True,
            row=1
        )
        self.sub_select.callback = self.sub_callback

        # 3. Prev Page Button (Row 2)
        self.prev_btn = discord.ui.Button(
            label="<", style=discord.ButtonStyle.primary, disabled=True, row=2
        )
        self.prev_btn.callback = self.prev_callback

        # 4. Cancel Button (Row 2)
        self.next_btn = discord.ui.Button(
            label=">", style=discord.ButtonStyle.primary, disabled=True, row=2
        )
        self.next_btn.callback = self.next_callback

        # Add them to the view
        self.add_item(self.category_select)
        self.add_item(self.sub_select)
        self.add_item(self.prev_btn)
        self.add_item(self.next_btn)
        
        # init page num
        self.page = 1
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        This runs before any button or dropdown callback.
        If it returns False, the callback never runs.
        """
        if interaction.user != self.author:
            # Send a private (ephemeral) message to the intruder
            await interaction.response.send_message(
                "❌ This menu is not for you! Run the command yourself to use it.", 
                ephemeral=True
            )
            return False
        return True

    async def category_callback(self, interaction: discord.Interaction):
        # Get the selected category
        category = self.category_select.values[0]

        # --- THE FIX: Maintain selection state ---
        for option in self.category_select.options:
            # If this option matches what the user picked, set it to True, else False
            option.default = (option.label == category)

        # Update the second dropdown's properties
        self.sub_select.disabled = False
        self.sub_select.placeholder = f"Step 2: Pick a {category} leaderboard"
        
        # get options
        options = API_TOTAL_LEADERBOARDS.keys()
        if category != TOTAL_NAME:
          options = API_MAP_LEADERBOARDS.keys()

        # Map the new options from our data dictionary
        self.sub_select.options = [
            discord.SelectOption(label=item) for item in options
        ]
        
        # Lock page buttons
        self.prev_btn.disabled = True
        self.next_btn.disabled = True

        # Edit the message with the updated view
        await interaction.response.edit_message(
            content=f"Category: **{category}**. Now select a specific leaderboard:", 
            view=self
        )

    async def sub_callback(self, interaction: discord.Interaction):
        category = self.category_select.values[0]
        stat = self.sub_select.values[0]

        # --- Maintain selection state ---
        for option in self.category_select.options:
            option.default = (option.label == category)
        for option in self.sub_select.options:
            option.default = (option.label == stat)

        # Update the second dropdown's properties
        self.sub_select.disabled = False
        self.sub_select.placeholder = f"Step 2: Pick a {category} leaderboard"
      
        # Unlock page buttons
        self.prev_btn.disabled = False
        self.next_btn.disabled = False

        # Reset page num
        self.page = 1

        # get leaderboard
        await self.update_leaderboard(interaction)

    async def prev_callback(self, interaction: discord.Interaction):
        if self.page > 1:
           self.page -= 1

        await self.update_leaderboard(interaction)

    async def next_callback(self, interaction: discord.Interaction):
        self.page += 1
        await self.update_leaderboard(interaction)

    async def update_leaderboard(self, interaction: discord.Interaction):
        category = self.category_select.values[0]
        stat = self.sub_select.values[0]
        embed = None
       
        # get leaderboard
        if category == TOTAL_NAME:
            lb = survival_get_leaderboard(API_TOTAL_LEADERBOARDS[stat], page=self.page, page_size=10)
            embed = await survival_build_leaderboard(stat, lb, self.page, 10)
        else:
            lb = survival_get_map_leaderboard(category, API_MAP_LEADERBOARDS[stat], page=self.page, page_size=10)
            embed = await survival_build_map_leaderboard(category, stat, lb, self.page, 10)
      
        # Edit the message with the updated view
        await interaction.response.edit_message(
            content=f"",
            embed=embed,
            view=self
        )

class DLSurvivalStatsForm(discord.ui.View):
    def __init__(self, author: discord.Member, name: str):
        super().__init__(timeout=None)
        self.author = author
            
        # get user
        account = get_account(DEADLOCKED_API_NAME, APPID_DEADLOCKED, name)
        self.account_id = account["AccountId"]
        self.account_name = account["AccountName"]

        # get maps
        maps = survival_get_maps()
        options = [item["Name"] for item in maps]
        options.insert(0, OVERALL_NAME)

        # 1. Setup the First Dropdown (Category)
        self.category_select = discord.ui.Select(
            placeholder="Step 1: Choose a Category",
            options=[discord.SelectOption(label=k) for k in options],
            row=0 # Explicitly set row
        )
        self.category_select.callback = self.category_callback
        self.add_item(self.category_select)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        This runs before any button or dropdown callback.
        If it returns False, the callback never runs.
        """
        if interaction.user != self.author:
            # Send a private (ephemeral) message to the intruder
            await interaction.response.send_message(
                "❌ This menu is not for you! Run the command yourself to use it.", 
                ephemeral=True
            )
            return False
        return True

    async def category_callback(self, interaction: discord.Interaction):
        # Get the selected category
        category = self.category_select.values[0]

        # --- Maintain selection state ---
        for option in self.category_select.options:
            option.default = (option.label == category)

        await self.update_embed(interaction)

    async def update_embed(self, interaction: discord.Interaction):
        category = self.category_select.values[0]
        embed = None
       
        # get stats
        if category == OVERALL_NAME:
            embed = await self.build_overall_stats()
        else:
            embed = await self.build_map_stats(category)

        # Edit the message with the updated view
        await interaction.response.edit_message(
            content=f"",
            embed=embed,
            view=self
        )

    async def build_overall_stats(self):
      try:
        account = get_account(DEADLOCKED_API_NAME, APPID_DEADLOCKED, self.account_name)
        stats = survival_get_stats(self.account_id)
        
        gap = {
            'Name': ' ',
            'DefaultValue': ' ',
            'Inline': False
        }
        fields = [
          {
            'Name': 'General',
            'Inline': True,
            'Children': [
              {
                'Name': 'Completion Leaderboard Ranking',
                'Value': lambda : f'#{stats["Ranking"]}'
              },
              {
                'Name': 'Total Percent Complete',
                'Value': lambda : f'{int_topercent(stats["TotalPercentCompleted"], 1)}'
              },
              {
                'Name': 'Games Played',
                'Value': lambda : f'{stats["GamesPlayed"]}'
              },
              {
                'Name': 'Time Played',
                'Value': lambda : f'{int_totime(stats["TimePlayedMs"])}'
              },
              {
                'Name': 'Kills',
                'Value': lambda : f'{stats["Kills"]}'
              },
              {
                'Name': 'Deaths',
                'Value': lambda : f'{stats["Deaths"]}'
              },
              {
                'Name': 'Revives',
                'Value': lambda : f'{stats["Revives"]}'
              },
              {
                'Name': 'Revived',
                'Value': lambda : f'{stats["TimesRevived"]}'
              }
            ]
          },
          gap,
          {
            'Name': 'Weapons',
            'Inline': True,
            'Children': [
              {
                'Name': 'Wrench Kills',
                'Value': lambda : f'{stats["WrenchKills"]}'
              },
              {
                'Name': 'Dual Viper Kills',
                'Value': lambda : f'{stats["DualViperKills"]}'
              },
              {
                'Name': 'Magma Cannon Kills',
                'Value': lambda : f'{stats["MagmaCannonKills"]}'
              },
              {
                'Name': 'Arbiter Kills',
                'Value': lambda : f'{stats["ArbiterKills"]}'
              },
              {
                'Name': 'Fusion Rifle Kills',
                'Value': lambda : f'{stats["FusionRifleKills"]}'
              },
              {
                'Name': 'Mine Launcher Kills',
                'Value': lambda : f'{stats["MineLauncherKills"]}'
              },
              {
                'Name': 'B6 Obliterator Kills',
                'Value': lambda : f'{stats["B6Kills"]}'
              },
              {
                'Name': 'Holoshield Kills',
                'Value': lambda : f'{stats["HoloshieldKills"]}'
              },
              {
                'Name': 'Scorpion Flail Kills',
                'Value': lambda : f'{stats["ScorpionFlailKills"]}'
              }
            ]
          }
        ]
 
        embed = create_embed(account, fields)
        embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
        embed.title = f'Survival Stats for {self.account_name}'
        return embed
      except Exception as e:
        print(traceback.format_exc())
        return None

    async def build_map_stats(self, map_name: str):
      try:
        account = get_account(DEADLOCKED_API_NAME, APPID_DEADLOCKED, self.account_name)
        map_stats = survival_get_map_stats(self.account_id, map_name)
        gambit_stats = map_stats["Gambits"]

        gap = {
            'Name': ' ',
            'DefaultValue': ' ',
            'Inline': False
        }

        # base map stats
        fields = [
          {
            'Name': map_name,
            'Inline': True,
            'Children': [
              {
                'Name': 'Prestige',
                'Value': lambda s=map_stats : f'{s["Prestige"] or 0}',
              },
              {
                'Name': 'Xp',
                'Value': lambda s=map_stats : f'{int_topercent(min(1, (s["Xp"] or 0) / 49500000), 1)}',
              },
              {
                'Name': f'Solo High Score (Rank {map_stats["SoloRoundRanking"]})' if map_stats["SoloRoundRanking"] else 'Solo High Score',
                'Value': lambda s=map_stats : f'{s["SoloRound"] or 0} rounds',
              },
              {
                'Name': f'Solo Fastest 50 Rounds (Rank {map_stats["Solo50Ranking"]})' if map_stats["Solo50Ranking"] else 'Solo Fastest 50 Rounds',
                'Value': lambda s=map_stats : f'{int_totime(s["Solo50"]) or "---"}',
              },
              {
                'Name': 'Coop High Score',
                'Value': lambda s=map_stats : f'{s["CoopRound"] or 0} rounds',
              },
              {
                'Name': 'Coop Fastest 50 Rounds',
                'Value': lambda s=map_stats : f'{int_totime(s["Coop50"]) or "---"}',
              },
            ]
          }
        ]

        # completion
        fields.append(gap)
        completionRow = {
          'Name': f'Completion: {int_topercent(map_stats["PercentCompleted"], 1)}',
          'Inline': True,
          'Children': [
            {
              'Name': '~~50 Rounds (No Gambits)~~' if ((map_stats["SoloRound"] or 0) >= 50 or (map_stats["CoopRound"] or 0) >= 50) else '50 Rounds (No Gambits)',
              'Value': lambda s=map_stats : f'{max(s["SoloRound"] or 0, s["CoopRound"] or 0)} rounds'
            }
          ]
        }

        # add gambits
        for gambit in gambit_stats:
          completionRow['Children'].append({
            'Name': f'~~Gambit {gambit["Gambit"]}~~' if gambit["Completed"] == True else f'Gambit {gambit["Gambit"]}',
            'Value': lambda s=gambit : f'{s["BestRound"] or 0} rounds'
          })

        fields.append(completionRow)
      
        embed = create_embed(account, fields)
        embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
        embed.title = f'Survival Stats for {self.account_name}'
        return embed
      except Exception as e:
        print(traceback.format_exc())
        return None

#
async def survival_build_leaderboard(stat, leaderboard, page, page_size, additional_embed_title= None, additional_embed_message= None):
  
  lb_str = ''
  pad_str = ' '
  transform_value = lambda x : x
  count = len(leaderboard)
  index = (page-1)*page_size

  if 'Time Played' in stat or 'Best Time' in stat:
    transform_value = lambda x : int_totime(x)
  if 'Completion' in stat:
     transform_value = lambda x : f'{x}%'

  for i in range(0, count):
    s = f'{leaderboard[i]["Index"]}. {leaderboard[i]["AccountName"]}'
    while len(s) < 20:
      s += pad_str
    lb_str += f'{s}{transform_value(leaderboard[i]["StatValue"])}\n'


  embed = discord.Embed()
  embed.add_field(name= f'Top {index+1} - {index+page_size}', value=f'```\n{lb_str}```', inline=True)
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'{TOTAL_NAME} {stat}'
  if additional_embed_title is not None and additional_embed_message is not None:
    embed.add_field(name= additional_embed_title, value= additional_embed_message, inline= False)

  return embed

#
async def survival_build_map_leaderboard(group, stat, leaderboard, page, page_size, additional_embed_title= None, additional_embed_message= None):
  
  lb_str = ''
  pad_str = ' '
  transform_value = lambda x : x
  count = len(leaderboard)
  index = (page-1)*page_size

  if 'Best Time' in stat:
    transform_value = lambda x : int_totime(x)
  if 'Completion' in stat:
     transform_value = lambda x : f'{x}%'

  for i in range(0, count):
    s = f'{leaderboard[i]["Index"]}. {leaderboard[i]["AccountNames"]}'
    while len(s) < 20:
      s += pad_str
    lb_str += f'{s}{transform_value(leaderboard[i]["StatValue"])}\n'


  embed = discord.Embed()
  embed.add_field(name= f'Top {index+1} - {index+page_size}', value=f'```\n{lb_str}```', inline=True)
  embed.set_thumbnail(url=constants.DEADLOCKED_DREADZONE_ICON_URL)
  embed.title = f'{group} {stat}'
  if additional_embed_title is not None and additional_embed_message is not None:
    embed.add_field(name= additional_embed_title, value= additional_embed_message, inline= False)

  return embed

#
def survival_get_maps():
  global survival_maps
  if len(survival_maps) > 0:
     return survival_maps
  
  survival_maps = survival_get("getMaps")
  return survival_maps

#
def survival_get_map_leaderboard(map_name, leaderboard, page = 1, page_size = 10):
  maps = survival_get_maps()
  map_key = ""
  for map in maps:
        if map["Name"] == map_name:
            map_key = map["Filename"]

  if map_key is None:
     return None
  
  map_encoded = urllib.parse.quote(map_key)
  lb_encoded = urllib.parse.quote(leaderboard)
  return survival_get(f"getMapLeaderboard/{map_encoded}/{lb_encoded}?Page={page}&PageSize={page_size}")

#
def survival_get_leaderboard(leaderboard, page = 1, page_size = 10):
  lb_encoded = urllib.parse.quote(leaderboard)
  return survival_get(f"getLeaderboard/{lb_encoded}?Page={page}&PageSize={page_size}")

#
def survival_get_stats(account_id):
  return survival_get(f"getAccountStats?AccountId={account_id}")

#
def survival_get_map_stats(account_id, map_name):
  maps = survival_get_maps()
  map_key = ""
  for map in maps:
        if map["Name"] == map_name:
            map_key = map["Filename"]

  if map_key is None:
     return None
  
  map_encoded = urllib.parse.quote(map_key)
  return survival_get(f"getAccountMapStats?AccountId={account_id}&MapFilename={map_encoded}")

#
def survival_get(endpoint):
  global headers
  api = DEADLOCKED_API_NAME
  if api not in headers:
    authenticate(api)
  
  route = f"Survival/{endpoint}"
  response = requests.get(os.getenv(f'MIDDLEWARE_ENDPOINT_{api}') + route, headers=headers[api], verify=False)

  if response.status_code == 200:
    return response.json()
  elif response.status_code == 401:
    print("Got 401 Unauthorized. Repulling token")
    authenticate(api)
    return "Got 401. Try again"
  elif response.status_code == 404:
    return f"{api} survival_get {route} not found"
  else:
    raise ValueError(f"{route} returned {response.status_code}")

