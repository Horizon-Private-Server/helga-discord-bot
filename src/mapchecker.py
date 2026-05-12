import discord
import aiohttp
import asyncssh
import os
from dataclasses import dataclass
from typing import Optional

# Configuration
MAPCHECKER_ROLE_ID = int(os.getenv("MAPCHECKER_ROLE_ID", "0"))  # Set to 0 if not configured

MAP_SERVER_PATH = "/tmp/maps"
MAP_DOWNLOADS_SERVER_PATH = "/var/www/static/downloads"
STANDARD_MAPS_SERVER_PATH = f"{MAP_DOWNLOADS_SERVER_PATH}/maps"
DL_REPOSITORY_PATHS = {
    "standard": f"{STANDARD_MAPS_SERVER_PATH}/dl",
    "survival": f"{MAP_DOWNLOADS_SERVER_PATH}/unofficial_maps/horizon_survival/dl",
    "dzo-only": f"{MAP_DOWNLOADS_SERVER_PATH}/unofficial_maps/horizon_dzo/dl",
    "party": f"{MAP_DOWNLOADS_SERVER_PATH}/unofficial_maps/horizon_party/dl",
    "retired": f"{MAP_DOWNLOADS_SERVER_PATH}/unofficial_maps/horizon_retired/dl",
    #"collectathon": f"{SERVER_DOWNLOADS_DIRECTORY}/unofficial_maps/collectathon/dl"
}

MAIN_COMMAND = 'python3 /home/box/update.py'
BUILD_CMD = "bash /home/box/rebuild.sh"

@dataclass
class MapUploadCommand:
    game: str
    repository: Optional[str]
    is_confirm: bool

class MockContext:
    def __init__(self, message):
        self.message = message
        self.channel = message.channel
        self.guild = message.guild
        self.author = message.author

    async def respond(self, content):
        await self.channel.send(content)

    async def followup(self):
        return self

    async def send(self, content):
        await self.channel.send(content)

def build_server_path(game, repository):
    if game == 'dl' and repository is not None:
        return DL_REPOSITORY_PATHS.get(repository)
    else:
        return f"{STANDARD_MAPS_SERVER_PATH}/{game}"

def build_staging_path(game: str, repository: Optional[str]) -> str:
    base = f"{MAP_SERVER_PATH}/{game}"

    if game == "dl":
        repo = repository or "standard"
        return f"{base}/{repo}"

    return base

def parse_mapupload_command(content: str) -> MapUploadCommand:
    tokens = content.strip().split()

    if len(tokens) < 2:
        raise ValueError("❌ Usage: `!mapupload <game> [repository]` with file attachments OR `!mapupload <game> [repository] confirm`\nExamples: `!mapupload dl` (attach files) or `!mapupload uya confirm` or `!mapupload dl survival confirm`")

    game = tokens[1].lower()
    if game not in ("dl", "uya"):
        raise ValueError("❌ Invalid game. Use 'dl' or 'uya'.")

    is_confirm = tokens[-1].lower() == "confirm"
    # grab the middle argument which could be a repository for DL
    args = tokens[2:-1] if is_confirm else tokens[2:]

    repository = None

    if game == "dl":
        if len(args) > 1:
            raise ValueError("❌ Too many arguments.")

        if len(args) == 1:
            repository = args[0].lower()
            if repository not in DL_REPOSITORY_PATHS:
                raise ValueError(f"❌ Invalid repository. Options: {', '.join(DL_REPOSITORY_PATHS.keys())}.")
        else:
            repository = "standard"
    else:
        if args:
            raise ValueError("❌ Too many arguments.")

    return MapUploadCommand(game=game, repository=repository, is_confirm=is_confirm)

def has_mapchecker_permission(user):
    """
    Check if user has permission to use mapchecker commands
    """
    if MAPCHECKER_ROLE_ID == 0:
        print("WARNING: MAPCHECKER_ROLE_ID not set - allowing all users")
        return True
    
    return any(role.id == MAPCHECKER_ROLE_ID for role in user.roles)


