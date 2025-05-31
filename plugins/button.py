# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL

import logging
import asyncio
import json
import os
import shutil
import time
from datetime import datetime
from pyrogram import enums
from pyrogram.types import InputMediaPhoto
from plugins.config import Config
from plugins.script import Translation
from plugins.thumbnail import *
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes
from plugins.database.database import db
from PIL import Image
from plugins.functions.ran_text import random_char
from plugins.config import Config
import aiohttp
import re
import random
import string
import base64

cookies_file = Config.COOKIES_FILE
# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

async def generate_degoo_cookies():
    try:
        # Generate random session ID
        session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        auth_token = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
        
        cookies = {
            "cookies": [
                {
                    "domain": "app.degoo.com",
                    "name": "session",
                    "value": session_id
                },
                {
                    "domain": "app.degoo.com",
                    "name": "auth_token",
                    "value": auth_token
                }
            ]
        }
        
        # Save cookies to file
        with open(Config.COOKIES_FILE, 'w') as f:
            json.dump(cookies, f)
        
        return True
    except Exception as e:
        logger.error(f"Error generating Degoo cookies: {e}")
        return False

async def extract_degoo_url(url):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://app.degoo.com",
                "Referer": "https://app.degoo.com/",
                "X-Requested-With": "XMLHttpRequest"
            }
            
            # Extract share ID from URL
            share_id = url.split('/')[-1]
            
            # First get the share info
            share_url = f"https://app.degoo.com/api/share/{share_id}"
            async with session.get(share_url, headers=headers) as response:
                if response.status == 200:
                    share_data = await response.json()
                    if 'files' in share_data:
                        files = share_data['files']
                        # Get download URLs for each file
                        for file in files:
                            file_id = file.get('id')
                            if file_id:
                                download_url = f"https://app.degoo.com/api/share/{share_id}/file/{file_id}/download"
                                file['download_url'] = download_url
                        return files
                return None
    except Exception as e:
        logger.error(f"Error extracting Degoo URL: {e}")
        return None

async def download_degoo_file(url, output_path, headers):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    with open(output_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                    return True
                return False
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return False

async def login_to_degoo():
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Content-Type": "application/json",
                "Origin": "https://app.degoo.com",
                "Referer": "https://app.degoo.com/login"
            }
            
            # Login data
            login_data = {
                "email": Config.DEGOO_EMAIL,
                "password": Config.DEGOO_PASSWORD
            }
            
            # Login URL
            login_url = "https://app.degoo.com/api/auth/login"
            
            async with session.post(login_url, json=login_data, headers=headers) as response:
                if response.status == 200:
                    login_response = await response.json()
                    if 'token' in login_response:
                        # Save cookies
                        cookies = {
                            "cookies": [
                                {
                                    "domain": "app.degoo.com",
                                    "name": "session",
                                    "value": login_response.get('token', '')
                                },
                                {
                                    "domain": "app.degoo.com",
                                    "name": "auth_token",
                                    "value": login_response.get('token', '')
                                }
                            ]
                        }
                        
                        with open(Config.COOKIES_FILE, 'w') as f:
                            json.dump(cookies, f)
                        
                        return True
                return False
    except Exception as e:
        logger.error(f"Error logging in to Degoo: {e}")
        return False

