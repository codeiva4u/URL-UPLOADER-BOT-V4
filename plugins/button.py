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
from plugins.functions.help_Nekmo_ffmpeg import ensure_audio_video_sync
cookies_file = 'cookies.txt'
# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

async def youtube_dl_call_back(bot, update):
    cb_data = update.data
    tg_send_type, youtube_dl_format, youtube_dl_ext, ranom = cb_data.split("|")
    random1 = random_char(5)
    
    save_ytdl_json_path = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{ranom}.json")
    
    try:
        with open(save_ytdl_json_path, "r", encoding="utf8") as f:
            response_json = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"JSON file not found: {e}")
        await update.message.delete()
        return False
    
    youtube_dl_url = update.message.reply_to_message.text
    custom_file_name = f"{response_json.get('title')}_{youtube_dl_format}.{youtube_dl_ext}"
    # Clean filename by removing special characters
    custom_file_name = "".join(c for c in custom_file_name if c.isalnum() or c in (' ', '-', '_', '.'))
    youtube_dl_username = None
    youtube_dl_password = None
    
    if "|" in youtube_dl_url:
        url_parts = youtube_dl_url.split("|")
        if len(url_parts) == 2:
            youtube_dl_url, custom_file_name = url_parts
        elif len(url_parts) == 4:
            youtube_dl_url, custom_file_name, youtube_dl_username, youtube_dl_password = url_parts
        else:
            for entity in update.message.reply_to_message.entities:
                if entity.type == "text_link":
                    youtube_dl_url = entity.url
                elif entity.type == "url":
                    o = entity.offset
                    l = entity.length
                    youtube_dl_url = youtube_dl_url[o:o + l]
                    
        youtube_dl_url = youtube_dl_url.strip()
        custom_file_name = custom_file_name.strip()
        if youtube_dl_username:
            youtube_dl_username = youtube_dl_username.strip()
        if youtube_dl_password:
            youtube_dl_password = youtube_dl_password.strip()
        
        logger.info(youtube_dl_url)
        logger.info(custom_file_name)
    else:
        for entity in update.message.reply_to_message.entities:
            if entity.type == "text_link":
                youtube_dl_url = entity.url
            elif entity.type == "url":
                o = entity.offset
                l = entity.length
                youtube_dl_url = youtube_dl_url[o:o + l]

    await update.message.edit_caption(
        caption=Translation.DOWNLOAD_START.format(custom_file_name)
    )
    
    description = Translation.CUSTOM_CAPTION_UL_FILE
    if "fulltitle" in response_json:
        description = response_json["fulltitle"][0:1021]
    
    tmp_directory_for_each_user = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{random1}")
    os.makedirs(tmp_directory_for_each_user, exist_ok=True)
    download_directory = os.path.join(tmp_directory_for_each_user, custom_file_name)
    
    command_to_exec = [
        "yt-dlp",
        "-c",
        "--max-filesize", str(Config.TG_MAX_FILE_SIZE),
        "--embed-subs",
        # Assuming youtube_dl_format is a specific format code (e.g., "22" for 720p, "137" for 1080p video-only).
        # If it's a quality string like "720p", the logic to select format codes needs to be upstream
        # or this needs to be more complex. For now, direct use of youtube_dl_format as a format code.
        "-f", youtube_dl_format,
        "--hls-prefer-ffmpeg",
        "--cookies", cookies_file,
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        youtube_dl_url,
        "-o", download_directory,
        "--no-warnings"
    ]
    
    if tg_send_type == "audio":
        command_to_exec = [
            "yt-dlp",
            "-c",
            "--max-filesize", str(Config.TG_MAX_FILE_SIZE),
            "--bidi-workaround",
            "--extract-audio",
            "--cookies", cookies_file,
            "--audio-format", youtube_dl_ext,
            "--audio-quality", youtube_dl_format,
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            youtube_dl_url,
            "-o", download_directory
        ]
    
    if Config.HTTP_PROXY:
        command_to_exec.extend(["--proxy", Config.HTTP_PROXY])
    if youtube_dl_username:
        command_to_exec.extend(["--username", youtube_dl_username])
    if youtube_dl_password:
        command_to_exec.extend(["--password", youtube_dl_password])
    
    logger.info(command_to_exec)
    start = datetime.now()
    
    process = await asyncio.create_subprocess_exec(
        *command_to_exec,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    logger.info(e_response)
    logger.info(t_response)
    
    if process.returncode != 0:
        logger.error(f"yt-dlp command failed with return code {process.returncode}")
        await update.message.edit_caption(
            caption=f"Error: {e_response}"
        )
        return False
    
    ad_string_to_replace = "**Invalid link !**"
    if e_response and ad_string_to_replace in e_response:
        error_message = e_response.replace(ad_string_to_replace, "")
        await update.message.edit_caption(
            text=error_message
        )
        return False

    if t_response:
        logger.info(t_response)
        try:
            os.remove(save_ytdl_json_path)
        except FileNotFoundError:
            pass
        
        end_one = datetime.now()
        time_taken_for_download = (end_one - start).seconds
        
        if os.path.isfile(download_directory):
            file_size = os.stat(download_directory).st_size
        else:
            base_name = os.path.splitext(download_directory)[0]
            download_directory = f"{base_name}.mp4"
            if os.path.isfile(download_directory):
                file_size = os.stat(download_directory).st_size
            else:
                logger.error(f"Downloaded file not found: {download_directory}")
                await update.message.edit_caption(
                    caption=Translation.DOWNLOAD_FAILED
                )
                return False
        
        if file_size > Config.TG_MAX_FILE_SIZE:
            await update.message.edit_caption(
                caption=Translation.RCHD_TG_API_LIMIT.format(time_taken_for_download, humanbytes(file_size))
            )
        else:
            await update.message.edit_caption(
                caption="Processing video to ensure audio-video synchronization..."
            )
            
            # Get the directory path for processing
            process_dir = os.path.dirname(download_directory)
            
            # Apply audio-video synchronization
            synced_file = await ensure_audio_video_sync(download_directory, process_dir)
            
            await update.message.edit_caption(
                caption=Translation.UPLOAD_START.format(custom_file_name)
            )
            start_time = time.time()
            if not await db.get_upload_as_doc(update.from_user.id):
                thumbnail = await Gthumb01(bot, update)
                await update.message.reply_document(
                    document=synced_file,
                    thumb=thumbnail,
                    caption=description,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
            else:
                width, height, duration = await Mdata01(synced_file)
                thumb_image_path = await Gthumb02(bot, update, duration, synced_file)
                await update.message.reply_video(
                    video=synced_file,
                    caption=description,
                    duration=duration,
                    width=width,
                    height=height,
                    supports_streaming=True,
                    thumb=thumb_image_path,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
            
            if tg_send_type == "audio":
                duration = await Mdata03(download_directory)
                thumbnail = await Gthumb01(bot, update)
                await update.message.reply_audio(
                    audio=download_directory,
                    caption=description,
                    duration=duration,
                    thumb=thumbnail,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
            elif tg_send_type == "vm":
                width, duration = await Mdata02(download_directory)
                thumbnail = await Gthumb02(bot, update, duration, download_directory)
                await update.message.reply_video_note(
                    video_note=download_directory,
                    duration=duration,
                    length=width,
                    thumb=thumbnail,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
            else:
                logger.info("Downloaded file: " + custom_file_name)
            
            end_two = datetime.now()
            time_taken_for_upload = (end_two - end_one).seconds
            
            # Store thumbnail path before cleanup
            thumbnail_path = None
            if 'thumbnail' in locals():
                thumbnail_path = thumbnail
            
            try:
                # Wait longer before cleanup to ensure file is released
                await asyncio.sleep(5)
                
                # First try to remove the specific downloaded file
                if os.path.exists(download_directory):
                    try:
                        os.remove(download_directory)
                        logger.info("Successfully removed downloaded file: " + download_directory)
                    except Exception as e:
                        logger.error("Error removing downloaded file " + download_directory + ": " + str(e))
                        # Try to force close any handles to the file
                        try:
                            import psutil
                            for proc in psutil.process_iter(['pid', 'open_files']):
                                try:
                                    for file in proc.open_files():
                                        if download_directory in file.path:
                                            proc.kill()
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                            # Try removing again after killing processes
                            if os.path.exists(download_directory):
                                os.remove(download_directory)
                        except Exception as e2:
                            logger.error("Failed to force remove file: " + str(e2))
                
                # Then cleanup the temporary user directory
                tmp_dir = os.path.dirname(download_directory)
                if os.path.exists(tmp_dir):
                    try:
                        shutil.rmtree(tmp_dir)
                        logger.info("Successfully cleaned up temporary directory: " + tmp_dir)
                    except Exception as e:
                        logger.error("Error cleaning up temporary directory " + tmp_dir + ": " + str(e))
                
                # Remove thumbnail if exists
                if thumbnail_path and os.path.exists(thumbnail_path):
                    try:
                        os.remove(thumbnail_path)
                        logger.info("Successfully removed thumbnail: " + thumbnail_path)
                    except Exception as e:
                        logger.error("Error removing thumbnail: " + str(e))
                
            except Exception as e:
                logger.error("Error in cleanup process: " + str(e))
            
            await update.message.edit_caption(
                caption=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download, time_taken_for_upload)
            )
            
            logger.info("Downloaded in: " + str(time_taken_for_download) + " seconds")
            logger.info("Uploaded in: " + str(time_taken_for_upload) + " seconds")
