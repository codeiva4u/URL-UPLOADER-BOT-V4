# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL

import logging
import asyncio
import json
import os
import shutil
import time
import math
from datetime import datetime
from pyrogram import enums
from pyrogram.types import InputMediaPhoto
from plugins.config import Config
from plugins.script import Translation
from plugins.thumbnail import *
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes, string_to_bytes
from plugins.database.database import db
from PIL import Image
from plugins.functions.ran_text import random_char
# from plugins.config import Config # पहले ही import हो चुका है
cookies_file = Config.COOKIES_FILE
# Set up logging
# logging.basicConfig(level=logging.DEBUG, # यह रूट लॉगर को कॉन्फ़िगर करता है, स्थानीय रूप से ठीक है
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # स्थानीय लॉगर का उपयोग करें
# logging.getLogger("pyrogram").setLevel(logging.WARNING) # यह भी रूट लॉगर को प्रभावित कर सकता है, यदि आवश्यक हो तो ठीक है

async def youtube_dl_call_back(bot, update):
    cb_data = update.data
    tg_send_type, youtube_dl_format, youtube_dl_ext, ranom = cb_data.split("|")
    random1 = random_char(5) # tmp डायरेक्टरी के लिए
    
    # क्लीनअप के लिए वेरिएबल्स को None से प्रारंभ करें
    save_ytdl_json_path = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{ranom}.json")
    tmp_directory_for_each_user = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{random1}")
    thumb_to_remove_path = None # थंबनेल का पाथ स्टोर करने के लिए

    # मुख्य लॉजिक को try ब्लॉक में रखें
    try:
        try:
            with open(save_ytdl_json_path, "r", encoding="utf8") as f:
                response_json = json.load(f)
        except FileNotFoundError as e:
            logger.error(f"JSON file [{save_ytdl_json_path}] not found: {e}")
            try: # मैसेज को डिलीट करने का प्रयास करें
                await update.message.delete()
            except Exception as del_err:
                logger.error(f"Error deleting message after JSON not found: {del_err}")
            return # यहाँ से बाहर निकलें, finally क्लीनअप करेगा

        youtube_dl_url = update.message.reply_to_message.text
        # response_json से 'title' प्राप्त करने का प्रयास करें, यदि नहीं मिलता है तो 'Untitled Video' का उपयोग करें
        video_title = response_json.get('title', 'Untitled Video')
        if not video_title: # यदि शीर्षक खाली स्ट्रिंग है
            video_title = 'Untitled Video'
            
        custom_file_name = f"{video_title}_{youtube_dl_format}.{youtube_dl_ext}"
        # संभावित अवैध वर्णों को फ़ाइल नाम से हटाएं
        custom_file_name = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in custom_file_name)


        youtube_dl_username = None
        youtube_dl_password = None
    
        if "|" in youtube_dl_url:
            url_parts = youtube_dl_url.split("|")
            if len(url_parts) == 2:
                youtube_dl_url, custom_file_name_from_url = url_parts
                if custom_file_name_from_url.strip(): # यदि url से फ़ाइल नाम प्रदान किया गया है
                    custom_file_name = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in custom_file_name_from_url.strip())
            elif len(url_parts) == 4:
                youtube_dl_url, custom_file_name_from_url, youtube_dl_username, youtube_dl_password = url_parts
                if custom_file_name_from_url.strip():
                    custom_file_name = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in custom_file_name_from_url.strip())
                if youtube_dl_username:
                    youtube_dl_username = youtube_dl_username.strip()
                if youtube_dl_password:
                    youtube_dl_password = youtube_dl_password.strip()
            else: # अप्रत्याशित संख्या में पार्ट्स, केवल url निकालें
                if update.message.reply_to_message.entities:
                    for entity in update.message.reply_to_message.entities:
                        if entity.type == enums.MessageEntityType.TEXT_LINK:
                            youtube_dl_url = entity.url
                            break # पहला लिंक मिलने पर बाहर निकलें
                        elif entity.type == enums.MessageEntityType.URL:
                            o = entity.offset
                            l = entity.length
                            youtube_dl_url = update.message.reply_to_message.text[o:o + l]
                            break # पहला लिंक मिलने पर बाहर निकलें
            youtube_dl_url = youtube_dl_url.strip() if youtube_dl_url else ""
        else: # कोई "|" नहीं, मैसेज से url निकालें
            # entities की जाँच करें
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
            if not youtube_dl_url: # यदि entities से नहीं मिला
                 youtube_dl_url = update.message.reply_to_message.text.strip()


        if not youtube_dl_url:
            logger.error("Could not extract URL from message.")
            await update.message.edit_caption(caption="Could not extract URL.")
            return

        logger.info(f"Processing URL: {youtube_dl_url}")
        logger.info(f"Custom file name: {custom_file_name}")

        # डाउनलोड प्रगति संदेश (यदि आवश्यक हो)
        # आप चाहें तो इस संदेश को कस्टमाइज़ कर सकते हैं या इसे पूरी तरह से हटा सकते हैं
        # और केवल अपलोड के दौरान प्रगति दिखा सकते हैं।
        # अभी के लिए, मैं इसे Translation.DOWNLOAD_START के साथ रखता हूँ।
        # await update.message.edit_caption(
        #     caption=Translation.DOWNLOAD_START.format(custom_file_name) 
        # )

        # डाउनलोड शुरू होने पर स्थैतिक प्रगति बार दिखाएं
        ud_type_download_str = "📥 Downloading... 📥"
        progress_bar_static = ''.join(["░░░░" for i in range(12)])
        percentage_static = 0.0
        current_bytes_static = humanbytes(0)
        total_bytes_static = humanbytes(0) 
        speed_static = humanbytes(0)
        eta_static = "0 s"

        progress_details_static = Translation.PROGRESS.format(
            f"{percentage_static:.2f}",
            current_bytes_static,
            total_bytes_static,
            speed_static,
            eta_static
        )
        
        tmp_static_payload = (
            f"File Name: {custom_file_name}\n"
            f"{progress_bar_static}\n"
            f"P: {percentage_static:.2f}%\n"
            f"{progress_details_static}"
        )

        static_download_caption = Translation.PROGRES.format(ud_type_download_str, tmp_static_payload)
        
        await update.message.edit_caption(
            caption=static_download_caption
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
            "-f", f"{youtube_dl_format}bestvideo+bestaudio/best", 
            "--hls-prefer-ffmpeg", 
            "--progress-hooks", # Use progress hooks for JSON output
            "--progress-template", "hook:{\"status\": \"%(progress.status)s\", \"downloaded_bytes\": \"%(progress._downloaded_bytes_str)s\", \"total_bytes\": \"%(progress._total_bytes_str)s\", \"total_bytes_estimate\": \"%(progress._total_bytes_estimate_str)s\", \"speed\": \"%(progress._speed_str)s\", \"eta\": \"%(progress._eta_str)s\", \"filename\": \"%(info.filename)s\", \"percentage\": \"%(progress._percent_str)s\"}"
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
                "--progress-hooks", # Use progress hooks for JSON output
                "--progress-template", "hook:{\"status\": \"%(progress.status)s\", \"downloaded_bytes\": \"%(progress._downloaded_bytes_str)s\", \"total_bytes\": \"%(progress._total_bytes_str)s\", \"total_bytes_estimate\": \"%(progress._total_bytes_estimate_str)s\", \"speed\": \"%(progress._speed_str)s\", \"eta\": \"%(progress._eta_str)s\", \"filename\": \"%(info.filename)s\", \"percentage\": \"%(progress._percent_str)s\"}"
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
        
        # yt-dlp से डाउनलोड प्रगति को कैप्चर करना मुश्किल है क्योंकि यह stdout पर प्रिंट करता है
        # और इसे parse करना होगा। Pyrogram का progress callback अपलोड के लिए है।
        # डाउनलोड के लिए, हम केवल एक सामान्य "Downloading..." संदेश दिखा सकते हैं।
        # या yt-dlp के stdout को लगातार पढ़ने और संदेश को अपडेट करने के लिए एक अधिक जटिल समाधान लागू करें।
        # सिंप्लिसिटी के लिए, हम डाउनलोड के दौरान एक स्थिर संदेश रखेंगे।

        process = await asyncio.create_subprocess_exec(
            *command_to_exec,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        # stdout, stderr = await process.communicate() # We will read stdout line by line

        last_update_time = time.time()
        # DOWNLOAD_START and other variables are already defined from the static part.
        # We'll reuse them or update as needed.
        
        async for line_bytes in process.stdout:
            line = line_bytes.decode('utf-8', errors='ignore').strip()
            if line.startswith("hook:"):
                try:
                    progress_data_json = line[len("hook:"):]
                    progress_data = json.loads(progress_data_json)

                    status = progress_data.get("status")
                    if status == "downloading":
                        current_time = time.time()
                        if current_time - last_update_time < Config.EDIT_SLEEP_TIME_OUT: # Update message sparingly
                            continue
                        last_update_time = current_time

                        downloaded_bytes_str = progress_data.get("downloaded_bytes", "0B")
                        total_bytes_str = progress_data.get("total_bytes") or progress_data.get("total_bytes_estimate", "0B")
                        
                        current = string_to_bytes(downloaded_bytes_str)
                        total = string_to_bytes(total_bytes_str)
                        
                        # Ensure total is not zero to avoid division by zero
                        if total == 0 and current > 0: # If total is unknown but we have current bytes
                            percentage = 0 # Or handle as unknown progress
                        elif total == 0 and current == 0:
                             percentage = 0
                        else:
                            percentage = (current * 100) / total if total > 0 else 0.0


                        speed_str = progress_data.get("speed", "0B/s")
                        eta_str = progress_data.get("eta", "0s")
                        filename_progress = progress_data.get("filename", custom_file_name) # Use actual filename if available

                        # Use progress_for_pyrogram arguments style to build the message
                        # progress bar generation
                        progress_bar = "{0}{1}".format(
                            ''.join(["████" for i in range(math.floor(percentage * 0.1))]),
                            ''.join(["░░░░" for i in range(12 - math.floor(percentage * 0.1))])
                        )

                        progress_details = Translation.PROGRESS.format(
                            f"{percentage:.2f}",
                            humanbytes(current),
                            humanbytes(total) if total > 0 else "Unknown", # Show unknown if total is 0
                            speed_str, # yt-dlp provides speed already formatted
                            eta_str    # yt-dlp provides eta already formatted
                        )
                        
                        # Include filename in the tmp_payload if desired, or stick to custom_file_name
                        tmp_payload = (
                            f"File Name: {os.path.basename(filename_progress)}\n" 
                            f"{progress_bar}\n"
                            f"P: {percentage:.2f}%\n"
                            f"{progress_details}"
                        )
                        
                        download_caption = Translation.PROGRES.format(ud_type_download_str, tmp_payload)
                        
                        try:
                            await update.message.edit_caption(caption=download_caption)
                        except Exception as e_edit:
                            logger.warning(f"Error updating download progress caption: {e_edit}")
                    elif status == "finished":
                        logger.info(f"yt-dlp status: finished for {progress_data.get('filename')}")
                    elif status == "error":
                         logger.error(f"yt-dlp status: error for {progress_data.get('filename')}")

                except json.JSONDecodeError:
                    logger.debug(f"yt-dlp non-JSON stdout: {line}") # Log non-JSON lines for debugging
                except Exception as e_prog:
                    logger.error(f"Error processing yt-dlp progress line: {e_prog} | Line: {line}")
            else:
                if line: # Log other non-empty stdout lines
                    logger.info(f"yt-dlp other stdout: {line}")

        await process.wait() # Wait for the process to complete
        
        stderr_bytes = await process.stderr.read() # Read stderr after process completion
        e_response = stderr_bytes.decode().strip()
        # t_response = stdout.decode().strip() # stdout was consumed line by line
        
        logger.info(f"yt-dlp stderr: {e_response}")
        # logger.info(f"yt-dlp stdout: {t_response}") # t_response no longer holds full stdout

        end_time_download = datetime.now()
        time_taken_for_download = (end_time_download - start_time_download).seconds
        
        file_size = 0
        actual_downloaded_file_path = download_directory 
        
        if os.path.exists(download_directory) and os.path.isfile(download_directory):
            file_size = os.stat(download_directory).st_size
        else:
            # यदि मूल नाम से फ़ाइल नहीं मिलती है, तो डायरेक्टरी में देखें
            # क्योंकि yt-dlp कभी-कभी एक्सटेंशन या नाम बदल सकता है
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
        
        # अपलोड प्रगति संदेश
        # यहाँ Translation.UPLOAD_START का उपयोग किया जा सकता है, या एक सरल "Uploading..."
        upload_caption = Translation.UPLOAD_START.format(os.path.basename(download_directory))
        await update.message.edit_caption(caption=upload_caption) 
        
        upload_start_time = time.time()

        if tg_send_type == "audio":
            duration = await Mdata03(download_directory)
            thumb_to_remove_path = await Gthumb01(bot, update)
            await update.message.reply_audio(
                audio=download_directory, caption=description, duration=duration,
                thumb=thumb_to_remove_path,
                progress=progress_for_pyrogram,
                progress_args=(upload_caption, update.message, upload_start_time)
            )
        elif tg_send_type == "vm":
            width, duration = await Mdata02(download_directory)
            thumb_to_remove_path = await Gthumb02(bot, update, duration, download_directory)
            await update.message.reply_video_note(
                video_note=download_directory, duration=duration, length=width,
                thumb=thumb_to_remove_path,
                progress=progress_for_pyrogram,
                progress_args=(upload_caption, update.message, upload_start_time)
            )
        elif not await db.get_upload_as_doc(update.from_user.id):
            thumb_to_remove_path = await Gthumb01(bot, update)
            await update.message.reply_document(
                document=download_directory, thumb=thumb_to_remove_path, caption=description,
                progress=progress_for_pyrogram,
                progress_args=(upload_caption, update.message, upload_start_time)
            )
        else: 
            width, height, duration = await Mdata01(download_directory)
            thumb_to_remove_path = await Gthumb02(bot, update, duration, download_directory)
            await update.message.reply_video(
                video=download_directory, caption=description, duration=duration, width=width, height=height,
                supports_streaming=True, thumb=thumb_to_remove_path,
                progress=progress_for_pyrogram,
                progress_args=(upload_caption, update.message, upload_start_time)
            )
        
        logger.info(f"✅ Uploaded: {os.path.basename(download_directory)}")
        time_taken_for_upload = int(time.time() - upload_start_time)

        logger.info(f"✅ Downloaded in: {time_taken_for_download} seconds")
        logger.info(f"✅ Uploaded in: {time_taken_for_upload} seconds")
        
        try:
            final_caption = Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download, time_taken_for_upload)
            # सुनिश्चित करें कि अंतिम कैप्शन मूल संदेश को एडिट करे, न कि नए रिप्लाई को
            if update.message.caption:
                 await update.message.edit_caption(caption=final_caption)
            else:
                # यदि मूल संदेश में कोई कैप्शन नहीं था (जो कॉलबैक क्वेरी के लिए असामान्य है),
                # तो अंतिम फ़ाइल के साथ एक नया संदेश भेजें या मौजूदा को एडिट करने का प्रयास करें।
                # सिंप्लिसिटी के लिए, हम मानते हैं कि update.message में हमेशा कैप्शन होता है जिसे एडिट किया जा सकता है।
                # यदि reply_audio/video आदि एक नया संदेश लौटाते हैं, तो उसे एडिट करना होगा।
                # वर्तमान में, वे None लौटाते हैं, इसलिए हम update.message (कॉलबैक क्वेरी का संदेश) को एडिट करते हैं।
                pass # edit_caption ऊपर किया गया है

        except Exception as e_edit_final:
            logger.warning(f"Could not edit final success message: {e_edit_final}")

    except Exception as e:
        logger.error(f"An error occurred in youtube_dl_call_back: {e}", exc_info=True)
        try:
            await update.message.edit_caption(caption=f"An unexpected error occurred. Please check logs or try again.")
        except Exception as e_edit:
            logger.error(f"Failed to edit caption on error: {e_edit}")
            
    finally:
        # क्लीनअप लॉजिक यहाँ आएगा
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