async def get_ssh_connection():
    """
    Create SSH connection to the map server
    """
    host = os.getenv("BOX_SSH_HOST")
    username = os.getenv("BOX_SSH_USERNAME")
    key_path = os.getenv("BOX_SSH_KEYFILE")
    
    print(f"DEBUG: SSH connection details - Host: {host}, Username: {username}, Key: {key_path}")
    
    if not host or not username:
        raise Exception("BOX_SSH_HOST and BOX_SSH_USERNAME environment variables must be set")
    
    try:
        # Use key file if provided, otherwise use default SSH authentication
        # Set known_hosts=None to accept unknown host keys (for automated use)
        if key_path and os.path.exists(key_path):
            print(f"DEBUG: Connecting with key file: {key_path}")
            conn = await asyncssh.connect(
                host, 
                username=username, 
                client_keys=[key_path],
                known_hosts=None
            )
        else:
            print(f"DEBUG: Connecting with default SSH authentication")
            conn = await asyncssh.connect(
                host, 
                username=username,
                known_hosts=None
            )
        
        print(f"DEBUG: SSH connection successful")
        return conn
        
    except Exception as e:
        print(f"DEBUG: SSH connection failed: {e}")
        raise Exception(f"Failed to connect via SSH: {e}")


async def list_version_files(game):
    """
    SSH to server and list *.version files in MAP_SERVER_PATH/{game}/
    """
    conn = None
    try:
        conn = await get_ssh_connection()
        
        if conn is None:
            raise Exception("SSH connection returned None")
        
        # Create game-specific path
        game_path = f"{MAP_SERVER_PATH}/{game}"
        
        # List *.version files in the game-specific directory
        result = await conn.run(f'ls -la {game_path}/*.version 2>/dev/null || echo "No .version files found"')
        
        if result is None:
            raise Exception("SSH command returned None")
        
        print(f"\n=== MAP CHECKER - {game.upper()} SERVER FILES ===")
        print(f"Directory: {game_path}")
        print("=" * 50)
        print(result.stdout)
        print("=" * 50)
        
        return result.stdout.strip()
        
    except Exception as e:
        error_msg = f"SSH Error: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg
    finally:
        # Ensure connection is closed even if an error occurs
        if conn is not None:
            try:
                await conn.close()
            except:
                pass


async def clear_game_folder(game, repository):
    """
    Clear all files from the game-specific folder
    """
    conn = None
    try:
        conn = await get_ssh_connection()
        
        if conn is None:
            raise Exception("SSH connection returned None")
        
        # Create game-specific path
        game_path = build_staging_path(game, repository)

        print(f"\n=== MAP CLEAR - {game.upper()} ===")
        print(f"Clearing directory: {game_path}")
        print("=" * 50)
        
        # Remove all files in the game directory and recreate it
        await conn.run(f'rm -rf {game_path}')
        await conn.run(f'mkdir -p {game_path}')
        
        print(f"✅ Successfully cleared {game_path}")
        print("=" * 50)
        
        return True, f"Cleared {game_path}"
        
    except Exception as e:
        error_msg = f"Error clearing {game} folder: {e}"
        print(f"❌ {error_msg}")
        return False, error_msg
    finally:
        # Ensure connection is closed
        if conn is not None:
            try:
                await conn.close()
            except:
                pass


async def upload_single_file(session, game, repository, file, file_index=None):
    """
    Download and upload a single file to the server
    """
    conn = None
    try:
        # Download file from Discord
        async with session.get(file.url) as response:
            if response.status != 200:
                error_msg = f"Failed to download {file.filename}: HTTP {response.status}"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            file_content = await response.read()
        
        # Create game-specific path
        game_path = build_staging_path(game, repository)

        # Print upload info to console
        file_prefix = f"File {file_index}: " if file_index is not None else ""
        print(f"\n=== MAP UPLOAD - {game.upper()} ===")
        print(f"{file_prefix}{file.filename}")
        print(f"Size: {len(file_content)} bytes")
        print(f"Content Type: {file.content_type}")
        print(f"Uploading to: {game_path}/{file.filename}")
        print("=" * 50)
        
        # Connect to server and upload file
        conn = await get_ssh_connection()
        
        if conn is None:
            raise Exception("SSH connection returned None")
        
        # Create remote game-specific directory if it doesn't exist
        await conn.run(f'mkdir -p {game_path}')
        
        # Upload file using SFTP
        async with conn.start_sftp_client() as sftp:
            remote_path = f"{game_path}/{file.filename}"
            
            # Write file content to remote server
            async with sftp.open(remote_path, 'wb') as remote_file:
                await remote_file.write(file_content)
        
        # Verify upload by checking file size
        result = await conn.run(f'ls -la {game_path}/{file.filename}')
        
        print(f"✅ Upload successful!")
        print(f"Remote file info: {result.stdout.strip()}")
        print("=" * 50)
        
        return True, file.filename
        
    except Exception as e:
        error_msg = f"Error uploading {file.filename}: {e}"
        print(f"❌ {error_msg}")
        return False, error_msg
    finally:
        # Ensure connection is closed
        if conn is not None:
            try:
                await conn.close()
            except:
                pass