async def youtube_dl_call_back(bot, update):
    cb_data = update.data
    tg_send_type, youtube_dl_format, youtube_dl_ext, ranom = cb_data.split("|")
    random1 = random_char(5)
    
    save_ytdl_json_path = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{ranom}.json")
    tmp_directory_for_each_user = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{random1}")
    thumb_to_remove_path = None

    try:
        youtube_dl_url = update.message.reply_to_message.text
        
        # Check if URL is Degoo
        if "degoo.com" in youtube_dl_url:
            await update.message.edit_caption(caption="Please send your Degoo email and password in this format:\n\nemail:password")
            
            # Wait for user's response
            try:
                response = await bot.wait_for_message(
                    chat_id=update.message.chat.id,
                    user_id=update.from_user.id,
                    timeout=300  # 5 minutes timeout
                )
                
                if not response or not response.text:
                    await update.message.edit_caption(caption="No credentials provided. Process cancelled.")
                    return
                
                # Parse credentials
                try:
                    email, password = response.text.strip().split(':')
                    email = email.strip()
                    password = password.strip()
                except ValueError:
                    await update.message.edit_caption(caption="Invalid format. Please use format: email:password")
                    return
                
                await update.message.edit_caption(caption="Logging in to Degoo...")
                
                # Try to login with provided credentials
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Content-Type": "application/json",
                        "Origin": "https://app.degoo.com",
                        "Referer": "https://app.degoo.com/login"
                    }
                    
                    login_data = {
                        "email": email,
                        "password": password
                    }
                    
                    login_url = "https://app.degoo.com/api/auth/login"
                    
                    async with session.post(login_url, json=login_data, headers=headers) as response:
                        if response.status == 200:
                            login_response = await response.json()
                            if 'token' in login_response:
                                # Save cookies
                                cookies = {
                                    "cookies": [
                                        {
                                            "domain": "app.degoo.com",
                                            "name": "session",
                                            "value": login_response.get('token', '')
                                        },
                                        {
                                            "domain": "app.degoo.com",
                                            "name": "auth_token",
                                            "value": login_response.get('token', '')
                                        }
                                    ]
                                }
                                
                                with open(Config.COOKIES_FILE, 'w') as f:
                                    json.dump(cookies, f)
                                
                                await update.message.edit_caption(caption="Successfully logged in to Degoo!")
                            else:
                                await update.message.edit_caption(caption="Login failed. Invalid credentials.")
                                return
                        else:
                            await update.message.edit_caption(caption="Login failed. Please check your credentials.")
                            return
                
                # Extract share ID from URL
                share_id = youtube_dl_url.split('/')[-1]
                
                # Download each file
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Origin": "https://app.degoo.com",
                    "Referer": youtube_dl_url,
                    "X-Requested-With": "XMLHttpRequest",
                    "Authorization": f"Bearer {login_response.get('token', '')}"
                }
                
                # Get share info
                share_url = f"https://app.degoo.com/api/share/{share_id}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(share_url, headers=headers) as response:
                        if response.status == 200:
                            share_data = await response.json()
                            if 'files' in share_data:
                                files = share_data['files']
                                for file in files:
                                    file_id = file.get('id')
                                    if file_id:
                                        file_name = file.get('name', 'file')
                                        file_path = os.path.join(tmp_directory_for_each_user, file_name)
                                        
                                        await update.message.edit_caption(caption=f"Downloading {file_name}...")
                                        
                                        # Get download URL
                                        download_url = f"https://app.degoo.com/api/share/{share_id}/file/{file_id}/download"
                                        
                                        # Download file
                                        async with session.get(download_url, headers=headers) as download_response:
                                            if download_response.status == 200:
                                                with open(file_path, 'wb') as f:
                                                    while True:
                                                        chunk = await download_response.content.read(8192)
                                                        if not chunk:
                                                            break
                                                        f.write(chunk)
                                                
                                                await update.message.edit_caption(caption=f"Uploading {file_name}...")
                                                
                                                # Upload the file
                                                if os.path.exists(file_path):
                                                    await update.message.reply_document(
                                                        document=file_path,
                                                        caption=f"Downloaded from Degoo: {file_name}"
                                                    )
                                            else:
                                                await update.message.edit_caption(caption=f"Failed to download {file_name}")
                
                await update.message.edit_caption(caption="All files processed!")
                return
                
            except Exception as e:
                logger.error(f"Error waiting for credentials: {e}")
                await update.message.edit_caption(caption="Process timed out. Please try again.")
                return

        # For non-Degoo URLs, use yt-dlp
        try:
            with open(save_ytdl_json_path, "r", encoding="utf8") as f:
                response_json = json.load(f)
        except FileNotFoundError as e:
            logger.error(f"JSON file [{save_ytdl_json_path}] not found: {e}")
            try:
                await update.message.delete()
            except Exception as del_err:
                logger.error(f"Error deleting message after JSON not found: {del_err}")
            return

        video_title = response_json.get('title', 'Untitled Video')
        if not video_title:
            video_title = 'Untitled Video'
            
        custom_file_name = f"{video_title}_{youtube_dl_format}.{youtube_dl_ext}"
        custom_file_name = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in custom_file_name)

        youtube_dl_username = None
        youtube_dl_password = None
    
        if "|" in youtube_dl_url:
            url_parts = youtube_dl_url.split("|")
            if len(url_parts) == 2:
                youtube_dl_url, custom_file_name_from_url = url_parts
                if custom_file_name_from_url.strip():
                    custom_file_name = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in custom_file_name_from_url.strip())
            elif len(url_parts) == 4:
                youtube_dl_url, custom_file_name_from_url, youtube_dl_username, youtube_dl_password = url_parts
                if custom_file_name_from_url.strip():
                    custom_file_name = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in custom_file_name_from_url.strip())
                if youtube_dl_username:
                    youtube_dl_username = youtube_dl_username.strip()
                if youtube_dl_password:
                    youtube_dl_password = youtube_dl_password.strip()
            else:
                for entity in update.message.reply_to_message.entities:
                    if entity.type == enums.MessageEntityType.TEXT_LINK:
                        youtube_dl_url = entity.url
                        break
                    elif entity.type == enums.MessageEntityType.URL:
                        o = entity.offset
                        l = entity.length
                        youtube_dl_url = update.message.reply_to_message.text[o:o + l]
                        break
            youtube_dl_url = youtube_dl_url.strip() if youtube_dl_url else ""
        else:
            if update.message.reply_to_message.entities:
                for entity in update.message.reply_to_message.entities:
                    if entity.type == enums.MessageEntityType.TEXT_LINK:
                        youtube_dl_url = entity.url
                        break
                    elif entity.type == enums.MessageEntityType.URL:
                        o = entity.offset
                        l = entity.length
                        youtube_dl_url = update.message.reply_to_message.text[o:o + l]
                        break
            if not youtube_dl_url:
                 youtube_dl_url = update.message.reply_to_message.text.strip()

        if not youtube_dl_url:
            logger.error("Could not extract URL from message.")
            await update.message.edit_caption(caption="Could not extract URL.")
            return

        logger.info(f"Processing URL: {youtube_dl_url}")
        logger.info(f"Custom file name: {custom_file_name}")

        await update.message.edit_caption(
            caption=Translation.DOWNLOAD_START.format(custom_file_name, "")
        )
        
        description = Translation.CUSTOM_CAPTION_UL_FILE
        if "fulltitle" in response_json and response_json["fulltitle"]:
            full_title_str = response_json["fulltitle"]
            if isinstance(response_json["fulltitle"], list):
                full_title_str = response_json["fulltitle"][0]

            description = full_title_str[0:1021] if isinstance(full_title_str, str) else Translation.CUSTOM_CAPTION_UL_FILE

        os.makedirs(tmp_directory_for_each_user, exist_ok=True)
        download_directory = os.path.join(tmp_directory_for_each_user, custom_file_name)
        
        command_to_exec = [
            "yt-dlp",
            "-c",
            "--no-part",
            "--max-filesize", str(Config.TG_MAX_FILE_SIZE),
            "--embed-subs",
            "-f", f"bestvideo[height<={youtube_dl_format}]+bestaudio/best[height<={youtube_dl_format}]",
            "--hls-prefer-ffmpeg",
            "--merge-output-format", "mp4",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--referer", "https://app.degoo.com/",
            "--add-header", "Accept: */*",
            "--add-header", "Accept-Language: en-US,en;q=0.9",
            "--add-header", "Origin: https://app.degoo.com",
            "--add-header", "Sec-Fetch-Dest: empty",
            "--add-header", "Sec-Fetch-Mode: cors",
            "--add-header", "Sec-Fetch-Site: same-origin",
            "--extractor-args", "degoo:headers={'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9', 'Origin': 'https://app.degoo.com', 'Referer': 'https://app.degoo.com/'}",
            "--downloader-args", "http:headers={'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9', 'Origin': 'https://app.degoo.com', 'Referer': 'https://app.degoo.com/'}",
            "--retries", "10",
            "--fragment-retries", "10",
            "--file-access-retries", "10",
            "--extractor-retries", "10",
            "--retry-sleep", "5",
            "--yes-playlist",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--embed-metadata",
            "--add-metadata",
            "--playlist-reverse",
            "--no-playlist-reverse",
            "--playlist-items", "all",
            "--extractor-args", "degoo:playlist=True",
            "--extractor-args", "degoo:playlist_items=all",
            "--extractor-args", "degoo:playlist_reverse=False",
            "--extractor-args", "degoo:playlist_start=1",
            "--extractor-args", "degoo:playlist_end=0",
            "--extractor-args", "degoo:playlist_min_items=1",
            "--extractor-args", "degoo:playlist_max_items=0"
        ]
        # Add cookies if available
        if os.path.exists(cookies_file) and os.path.isfile(cookies_file):
            command_to_exec.extend(["--cookies", cookies_file])
        else:
            # Create default Degoo cookies if not exists
            default_cookies = {
                "cookies": [
                    {
                        "domain": "app.degoo.com",
                        "name": "session",
                        "value": "your_session_value_here"
                    },
                    {
                        "domain": "app.degoo.com",
                        "name": "auth_token",
                        "value": "your_auth_token_here"
                    }
                ]
            }
            try:
                with open(cookies_file, 'w') as f:
                    json.dump(default_cookies, f)
                command_to_exec.extend(["--cookies", cookies_file])
                logger.info("Created default Degoo cookies file")
            except Exception as e:
                logger.error(f"Error creating cookies file: {e}")
        
        command_to_exec.extend([
            youtube_dl_url,
            "-o", os.path.join(tmp_directory_for_each_user, "%(playlist_index)s-%(title)s.%(ext)s")
        ])
        
        if Config.HTTP_PROXY:
            command_to_exec.extend(["--proxy", Config.HTTP_PROXY])
        if youtube_dl_username:
            command_to_exec.extend(["--username", youtube_dl_username])
        if youtube_dl_password:
            command_to_exec.extend(["--password", youtube_dl_password])
        
        command_to_exec.append("--no-warnings")
        
        logger.info(f"Executing command: {' '.join(command_to_exec)}")
        start_time_download = datetime.now()
        
        process = await asyncio.create_subprocess_exec(
            *command_to_exec,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await process.communicate()
        e_response = stderr.decode().strip()
        t_response = stdout.decode().strip()
        
        logger.info(f"yt-dlp stderr: {e_response}")
        logger.info(f"yt-dlp stdout: {t_response}")
        
        if process.returncode != 0:
            logger.error(f"yt-dlp command failed with return code {process.returncode}. Error: {e_response}")
            error_display = e_response if e_response else "yt-dlp failed, check logs."
            await update.message.edit_caption(caption=f"Error: {error_display[:1000]}")
            return 

        end_time_download = datetime.now()
        time_taken_for_download = (end_time_download - start_time_download).seconds
        
        file_size = 0
        actual_downloaded_file_path = download_directory
        
        if os.path.exists(download_directory) and os.path.isfile(download_directory):
            file_size = os.stat(download_directory).st_size
        else:
            logger.info(f"File not found at exact path {download_directory}, checking directory {tmp_directory_for_each_user} for alternatives.")
            found_alternative = False
            if os.path.exists(tmp_directory_for_each_user) and os.path.isdir(tmp_directory_for_each_user):
                files_in_dir = os.listdir(tmp_directory_for_each_user)
                potential_files = [f for f in files_in_dir if not f.endswith(f"{ranom}.json")]
                if potential_files:
                    target_file_in_dir = potential_files[0]
                    
                    actual_downloaded_file_path = os.path.join(tmp_directory_for_each_user, target_file_in_dir)
                    if os.path.isfile(actual_downloaded_file_path):
                        file_size = os.stat(actual_downloaded_file_path).st_size
                        logger.info(f"Found downloaded file at alternative path: {actual_downloaded_file_path} with size {file_size}")
                        found_alternative = True
                    else:
                         logger.warning(f"Alternative path {actual_downloaded_file_path} is not a file.")
                else:
                    logger.warning(f"No files (excluding json) found in tmp directory {tmp_directory_for_each_user}")
            
            if not found_alternative:
                logger.error(f"Downloaded file not found. Original path: {download_directory}, and no alternatives in tmp dir.")
                await update.message.edit_caption(caption=Translation.DOWNLOAD_FAILED + " (File not found after download)")
                return

        download_directory = actual_downloaded_file_path

        if file_size == 0:
            logger.error(f"Downloaded file {download_directory} has size 0.")
            await update.message.edit_caption(caption=Translation.DOWNLOAD_FAILED + " (File size is 0)")
            return

        if file_size > Config.TG_MAX_FILE_SIZE:
            await update.message.edit_caption(
                caption=Translation.RCHD_TG_API_LIMIT.format(time_taken_for_download, humanbytes(file_size))
            )
            return 
        
        await update.message.edit_caption(
            caption=Translation.UPLOAD_START.format(os.path.basename(download_directory))
        )
        
        upload_start_time = time.time()

        if tg_send_type == "audio":
            duration = await Mdata03(download_directory)
            thumb_to_remove_path = await Gthumb01(bot, update)
            await update.message.reply_audio(
                audio=download_directory, caption=description, duration=duration,
                thumb=thumb_to_remove_path, progress=progress_for_pyrogram,
                progress_args=(Translation.UPLOAD_START, update.message, upload_start_time)
            )
        elif tg_send_type == "vm":
            width, duration = await Mdata02(download_directory)
            thumb_to_remove_path = await Gthumb02(bot, update, duration, download_directory)
            await update.message.reply_video_note(
                video_note=download_directory, duration=duration, length=width,
                thumb=thumb_to_remove_path, progress=progress_for_pyrogram,
                progress_args=(Translation.UPLOAD_START, update.message, upload_start_time)
            )
        elif not await db.get_upload_as_doc(update.from_user.id):
            thumb_to_remove_path = await Gthumb01(bot, update)
            await update.message.reply_document(
                document=download_directory, thumb=thumb_to_remove_path, caption=description,
                progress=progress_for_pyrogram,
                progress_args=(Translation.UPLOAD_START, update.message, upload_start_time)
            )
        else:
            width, height, duration = await Mdata01(download_directory)
            thumb_to_remove_path = await Gthumb02(bot, update, duration, download_directory)
            await update.message.reply_video(
                video=download_directory, caption=description, duration=duration, width=width, height=height,
                supports_streaming=True, thumb=thumb_to_remove_path, progress=progress_for_pyrogram,
                progress_args=(Translation.UPLOAD_START, update.message, upload_start_time)
            )
        
        logger.info(f"✅ Uploaded: {os.path.basename(download_directory)}")
        upload_end_time = datetime.now()
        time_taken_for_upload = int(time.time() - upload_start_time)

        logger.info(f"✅ Downloaded in: {time_taken_for_download} seconds")
        logger.info(f"✅ Uploaded in: {time_taken_for_upload} seconds")
        
        try:
            await update.message.edit_caption(caption=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download, time_taken_for_upload))
        except Exception as e_edit_final:
            logger.warning(f"Could not edit final success message: {e_edit_final}")

    except Exception as e:
        logger.error(f"An error occurred in youtube_dl_call_back: {e}", exc_info=True)
        try:
            await update.message.edit_caption(caption=f"An unexpected error occurred. Please check logs or try again.")
        except Exception as e_edit:
            logger.error(f"Failed to edit caption on error: {e_edit}")
            
    finally:
        logger.info(f"Cleaning up temporary files for user {update.from_user.id}...")
        try:
            if save_ytdl_json_path and os.path.exists(save_ytdl_json_path):
                os.remove(save_ytdl_json_path)
                logger.info(f"Removed JSON file: {save_ytdl_json_path}")
        except Exception as e_json:
            logger.error(f"Error removing JSON file {save_ytdl_json_path}: {e_json}")

        try:
            if thumb_to_remove_path and os.path.exists(thumb_to_remove_path):
                os.remove(thumb_to_remove_path)
                logger.info(f"Removed thumbnail file: {thumb_to_remove_path}")
        except Exception as e_thumb:
            logger.error(f"Error removing thumbnail {thumb_to_remove_path}: {e_thumb}")

        try:
            if tmp_directory_for_each_user and os.path.exists(tmp_directory_for_each_user):
                shutil.rmtree(tmp_directory_for_each_user)
                logger.info(f"Removed temporary directory: {tmp_directory_for_each_user}")
        except Exception as e_dir:
            logger.error(f"Error removing temporary directory {tmp_directory_for_each_user}: {e_dir}")
        
        logger.info(f"Cleanup process finished for user {update.from_user.id}.")
