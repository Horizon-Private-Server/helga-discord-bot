import os
import asyncio
import asyncssh


def get_last_15_lines(input_string):
    # Split the string into lines
    lines = input_string.splitlines()
    
    # Get the last 15 lines
    last_15_lines = lines[-15:]
    
    # Join the lines back into a single string, separated by newline characters
    result = "\n".join(last_15_lines)
    
    return result


class ModSshCommands:
    def __init__(self):
        self._uya_host = os.getenv("UYA_SSH_HOST")
        self._uya_username = os.getenv("UYA_SSH_USERNAME")
        self._uya_keyfile = os.getenv("UYA_SSH_KEYFILE")

        self._dl_host = os.getenv("DL_SSH_HOST")
        self._dl_username = os.getenv("DL_SSH_USERNAME")
        self._dl_keyfile = os.getenv("DL_SSH_KEYFILE")

    async def run_remote_command(self, game, command):
        stdout = 'None'
        stderr = 'None'
        error = 'None'

        if game == 'uya':
            host = self._uya_host
            username = self._uya_username
            keyfile = self._uya_keyfile
        elif game == 'dl':
            host = self._dl_host
            username = self._dl_username
            keyfile = self._dl_keyfile

        try:
            # Connect to the remote host
            async with asyncssh.connect(host, known_hosts=None, username=username, client_keys=[keyfile]) as conn:
                # Execute the command
                result = await conn.run(command, check=True)
                stdout = get_last_15_lines(result.stdout)
                stderr = get_last_15_lines(result.stderr)

        except Exception as exc:
            error = get_last_15_lines(str(exc))

        if stdout == '':
            stdout = 'None'
        elif stderr == '':
            stderr = 'None'
        elif error == '':
            error = 'None'

        result = f'Output: \n```{stdout}```\nStandard Error:\n```{stderr}```\nErrors:\n```{error}```\n'
        return result

    async def run_remote_command_raw(self, game, command):
        stdout = ''
        stderr = ''
        error = ''

        if game == 'uya':
            host = self._uya_host
            username = self._uya_username
            keyfile = self._uya_keyfile
        elif game == 'dl':
            host = self._dl_host
            username = self._dl_username
            keyfile = self._dl_keyfile
        else:
            return stdout, stderr, 'Unknown game'

        try:
            async with asyncssh.connect(host, known_hosts=None, username=username, client_keys=[keyfile]) as conn:
                result = await conn.run(command, check=True)
                stdout = result.stdout
                stderr = result.stderr
        except Exception as exc:
            error = str(exc)

        return stdout, stderr, error
    
    async def uya_check_filesystem(self):
        return await self.run_remote_command('uya', 'df -h')

    async def uya_check_memory(self):
        return await self.run_remote_command('uya', '''free -mh''')

    async def uya_check_cpu(self):
        return await self.run_remote_command('uya', '''awk '/^cpu[0-9]+ / {usage=($2+$3+$4)*100/($2+$3+$4+$5); printf "%s: %.2f%% usage, ", $1, usage}' /proc/stat''')

    async def uya_check_containers(self):
        return await self.run_remote_command('uya', "docker container ls --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}'")

    async def uya_get_container_names(self):
        stdout, stderr, error = await self.run_remote_command_raw('uya', "docker container ls --format '{{.Names}}'")
        if error or stderr:
            combined_error = error or stderr
            return [], combined_error
        names = [line.strip() for line in stdout.splitlines() if line.strip()]
        return names, ''
    
    async def uya_clean_filesystem(self):
        return await self.run_remote_command('uya', 'docker system prune -f')
    
    async def uya_restart_server(self):
        return await self.run_remote_command('uya', 'cd horizon-uya-prod && bash run.sh -s')
    
    async def uya_restart_middleware(self):
        return await self.run_remote_command('uya', 'cd horizon-uya-prod && bash run.sh -m')
    
    async def uya_restart_database(self):
        return await self.run_remote_command('uya', 'cd horizon-uya-prod && bash run.sh -d')

    async def uya_restart_all(self):
        results = [
            "Database:\n" + await self.uya_restart_database(),
            "Waiting 3 seconds before restarting middleware..."
        ]
        await asyncio.sleep(3)
        results += [
            "Middleware:\n" + await self.uya_restart_middleware(),
            "Server:\n" + await self.uya_restart_server(),
        ]
        return "\n".join(results)

    async def uya_hard_reset(self):
        stdout, stderr, error = await self.run_remote_command_raw('uya', 'sudo reboot now')

        lines = [
            'Reboot command sent. SSH connection may drop while the host restarts.'
        ]

        if stdout.strip():
            lines.append(f'Output:\n```{get_last_15_lines(stdout)}```')
        if stderr.strip():
            lines.append(f'Standard Error:\n```{get_last_15_lines(stderr)}```')
        if error.strip():
            lines.append(f'Errors:\n```{get_last_15_lines(error)}```')

        return "\n".join(lines)

    async def uya_backup_database_to_cloud(self):
        return await self.run_remote_command('uya', 'cd /root/horizon-uya-prod/horizon-database-backup && bash run_backup.sh')