async def mapupload_command(ctx, game, files, repository):
    """
    Upload map files to the server for the specified game (supports multiple files)
    Clears the game folder before uploading new files
    """
    # Check permissions
    if not has_mapchecker_permission(ctx.author):
        await ctx.respond("❌ You don't have permission to use mapchecker commands.")
        return
    
    try:
        if len(files) == 1:
            await ctx.respond(f"Clearing {game.upper()} folder and uploading map file: {files[0].filename}")
        else:
            await ctx.respond(f"Clearing {game.upper()} folder and uploading {len(files)} map files...")
        
        # Clear the game folder first
        clear_success, clear_msg = await clear_game_folder(game, repository)
        if not clear_success:
            await ctx.followup.send(f"❌ Failed to clear {game.upper()} folder: {clear_msg}")
            return
        
        successful_files = []
        failed_files = []
        
        # Download and upload all files
        async with aiohttp.ClientSession() as session:
            for index, file in enumerate(files, 1):
                file_index = index if len(files) > 1 else None
                success, result_msg = await upload_single_file(session, game, repository, file, file_index)
                
                if success:
                    successful_files.append(result_msg)
                else:
                    failed_files.append(result_msg)
        
        # Send summary response
        summary_parts = []
        if successful_files:
            if len(successful_files) == 1:
                summary_parts.append(f"✅ Successfully uploaded: {successful_files[0]}")
            else:
                summary_parts.append(f"✅ Successfully uploaded {len(successful_files)} files:")
                for filename in successful_files:
                    summary_parts.append(f"  • {filename}")
        
        if failed_files:
            if len(failed_files) == 1:
                summary_parts.append(f"❌ Failed to upload: {failed_files[0]}")
            else:
                summary_parts.append(f"❌ Failed to upload {len(failed_files)} files:")
                for error_msg in failed_files:
                    summary_parts.append(f"  • {error_msg}")
        
        summary_parts.append(f"\n**Game:** {game.upper()}")
        summary_parts.append(f"**Server Path:** `{build_staging_path(game, repository)}`")
        
        # Run the update script if there were successful uploads
        if successful_files:
            summary_parts.append("\n**Running update script...**")
            conn = None
            try:
                # Connect to server and run the update script
                try:
                    conn = await get_ssh_connection()
                except Exception as conn_error:
                    print(f"Failed to get SSH connection: {conn_error}")
                    summary_parts.append("❌ Failed to connect to server for update script")
                    conn = None
                
                if conn is not None:
                    final_directory = build_server_path(game, repository)
                    staging_path = build_staging_path(game, repository)
                    update_cmd = f"{MAIN_COMMAND} {staging_path} {final_directory} check"
                    print(f"\n=== RUNNING UPDATE SCRIPT - {game.upper()} ===")
                    print(f"Command: {update_cmd}")
                    print("=" * 50)
                    
                    result = await conn.run(update_cmd)
                    
                    if result is not None:
                        print(f"Exit code: {result.exit_status}")
                        print(f"Output: {result.stdout}")
                        if result.stderr:
                            print(f"Errors: {result.stderr}")
                        print("=" * 50)
                        
                        # Add script results to response
                        if result.exit_status == 0:
                            summary_parts.append("✅ **Update script completed successfully:**")
                            if result.stdout and result.stdout.strip():
                                summary_parts.append(f"```\n{result.stdout.strip()}\n```")
                            else:
                                summary_parts.append("Script completed with no output.")
                        else:
                            summary_parts.append("❌ **Update script failed:**")
                            error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
                            if error_output:
                                summary_parts.append(f"```\n{error_output}\n```")
                            summary_parts.append(f"Exit code: {result.exit_status}")
                    else:
                        summary_parts.append("❌ Update script returned no result")
                else:
                    summary_parts.append("❌ Failed to connect to server for update script")
                    
            except Exception as e:
                error_msg = f"Error running update script: {str(e)}"
                print(f"❌ {error_msg}")
                summary_parts.append(f"❌ **Update script error:** {error_msg}")
            finally:
                # Ensure connection is closed
                if conn is not None:
                    try:
                        await conn.close()
                    except:
                        pass
        
        summary_parts.append("\nCheck console for detailed upload logs.")
        
        await ctx.followup.send("\n".join(summary_parts))
                    
    except Exception as e:
        print(f"Error in mapupload command: {e}")
        await ctx.followup.send(f"❌ Error uploading files: {str(e)}")


