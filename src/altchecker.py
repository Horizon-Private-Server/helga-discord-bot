import asyncio
import traceback
import discord

from config import config_get
from mediusapi import get_alts, get_alts_public, UYA_API_NAME

# !alt <account name>
# Ported from goldboltbot. Looks up accounts sharing a machine id or last sign-in IP
# with the given account, via the middleware's Account/getAlts and Account/getAltsPublic routes.
#
# Config (config.json -> "AltChecker"):
#   PublicChannelIds:  channels where anyone can run !alt and get the reduced (EMU/PS2 + IP) result
#   PrivateChannelIds: channels where !alt returns the full result (machine id and IP matches)
#   PrivateRoleId:     role required to use !alt in a private channel (0 = no role check)

COMMAND = '!alt '


def format_matches(matches):
  if matches is None:
    return 'Not Found'
  return str(matches)


def public_alt_message(username, result):
  emu_or_ps2 = result['EmuOrPs2'] if result else 'Not Found'
  ip_results = result['IpMatches'] if result else None
  return f"""
UYA Alt results for: `{username}`
EMU or PS2? `{emu_or_ps2}`
Matches: ```{format_matches(ip_results)}```
    """


def private_alt_message(username, result):
  emu_or_ps2 = result['EmuOrPs2'] if result else 'Not Found'
  mac_results = result['MachineIdMatches'] if result else None
  ip_results = result['IpMatches'] if result else None
  return f"""
Searching database for `{username}` ...
EMU or PS2? `{emu_or_ps2}`
Machine ID matches for `{username}`: ```{format_matches(mac_results)}```
IP matches for `{username}`: ```{format_matches(ip_results)}```
        """


async def handle_alt_message(message: discord.Message) -> bool:
  """Handle !alt in configured channels. Returns True if the message was consumed."""
  if message.author.bot:
    return False
  if len(message.content) <= len(COMMAND) or not message.content.startswith(COMMAND):
    return False

  config = config_get(['AltChecker']) or {}
  public_channels = config.get('PublicChannelIds') or []
  private_channels = config.get('PrivateChannelIds') or []
  private_role_id = config.get('PrivateRoleId') or 0
  username = message.content[len(COMMAND):].strip()

  try:
    if message.channel.id in private_channels:
      if private_role_id and not any(role.id == private_role_id for role in message.author.roles):
        return False
      result = await asyncio.to_thread(get_alts, UYA_API_NAME, username)
      await message.channel.send(private_alt_message(username, result))
      return True

    if message.channel.id in public_channels:
      result = await asyncio.to_thread(get_alts_public, UYA_API_NAME, username)
      await message.channel.send(public_alt_message(username, result))
      return True
  except Exception:
    print(traceback.format_exc())
    await message.channel.send(f"Got an error looking up alts for `{username}`.")
    return True

  return False
