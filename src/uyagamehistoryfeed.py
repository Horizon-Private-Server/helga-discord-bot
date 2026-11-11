import json
import time
import asyncio
import traceback
import requests
import discord
from datetime import datetime, timedelta
from tabulate import tabulate

from config import config_get, config_save
from mediusapi import get_recent_games, get_game_history_by_date, get_account_basic, UYA_API_NAME, APPID_UYA
from uya_parsers import mapParser, timeParser, gamerulesParser

# Posts an embed to a Discord webhook for every UYA game that finishes, read straight from the middleware.
# Config (config.json -> "UyaGameHistoryFeed"):
#   WebhookUrl: Discord webhook URL. Feature is disabled when empty.
#   StartDate:  ISO date/datetime (UTC). Every game that ended after this is posted, oldest first.
#               Also used as the persistent cursor: after each post it is advanced to that game's
#               end time and saved, so restarts never re-post. When empty it is set to "now".

POLL_INTERVAL = 60            # seconds between middleware polls
POST_DELAY = 1                # seconds between webhook posts (webhook rate limit)
RECENT_GAMES_MAX_MINUTES = 600  # middleware caps getRecentGames at 600 minutes

# Index into the (PostWideStats - PreWideStats) diff list for each player.
# Position 0 is an unused slot, so the index equals the stat id (matches the tracker's uya_vanilla_stats_map).
STAT_WINS = 2
STAT_KILLS = 5
STAT_DEATHS = 6
STAT_BASE_DMG = 9
STAT_NODES = 10
STAT_FLAG_CAPTURES = 62

RED, GREEN, BLUE = 16711680, 65280, 255
COLOR_MAP = {'CTF': BLUE, 'Siege': RED, 'Deathmatch': GREEN}

_username_cache = {}


def parse_dt(value: str) -> datetime:
  # .NET emits 7 fractional digits; python's fromisoformat handles at most 6
  return datetime.fromisoformat(value[:26]).replace(tzinfo=None)


def get_username(account_id) -> str:
  if account_id not in _username_cache:
    account = get_account_basic(UYA_API_NAME, account_id)
    _username_cache[account_id] = account["AccountName"] if account else "UNKNOWN"
  return _username_cache[account_id]


def fetch_games_since(cursor: datetime) -> list:
  """Return all games with GameEndDt > cursor, oldest first."""
  now = datetime.utcnow()
  minutes = int((now - cursor).total_seconds() / 60) + 5

  if minutes <= RECENT_GAMES_MAX_MINUTES:
    games = get_recent_games(UYA_API_NAME, APPID_UYA, minutes) or []
  else:
    # Page backwards from now until we pass the cursor
    games = []
    last_game_end_dt = now.isoformat()
    while True:
      page = get_game_history_by_date(UYA_API_NAME, APPID_UYA, last_game_end_dt)
      if not page or not page.get("Games"):
        break
      games += page["Games"]
      if parse_dt(page["Games"][-1]["GameEndDt"]) <= cursor:
        break
      last_game_end_dt = page["NextCursor"]

  games = [g for g in games if g.get("GameEndDt") and parse_dt(g["GameEndDt"]) > cursor]
  return sorted(games, key=lambda g: parse_dt(g["GameEndDt"]))