async def mapupload_confirm_command(ctx, game, repository):
    """
    Confirm and deploy maps from staging to final location
    """
    # Check permissions
    if not has_mapchecker_permission(ctx.author):
        await ctx.respond("❌ You don't have permission to use mapchecker commands.")
        return
    
    try:
        await ctx.respond(f"Confirming and deploying {game.upper()} maps...")
        
        conn = None
        try:
            # Connect to server and run the update script with 'update' parameter
            try:
                conn = await get_ssh_connection()
            except Exception as conn_error:
                print(f"Failed to get SSH connection: {conn_error}")
                await ctx.followup.send("❌ Failed to connect to server for deployment")
                return
            
            if conn is not None:
                final_directory = build_server_path(game, repository)
                staging_path = build_staging_path(game, repository)
                update_cmd = f"{MAIN_COMMAND} {staging_path} {final_directory} update"
                print(f"\n=== RUNNING DEPLOYMENT SCRIPT - {game.upper()} ===")
                print(f"Command: {update_cmd}")
                print("=" * 50)
                
                result = await conn.run(update_cmd)
                
                if result is not None:
                    print(f"Exit code: {result.exit_status}")
                    print(f"Output: {result.stdout}")
                    if result.stderr:
                        print(f"Errors: {result.stderr}")
                    print("=" * 50)
                    
                    # Add script results to response
                    summary_parts = [f"**Game:** {game.upper()}"]
                    summary_parts.append(f"**Source:** `{staging_path}`")
                    summary_parts.append(f"**Destination:** `{final_directory}`")

                    # Send update results first
                    if result.exit_status == 0:
                        summary_parts.append("\n✅ **Deployment completed successfully:**")
                        if result.stdout and result.stdout.strip():
                            summary_parts.append(f"```\n{result.stdout.strip()}\n```")
                        else:
                            summary_parts.append("Deployment completed with no output.")
                    else:
                        summary_parts.append("\n❌ **Deployment failed:**")
                        error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
                        if error_output:
                            summary_parts.append(f"```\n{error_output}\n```")
                        summary_parts.append(f"Exit code: {result.exit_status}")
                        
                    summary_parts.append("\nCheck console for detailed deployment logs.")
                    await ctx.followup.send("\n".join(summary_parts))
                    
                    # Only run build if deployment was successful
                    if result.exit_status == 0:
                        # Send separate deploying message
                        await ctx.followup.send("🔄 **Deploying...**")
                        
                        # Run build script as completely separate operation
                        build_conn = None
                        try:
                            # Get new connection for build
                            try:
                                build_conn = await get_ssh_connection()
                            except Exception as build_conn_error:
                                print(f"Failed to get SSH connection for build: {build_conn_error}")
                                await ctx.followup.send("❌ Failed to connect to server for build")
                                return
                            
                            if build_conn is not None:
                                print(f"\n=== RUNNING BUILD SCRIPT - {game.upper()} ===")
                                print(f"Command: {BUILD_CMD}")
                                print("=" * 50)
                                
                                build_result = await build_conn.run(BUILD_CMD)
                                
                                if build_result is not None:
                                    print(f"Build exit code: {build_result.exit_status}")
                                    print(f"Build output: {build_result.stdout}")
                                    if build_result.stderr:
                                        print(f"Build errors: {build_result.stderr}")
                                    print("=" * 50)
                                    
                                    # Create separate build summary
                                    build_summary_parts = [f"**Build Results for {game.upper()}:**"]
                                    
                                    # Get last 10 lines of output
                                    if build_result.stdout:
                                        output_lines = build_result.stdout.strip().split('\n')
                                        last_10_lines = output_lines[-10:] if len(output_lines) >= 10 else output_lines
                                        last_10_output = '\n'.join(last_10_lines)
                                    else:
                                        last_10_output = "No output"
                                    
                                    if build_result.exit_status == 0:
                                        build_summary_parts.append("\n✅ **Build completed successfully:**")
                                        build_summary_parts.append(f"```\n{last_10_output}\n```")
                                    else:
                                        build_summary_parts.append(f"\n❌ **Build failed (exit code {build_result.exit_status}):**")
                                        error_output = build_result.stderr.strip() if build_result.stderr else last_10_output
                                        build_summary_parts.append(f"```\n{error_output}\n```")
                                    
                                    build_summary_parts.append("\nCheck console for detailed build logs.")
                                    await ctx.followup.send("\n".join(build_summary_parts))
                                else:
                                    await ctx.followup.send("❌ Build script returned no result")
                            else:
                                await ctx.followup.send("❌ Failed to connect to server for build")
                                
                        except Exception as build_error:
                            build_error_msg = f"Error running build script: {str(build_error)}"
                            print(f"❌ {build_error_msg}")
                            await ctx.followup.send(f"❌ **Build error:** {build_error_msg}")
                        finally:
                            # Close build connection separately
                            if build_conn is not None:
                                try:
                                    await build_conn.close()
                                except:
                                    pass
                else:
                    await ctx.followup.send("❌ Deployment script returned no result")
            else:
                await ctx.followup.send("❌ Failed to connect to server for deployment")
                
        except Exception as e:
            error_msg = f"Error running deployment script: {str(e)}"
            print(f"❌ {error_msg}")
            await ctx.followup.send(f"❌ **Deployment error:** {error_msg}")
        finally:
            # Ensure connection is closed
            if conn is not None:
                try:
                    await conn.close()
                except:
                    pass
                    
    except Exception as e:
        print(f"Error in mapupload confirm command: {e}")
        await ctx.followup.send(f"❌ Error during deployment: {str(e)}")


