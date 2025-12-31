import asyncio
import datetime
import math
from discord.utils import get

from mediusapi import get_players_online, UYA_API_NAME

THUMBS_UP_EMOJI = '\N{THUMBS UP SIGN}'
MAX_LOG_LENGTH = 1900
MAX_MESSAGE_LENGTH = 2000


class CommunityResetManager:
    def __init__(self, client, config_get, mod_ssh_commands, logger=print):
        self.client = client
        self.config_get = config_get
        self.mod_ssh_commands = mod_ssh_commands
        self.log = logger
        self.votes = {}
        self.vote_tasks = {}
        self.required_containers = [
            'horizon-server',
            'horizon-middleware',
            'horizon-database',
        ]

    def _normalize_blacklist(self, blacklist):
        if not blacklist:
            return []
        if not isinstance(blacklist, list):
            return []
        normalized = []
        for user_id in blacklist:
            try:
                normalized.append(int(user_id))
            except (TypeError, ValueError):
                continue
        return normalized

    def _get_settings(self):
        settings = self.config_get(['CommunityServerReset', 'UYA'])
        if not settings:
            return None

        horizon_log_id = settings.get('HorizonChannelLogId', settings.get('HorizonChannelLog'))
        public_log_id = settings.get('PublicChannelLogId', settings.get('PublicChannelLog'))
        vote_blacklist = self._normalize_blacklist(settings.get('VoteBlacklist'))

        required_keys = ['VoteDurationMinutes', 'VoteChannelId']
        for key in required_keys:
            if settings.get(key) is None:
                return None

        if horizon_log_id is None or public_log_id is None:
            return None

        return {
            'VoteDurationMinutes': settings['VoteDurationMinutes'],
            'VoteChannelId': settings['VoteChannelId'],
            'HorizonChannelLogId': horizon_log_id,
            'PublicChannelLogId': public_log_id,
            'VoteBlacklist': vote_blacklist,
        }

    def _get_active_vote(self, channel_id):
        now = datetime.datetime.now(datetime.timezone.utc)
        for message_id, vote in list(self.votes.items()):
            if vote.get('completed'):
                continue
            if vote['ends_at'] <= now:
                self.votes.pop(message_id, None)
                task = self.vote_tasks.pop(message_id, None)
                if task:
                    task.cancel()
                continue
            if vote['channel_id'] == channel_id:
                return message_id, vote
        return None, None

    def _build_prompt(self, command, votes_needed, ends_at, players, error):
        unix_time = int(ends_at.timestamp())
        deadline_text = f'<t:{unix_time}:F>'
        if command == '!hardreset':
            action_text = 'hard reset the host'
            reminder = ' Note: services will restart automatically 1 minute after the hard reboot.'
        else:
            action_text = 'reset the server fully'
            reminder = ''

        prompt = (
            f'Vote on this message with {THUMBS_UP_EMOJI} to {action_text}! '
            f'Votes needed: {votes_needed} by {deadline_text}.{reminder}'
        )
        available = max(0, 2000 - len(prompt) - 1)
        players_line = self._build_players_line(players, error, available)
        if players_line:
            prompt = f'{prompt}\n{players_line}'
        return prompt

    def _format_display_name(self, user):
        return getattr(user, 'display_name', getattr(user, 'name', 'Unknown'))

    def _build_list_line(self, prefix, items, empty_text, max_length=MAX_LOG_LENGTH):
        if max_length <= 0:
            return ''
        if not items:
            line = f'{prefix} {empty_text}'
            return line if len(line) <= max_length else line[:max_length - 3] + '...'

        line = f'{prefix} ' + ', '.join(items)
        if len(line) <= max_length:
            return line

        trimmed = []
        for item in items:
            candidate = trimmed + [item]
            remaining = len(items) - len(candidate)
            candidate_line = f'{prefix} ' + ', '.join(candidate)
            if remaining > 0:
                candidate_line += f', ... and {remaining} more'
            if len(candidate_line) > max_length:
                break
            trimmed.append(item)

        if not trimmed:
            max_item_len = max(0, max_length - len(prefix) - 4)
            if max_item_len <= 0:
                return prefix[:max_length - 3] + '...'
            return f'{prefix} {items[0][:max_item_len]}...'

        remaining = len(items) - len(trimmed)
        if remaining > 0:
            return f'{prefix} ' + ', '.join(trimmed) + f', ... and {remaining} more'

        return f'{prefix} ' + ', '.join(trimmed)

    def _append_line(self, message, line, allow_truncate=True):
        if not message:
            if len(line) <= MAX_LOG_LENGTH:
                return line
            if not allow_truncate:
                return line[:MAX_LOG_LENGTH]
            return line[:MAX_LOG_LENGTH - 3] + '...'

        available = MAX_LOG_LENGTH - len(message) - 1
        if available <= 0:
            return message
        if len(line) <= available:
            return message + '\n' + line
        if not allow_truncate:
            return message
        if available <= 3:
            return message + '\n' + line[:available]
        return message + '\n' + line[:available - 3] + '...'

    def _build_players_line(self, players, error, max_length=MAX_LOG_LENGTH):
        if error:
            line = 'Players online: Unknown (failed to fetch)'
            return line if len(line) <= max_length else line[:max_length - 3] + '...'
        if not players:
            line = 'Players online: None'
            return line if len(line) <= max_length else line[:max_length - 3] + '...'
        return self._build_list_line(f'Players online ({len(players)}):', players, 'None', max_length)

    def _calculate_votes_needed(self, online_count):
        if online_count <= 0:
            return 0
        if online_count < 4:
            return online_count
        return max(1, math.ceil(online_count * 0.70))

    def _build_log_message(self, vote, voters, vote_message, players, error):
        reminder = ''
        if vote['command'] == '!hardreset':
            reminder = 'Automatic restart_all scheduled for 1 minute after the hard reset.'

        initiator_name = vote.get('initiator_display_name', 'Unknown')
        initiator_mention = vote.get('initiator_mention', f'<@{vote["initiator_id"]}>')

        voter_details = [
            f'{self._format_display_name(user)} ({user.mention})' for user in voters
        ]
        message = ''
        message = self._append_line(message, '✅ Community Vote Passed!')
        message = self._append_line(message, f'Command: {vote["command"]}')
        message = self._append_line(message, f'Initiated by: {initiator_name} ({initiator_mention})')
        available = MAX_LOG_LENGTH - len(message) - 1
        votes_line = self._build_list_line(
            f'Votes ({len(voters)}):',
            voter_details,
            'None',
            available,
        )
        if votes_line:
            message = self._append_line(message, votes_line, allow_truncate=False)
        message = self._append_line(message, f'Vote message: {vote_message.jump_url}')
        if reminder:
            message = self._append_line(message, reminder)
        available = MAX_LOG_LENGTH - len(message) - 1
        players_line = self._build_players_line(players, error, available)
        if players_line:
            message = self._append_line(message, players_line, allow_truncate=False)
        return message

    def _get_online_players(self):
        try:
            players = get_players_online(UYA_API_NAME)
        except Exception as exc:
            self.log(f'Failed to fetch online players: {exc}')
            return [], 'failed to fetch online players'

        players_online = []
        for player in players or []:
            account_name = player.get('AccountName')
            if not account_name:
                continue
            if account_name.lower().startswith('cpu-'):
                continue
            players_online.append(account_name)

        players_online.sort(key=lambda name: name.lower())
        return players_online, ''

    async def _send_logs(self, vote, voters, vote_message):
        players, error = self._get_online_players()
        log_message = self._build_log_message(vote, voters, vote_message, players, error)
        await self._send_log_message([vote['horizon_log_id'], vote['public_log_id']], log_message)

    async def _send_log_message(self, channel_ids, message):
        for channel_id in channel_ids:
            channel = self.client.get_channel(channel_id)
            if channel:
                await channel.send(message)
            else:
                self.log(f'Log channel not found: {channel_id}')

    async def _send_command_output(self, channel, output):
        if not output:
            return
        if len(output) <= MAX_MESSAGE_LENGTH:
            await channel.send(output)
            return

        for chunk in self._split_long_text(output, MAX_LOG_LENGTH):
            await channel.send(chunk)

    def _split_long_text(self, text, max_len):
        chunks = []
        remaining = text
        while remaining:
            if len(remaining) <= max_len:
                chunks.append(remaining)
                break
            split_at = remaining.rfind('\n', 0, max_len)
            if split_at == -1 or split_at < max_len // 2:
                split_at = max_len
            chunk = remaining[:split_at]
            chunks.append(chunk)
            remaining = remaining[split_at:].lstrip('\n')
        return chunks

    async def _vote_timeout(self, message_id):
        vote = self.votes.get(message_id)
        if not vote:
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        delay = (vote['ends_at'] - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)

        vote = self.votes.get(message_id)
        if not vote or vote.get('completed'):
            return

        self.votes.pop(message_id, None)
        self.vote_tasks.pop(message_id, None)

        channel = self.client.get_channel(vote['channel_id'])
        if channel:
            await channel.send('Vote window closed without enough votes.')

    async def _finalize_vote(self, vote_message, vote, voters):
        if vote.get('completed'):
            return

        vote['completed'] = True
        self.votes.pop(vote_message.id, None)
        task = self.vote_tasks.pop(vote_message.id, None)
        if task:
            task.cancel()

        await self._send_logs(vote, voters, vote_message)

        await vote_message.channel.send('Vote passed. Running the requested action now.')
        if vote['command'] == '!hardreset':
            output = await self.mod_ssh_commands.uya_hard_reset()
            await vote_message.channel.send('Hard reset issued. Restarting services in 1 minute.')
            asyncio.create_task(self._schedule_post_hardreset_restart(vote_message.channel))
        else:
            output = await self.mod_ssh_commands.uya_restart_all()

        await self._send_command_output(vote_message.channel, output)

    async def _schedule_post_hardreset_restart(self, channel):
        await asyncio.sleep(60)
        await channel.send('Running restart_all after the hard reset...')
        output = await self.mod_ssh_commands.uya_restart_all()
        await self._send_command_output(channel, output)

    async def _evaluate_vote(self, message_id):
        vote = self.votes.get(message_id)
        if not vote or vote.get('completed'):
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        if vote['ends_at'] <= now:
            return

        channel = self.client.get_channel(vote['channel_id'])
        if not channel:
            return

        try:
            vote_message = await channel.fetch_message(message_id)
        except Exception as exc:
            self.log(f'Failed to fetch vote message {message_id}: {exc}')
            return

        thumbs_reaction = get(vote_message.reactions, emoji=THUMBS_UP_EMOJI)
        if not thumbs_reaction:
            return

        users = [user async for user in thumbs_reaction.users()]
        blacklist = set(vote.get('blacklist', []))
        voters = [
            user for user in users
            if not user.bot and user.id not in blacklist
        ]

        if len(voters) < vote['votes_needed']:
            return

        await self._finalize_vote(vote_message, vote, voters)

    def _is_connection_refused(self, error):
        return 'connection refused' in error.lower()

    async def _get_missing_containers(self):
        names, error = await self.mod_ssh_commands.uya_get_container_names()
        if error:
            return None, error

        running = set(names)
        missing = [name for name in self.required_containers if name not in running]
        return missing, ''

    def _cancel_active_vote(self, channel_id):
        message_id, _ = self._get_active_vote(channel_id)
        if not message_id:
            return
        self.votes.pop(message_id, None)
        task = self.vote_tasks.pop(message_id, None)
        if task:
            task.cancel()

    async def _handle_auto_reset(self, message, settings, missing):
        self._cancel_active_vote(message.channel.id)
        missing_list = ', '.join(missing)
        players, error = self._get_online_players()
        log_message = ''
        log_message = self._append_line(log_message, 'Community reset auto-approved.')
        log_message = self._append_line(log_message, 'Reason: one or more core containers are not running.')
        log_message = self._append_line(log_message, 'Command: !reset')
        log_message = self._append_line(
            log_message,
            f'Initiated by: {message.author.display_name} ({message.author.mention})',
        )
        log_message = self._append_line(log_message, f'Missing containers: {missing_list}')
        available = MAX_LOG_LENGTH - len(log_message) - 1
        players_line = self._build_players_line(players, error, available)
        if players_line:
            log_message = self._append_line(log_message, players_line, allow_truncate=False)
        await self._send_log_message(
            [int(settings['HorizonChannelLogId']), int(settings['PublicChannelLogId'])],
            log_message,
        )

        await message.channel.send(
            'Detected missing containers. Skipping the vote and restarting services now.'
        )
        output = await self.mod_ssh_commands.uya_restart_all()
        await message.channel.send(output)

    async def _handle_auto_approve_no_players(self, message, settings, command, players, error):
        players_line = self._build_players_line(players, error)
        log_message = ''
        log_message = self._append_line(log_message, 'Community reset auto-approved.')
        log_message = self._append_line(log_message, 'Reason: no players online.')
        log_message = self._append_line(log_message, f'Command: {command}')
        log_message = self._append_line(
            log_message,
            f'Initiated by: {message.author.display_name} ({message.author.mention})',
        )
        log_message = self._append_line(log_message, players_line)
        await self._send_log_message(
            [int(settings['HorizonChannelLogId']), int(settings['PublicChannelLogId'])],
            log_message,
        )

        await message.channel.send('No players online. Skipping the vote and running the request now.')
        if command == '!hardreset':
            output = await self.mod_ssh_commands.uya_hard_reset()
            await message.channel.send('Hard reset issued. Restarting services in 1 minute.')
            asyncio.create_task(self._schedule_post_hardreset_restart(message.channel))
        else:
            output = await self.mod_ssh_commands.uya_restart_all()
        await self._send_command_output(message.channel, output)

    async def handle_reaction(self, payload):
        vote = self.votes.get(payload.message_id)
        if not vote:
            return

        if str(payload.emoji) != THUMBS_UP_EMOJI:
            return

        if payload.user_id == self.client.user.id:
            return

        await self._evaluate_vote(payload.message_id)

    async def handle_message(self, message):
        settings = self._get_settings()
        if not settings:
            return False

        command = message.content.strip().lower()
        if command not in ['!reset', '!hardreset']:
            return False

        if message.channel.id != int(settings['VoteChannelId']):
            return False

        if message.author.id in settings.get('VoteBlacklist', []):
            return True

        if command == '!reset':
            missing, error = await self._get_missing_containers()
            if error:
                if self._is_connection_refused(error):
                    await message.channel.send("Couldn't connect, try again in 30 seconds.")
                    return True
                self.log(f'Failed to check containers: {error}')
            elif missing:
                await self._handle_auto_reset(message, settings, missing)
                return True

        players, error = self._get_online_players()
        if error:
            await message.channel.send("Couldn't fetch players online, try again in 30 seconds.")
            return True

        online_count = len(players)
        votes_needed = self._calculate_votes_needed(online_count)
        if votes_needed == 0:
            await self._handle_auto_approve_no_players(message, settings, command, players, error)
            return True

        _, active_vote = self._get_active_vote(message.channel.id)
        if active_vote:
            await message.channel.send('A reset vote is already in progress.')
            return True

        duration_minutes = int(settings['VoteDurationMinutes'])
        if duration_minutes <= 0:
            await message.channel.send('Voting is currently disabled.')
            return True

        ends_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=duration_minutes)
        prompt = self._build_prompt(command, votes_needed, ends_at, players, error)
        vote_message = await message.channel.send(prompt)
        await vote_message.add_reaction(THUMBS_UP_EMOJI)
        self.votes[vote_message.id] = {
            'command': command,
            'initiator_id': message.author.id,
            'initiator_display_name': message.author.display_name,
            'initiator_mention': message.author.mention,
            'channel_id': vote_message.channel.id,
            'ends_at': ends_at,
            'votes_needed': votes_needed,
            'horizon_log_id': int(settings['HorizonChannelLogId']),
            'public_log_id': int(settings['PublicChannelLogId']),
            'blacklist': settings.get('VoteBlacklist', []),
            'completed': False,
        }
        self.vote_tasks[vote_message.id] = asyncio.create_task(
            self._vote_timeout(vote_message.id)
        )

        return True