def build_payload(game: dict):
  """Build the webhook payload for a game, or None if the game should not be posted."""
  metadata = game.get("Metadata") or {}
  if isinstance(metadata, str):
    metadata = json.loads(metadata)

  pre = metadata.get("PreWideStats", {}).get("Players", {})
  post = metadata.get("PostWideStats", {}).get("Players", {})

  players = []
  for account_id, pre_stats in pre.items():
    if account_id not in post:
      continue
    diff = [p - q for p, q in zip(post[account_id], pre_stats)]
    if not diff:
      continue
    username = get_username(account_id)[:7]
    if username.startswith("CPU-"):
      return None
    players.append({
      "username": username,
      "win": diff[STAT_WINS] == 1,
      "kills": diff[STAT_KILLS],
      "deaths": diff[STAT_DEATHS],
      "base_dmg": diff[STAT_BASE_DMG],
      "nodes": diff[STAT_NODES],
      "flag_captures": diff[STAT_FLAG_CAPTURES],
    })

  if len(players) <= 1:
    return None

  game_name = (game.get("GameName") or "")[:15]
  game_map = metadata.get("CustomMap") or mapParser(game["GenericField3"])
  game_mode = gamerulesParser(game["GenericField3"])[0]
  time_limit = timeParser(game["GenericField3"])
  duration = (parse_dt(game["GameEndDt"]) - parse_dt(game["GameStartDt"])).total_seconds() / 60
  color = COLOR_MAP.get(game_mode, GREEN)

  # Winners first, then alphabetical (same ordering as the tracker)
  sort_key = lambda p: ('0' if p["win"] else '1') + p["username"]
  players = sorted(players, key=sort_key)
  tabulate_format = 'colalign'

  str_to_post = f'```\nTime Limit: {time_limit}\nGame Duration: {duration:.2f} minutes\n\n'

  data = [["Player", "Win?"]] + [[p["username"], 'Win' if p["win"] else 'Loss'] for p in players]
  str_to_post += tabulate(data, headers="firstrow", tablefmt=tabulate_format)

  data = [["Player", "K", "D"]] + [[p["username"], p["kills"], p["deaths"]] for p in players]
  str_to_post += '\n\n' + tabulate(data, headers="firstrow", tablefmt=tabulate_format)

  if game_mode == 'CTF':
    data = [["Player", "BD", "Fl"]] + [[p["username"], p["base_dmg"], p["flag_captures"]] for p in players]
    str_to_post += '\n\n' + tabulate(data, headers="firstrow", tablefmt=tabulate_format)
  elif game_mode == 'Siege':
    data = [["Player", "BD", "Nodes"]] + [[p["username"], p["base_dmg"], p["nodes"]] for p in players]
    str_to_post += '\n\n' + tabulate(data, headers="firstrow", tablefmt=tabulate_format)

  str_to_post += f'```\nFor more info on this game visit: https://rac-horizon.com/uya/game-history/{game["Id"]}'

  return {
    "username": "UYA Game Scores",
    "embeds": [{
      "title": f"{game_name} - {game_mode}@{game_map}",
      "description": f"\n{str_to_post}\n",
      "color": color,
    }]
  }


def post_webhook(webhook_url: str, payload: dict):
  while True:
    response = requests.post(webhook_url, json=payload, timeout=10)
    if response.status_code == 429:
      retry_after = float(response.json().get("retry_after", 5))
      print(f"[uyagamehistoryfeed] webhook rate limited, retrying in {retry_after}s")
      time.sleep(retry_after)
      continue
    response.raise_for_status()
    return


def save_cursor(cursor: datetime):
  config_get(['UyaGameHistoryFeed'])['StartDate'] = cursor.isoformat()
  config_save()


async def uyagamehistoryfeed_task(client: discord.Client, config: dict):
  await client.wait_until_ready()
  webhook_url = config['WebhookUrl']

  if config.get('StartDate'):
    cursor = datetime.fromisoformat(config['StartDate']).replace(tzinfo=None)
  else:
    cursor = datetime.utcnow()
    save_cursor(cursor)
  print(f"[uyagamehistoryfeed] starting, posting games that ended after {cursor.isoformat()}")

  while not client.is_closed():
    try:
      # Blocking HTTP runs in a thread so a long backfill doesn't stall the bot
      games = await asyncio.to_thread(fetch_games_since, cursor)
      for game in games:
        payload = await asyncio.to_thread(build_payload, game)
        if payload is not None:
          await asyncio.to_thread(post_webhook, webhook_url, payload)
          await asyncio.sleep(POST_DELAY)
        cursor = parse_dt(game["GameEndDt"])
        save_cursor(cursor)
    except Exception:
      print(traceback.format_exc())
    await asyncio.sleep(POLL_INTERVAL)


def uyagamehistoryfeed(client):
  config = config_get(['UyaGameHistoryFeed'])
  if not config or not config.get('WebhookUrl'):
    print("[uyagamehistoryfeed] no WebhookUrl configured, feed disabled")
    return
  client.loop.create_task(uyagamehistoryfeed_task(client, config))