async def mapclear_command(ctx, game, repository):
    """
    Clear all files from the game-specific folder
    """
    # Check permissions
    if not has_mapchecker_permission(ctx.author):
        await ctx.respond("❌ You don't have permission to use mapchecker commands.")
        return
    
    try:
        await ctx.respond(f"Clearing {game.upper()} folder...")
        
        success, result_msg = await clear_game_folder(game, repository)
        
        if success:
            response = f"✅ {result_msg}"
        else:
            response = f"❌ {result_msg}"
        
        response += f"\n\n**Game:** {game.upper()}\n**Server Path:** `{build_staging_path(game, repository)}`"
        
        await ctx.followup.send(response)
                    
    except Exception as e:
        print(f"Error in mapclear command: {e}")
        await ctx.followup.send(f"❌ Error clearing folder: {str(e)}")


async def handle_mapchecker_message(message):
    """
    Handle !mapupload and !mapclear messages
    """
    if message.author.bot:
        return False

    # Check permissions first
    if not has_mapchecker_permission(message.author):
        if message.content.strip().startswith(('!mapupload', '!mapclear')):
            await message.channel.send("❌ You don't have permission to use mapchecker commands.")
            return True
        return False

    content = message.content.strip()

    # Handle !mapclear command (no file attachments needed)
    if content.startswith('!mapclear'):
        parts = content.split()
        if len(parts) < 2:
            await message.channel.send("❌ Usage: `!mapclear <game> [repository]`\nExample: `!mapclear uya` or `!mapclear dl standard`")
            return True

        game = parts[1].lower()
        if game not in ['dl', 'uya']:
            await message.channel.send("❌ Invalid game. Use 'dl' or 'uya'.")
            return True

        repository = None
        if game == 'dl':
            repository = 'standard'
            if len(parts) >= 3:
                repository = parts[2].lower()
            if repository not in DL_REPOSITORY_PATHS:
                await message.channel.send(f"❌ Invalid repository. Options: {', '.join(DL_REPOSITORY_PATHS.keys())}.")
                return True

        # Add followup method to mock context
        mock_ctx = MockContext(message)
        mock_ctx.followup = mock_ctx
        await mapclear_command(mock_ctx, game, repository)
        return True


    # Handle !mapupload command (supports both upload and confirm modes)
    elif content.startswith('!mapupload'):
        try:
            command = parse_mapupload_command(message.content)
        except ValueError as error:
            await message.channel.send(str(error))
            return True
        mock_ctx = MockContext(message)
        mock_ctx.followup = mock_ctx
        if command.is_confirm:
            # Handle confirm command (no file attachments needed)
            await mapupload_confirm_command(mock_ctx, command.game, command.repository)
        else:
            # Handle regular upload command (requires file attachments)
            if not message.attachments:
                await message.channel.send( "❌ No files attached! Use `!mapupload <game>` with file attachments.")
                return True
            await mapupload_command(mock_ctx, command.game, message.attachments, command.repository)
        return True
    return False

