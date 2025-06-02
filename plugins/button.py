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
cookies_file = Config.COOKIES_FILE
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
    tmp_directory_for_each_user = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{random1}")
    thumb_to_remove_path = None

    try:
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

        youtube_dl_url = update.message.reply_to_message.text
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
            caption=Translation.DOWNLOAD_START.format(custom_file_name)
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
            "-f", youtube_dl_format,
            "--hls-prefer-ffmpeg",
        ]
        if os.path.exists(cookies_file) and os.path.isfile(cookies_file):
            command_to_exec.extend(["--cookies", cookies_file])
        command_to_exec.extend([
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            youtube_dl_url,
            "-o", download_directory
        ])
        
        if tg_send_type == "audio":
            command_to_exec = [
                "yt-dlp",
                "-c",
                "--no-part",
                "--max-filesize", str(Config.TG_MAX_FILE_SIZE),
                "--bidi-workaround",
                "--extract-audio",
            ]
            if os.path.exists(cookies_file) and os.path.isfile(cookies_file):
                command_to_exec.extend(["--cookies", cookies_file])
            command_to_exec.extend([
                "--audio-format", youtube_dl_ext,
                "--audio-quality", youtube_dl_format,
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                youtube_dl_url,
                "-o", download_directory
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
            logger.error(f"Error removing directory {tmp_directory_for_each_user}: {e_dir}")
        
        logger.info(f"Cleanup process finished for user {update.from_user.id}.")
