import os
import string
import discord
import asyncio
import urllib.parse
import random
import constants
import traceback
from datetime import datetime
import aiohttp
import json
import base64
from datetime import timedelta

timelimit_map = {
  "no_time_limit": "None",
  "5_minutes": "5 minutes",
  "10_minutes": "10 minutes",
  "15_minutes": "15 minutes",
  "20_minutes": "20 minutes",
  "25_minutes": "25 minutes",
  "30_minutes": "30 minutes",
  "35_minutes": "35 minutes"
}

uya_map_map = {
  "Bakisi_Isle": "Bakisi Isles",
  "Hoven_Gorge": "Hoven Gorge",
  "Outpost_x12": "Outpost X12",
  "Korgon_Outpost": "Korgon Outpost",
  "Metropolis": "Metropolis",
  "Blackwater_City": "Blackwater City",
  "Command_Center": "Command Center",
  "Aquatos_Sewers": "Aquatos Sewers",
  "Blackwater_Dox": "Blackwater Dox",
  "Marcadia_Palace": "Marcadia Palace"
}


class UYAManager:
  def __init__(self, client, config):
    self._client = client
    self._config = config

    if config['UYA']['ServerUrl']:
      self._http_session = aiohttp.ClientSession(base_url=config['UYA']['ServerUrl'])
      
      client.loop.create_task(self.uya_players_online_task(client, config))

# background task that polls api and creates/updates respective smoke messages in discord
  async def uya_players_online_task(self, client: discord.Client, config):
    await client.wait_until_ready()
    channel: discord.TextChannel = client.get_channel(self._config['UYA']["PlayersOnline"]['ChannelId'])
    message: discord.Message = None
    embed: discord.Embed = discord.Embed()

    # try and get message to reuse
    message_id = self._config['UYA']['PlayersOnline']["MessageId"]
    if message_id != 0:
      message = await channel.fetch_message(message_id)

    while not client.is_closed():
      if not client.is_ws_ratelimited():
        try:
          embed = await self._build_players_online_embed(embed)
          if message is None:
            message = await channel.send(content= None, embed= embed)
          else:
            await message.edit(content= None, embed= embed)

        except Exception as e:
          print(traceback.format_exc())
      await asyncio.sleep(3)

  async def _build_players_online_embed(self, embed):
      # base
    embed.color = 7
    embed.description = ''
    embed.title = f'Up Your Arsenal Server'
    embed.timestamp = datetime.now()
    embed.clear_fields()
    embed.set_footer(text= 'Last Updated')

    players = await self.get_players_endpoint()
    games = await self.get_games_endpoint()
    print("ENDPOINT!")
    if len(players) == 0:
      players_val = 'No Players Online'
    else:
      players_val = ''
      for player in players:
        print(player['username'])
        if player["username"].strip().lower().startswith("cpu"):
          print("FOUND CPU!")
          continue
        this_player = f'[{player["region"]}] {player["username"]}'
        if player['clan_tag'] != '':
          this_player += f' [{player["clan_tag"]}]'
        this_player += '\n'
        players_val += this_player
      players_val = f'```{players_val.strip()}```'
    
    all_clans = set()
    if len(players) == 0:
      clans_val = 'No Clans Online'
    else:
      for player in players:
        if player['clan'] == '':
          continue
        all_clans.add((player['clan'], player['clan_tag']))
    if len(all_clans) == 0:
      clans_val = 'No Clans Online'
    else:
      clans_val = ''
      for clan_name, clan_tag in all_clans:
        clans_val += f'{clan_name} [{clan_tag}]'
        clans_val += '\n'
      clans_val = '```' + clans_val.strip() + '```'

    embed.add_field(name= f'Players Online - {len(players)}', value=players_val, inline= False)
    embed.add_field(name= f'Clans Online - {len(all_clans)}', value=clans_val, inline= False)
    embed.add_field(name= '\u200B', value= 'Active Games:', inline= False)

    if len(games) == 0:
      embed.add_field(name= f'No Games', value=None, inline= False)
    else:
      for game in games:
        games_val = ''
        games_val += game['game_mode'] + ' (' + game['submode'] + ') ' + '@ ' + uya_map_map[game['map']] + '\n'
        games_val += f'Time Limit: {timelimit_map[game["game_length"]]}\n\n'
        games_val += 'Players:\n'
        for player in game['players']:
          games_val += f'  {player["username"]}\n'
        games_val += '\n\n'
        games_val = '```' + games_val.strip() + '```'

        game_name = base64.b64decode(game["game_name"]).decode('utf-8')
        game_name = game_name.split("000000280000")[0].strip()
        num_players = len(game['players'])

        if game['started_date'] == '':
          time_elapsed = ''
        else:
          td = timedelta(seconds=datetime.now().timestamp() - game['started_date'])
          td = str(td).split(".")[0]
          time_elapsed = '@' + td

        embed.add_field(name= f'{game_name} - ({num_players}/8) {time_elapsed}', value=games_val, inline= False)

      #time_started: datetime = datetime.strptime(game["GameStartDt"][:26], '%Y-%m-%dT%H:%M:%S.%f') if in_game and game["GameStartDt"] is not None else None
      #seconds_since_started: datetime = (datetime.utcnow() - time_started).total_seconds() if time_started is not None else None


    return embed
    # filter players by appid and server
    
  async def get_players_endpoint(self):
    async with self._http_session.get('/robo/players') as response:
      html = await response.text()
      resp = json.loads(html)
      return resp
    
  async def get_games_endpoint(self):
    async with self._http_session.get('/robo/games') as response:
      html = await response.text()
      resp = json.loads(html)
      return resp


  async def alt(self, ctx: discord.ApplicationContext, username):
    embed = discord.Embed()    

    async with self._http_session.get(f'/robo/alts/{username}') as response:
      html = await response.text()
      resp = json.loads(html)
      if resp == '[]':
        resp = []

    if len(resp) == 0 :
      val = 'No Accounts found!'
    else:
      val = '```\n'
      val += ', '.join(resp)
      val += '```'

    val = val[:1000]

    embed.add_field(name=f'Found {len(resp)} accounts!', value=val, inline=False)


    embed.title = f'Alt Accounts for {username}'
    await ctx.respond(content='', embed=embed)


  async def clan(self, ctx: discord.ApplicationContext, name):
    embed = discord.Embed()    

    async with self._http_session.get(f'/robo/clans/name/{name}') as response:
      html = await response.text()
      resp = json.loads(html)
      if resp == '{}':
        resp = {}

    if resp == {}:
      embed.add_field(name=f'No Clans Found', value='No Clans Found', inline=False)
    else:
      embed.add_field(name=f'Name', value=resp['clan_name'], inline=False)
      embed.add_field(name=f'Leader', value=resp['leader_account_name'], inline=False)
      embed.add_field(name=f'Kills', value=resp['kills'], inline=False)
      embed.add_field(name=f'Deaths', value=resp['deaths'], inline=False)
      embed.add_field(name=f'Wins', value=resp['wins'], inline=False)
      embed.add_field(name=f'Losses', value=resp['losses'], inline=False)
      embed.add_field(name=f'Members', value='```\n' + '\n'.join(resp['members']) + '```', inline=False)

    embed.title = f'Clan Info'
    await ctx.respond(content='', embed=embed)