def setup_mapchecker(client):
    """
    Set up the mapchecker slash command group
    """
    from config import config_get
    
    # Create slash command group
    mapchecker = client.create_group(
        "mapchecker", 
        "Commands for map files and server management.", 
        guild_ids=config_get(['Stats', 'GuildIds'])
    )
    
    @mapchecker.command(
        name="help", 
        description="Instructions for map commands"
    )
    async def cmd_mapchecker_help(
        ctx: discord.ApplicationContext
    ):
        # Check permissions
        if not has_mapchecker_permission(ctx.author):
            await ctx.respond("❌ You don't have permission to use mapchecker commands.")
            return
        
        await ctx.respond(
            "**Map Commands Usage:**\n\n"
            #"**Check Server Files:**\n"
            #"• `!mapchecker dl` - List *.version files on DL server\n"
            #"• `!mapchecker uya` - List *.version files on UYA server\n\n"
            "**Upload Files to Server (Staging):**\n"
            "• `!mapupload dl` - Clear DL folder and upload files (main / standard repository if not specified) (attach files)\n"
            "• `!mapupload uya` - Clear UYA folder and upload files (attach files)\n\n"
            "• `!mapupload dl survival` - Clear DL folder and upload files for the survival repository (attach files)\n\n"
            "**Deploy Maps to Production:**\n"
            "• `!mapupload dl confirm` - Deploy DL maps from staging to production\n"
            "• `!mapupload dl party confirm` - Deploy DL maps from staging to production for the party repository\n"
            "• `!mapupload uya confirm` - Deploy UYA maps from staging to production\n\n"
            "**Clear Server Folders:**\n"
            "• `!mapclear dl` - Remove all files from DL staging folder\n"
            "• `!mapclear dl standard` - Remove all files from DL staging folder for the main / standard repository\n"
            "• `!mapclear uya` - Remove all files from UYA staging folder\n\n"
            "**Examples:**\n"
            #"• `!mapchecker dl` - Lists server files via SSH\n"
            "• `!mapupload uya` with files attached - Upload to staging and validate\n"
            "• `!mapupload dl confirm` - Deploy validated maps to production\n"
            "• `!mapclear dl` - Clear staging folder\n\n"
            f"**Staging:** `{MAP_SERVER_PATH}/[game]/` | **Production:** `{STANDARD_MAPS_SERVER_PATH}/[game]/`\n"
            f"**Available repositories for DL:** {', '.join(DL_REPOSITORY_PATHS.keys())}.\n"
            "**Note:** Upload validates maps in staging. Use 'confirm' to deploy to production.\n"
            f"**Permissions:** Only users with role ID {MAPCHECKER_ROLE_ID} can use these commands."
        )
    
    return mapchecker