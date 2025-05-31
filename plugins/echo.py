# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL | TG-SORRY


import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
import requests, urllib.parse, filetype, os, time, shutil, tldextract, asyncio, json, math
from PIL import Image
from plugins.config import Config
from plugins.script import Translation
logging.getLogger("pyrogram").setLevel(logging.WARNING)
from pyrogram import filters
import os
import time
import random
from pyrogram import enums
from pyrogram import Client
from plugins.functions.verify import verify_user, check_token, check_verification, get_token
from plugins.functions.forcesub import handle_force_subscribe
from plugins.functions.display_progress import humanbytes
from plugins.functions.help_uploadbot import DownLoadFile
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes, TimeFormatter
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from plugins.functions.ran_text import random_char
from plugins.database.database import db
from plugins.database.add import AddUser
from pyrogram.types import Thumbnail
from plugins.config import Config
cookies_file = Config.COOKIES_FILE

def check_cookies_file():
    if not os.path.exists(cookies_file):
        logger.error(f"Cookies file not found at {cookies_file}")
        return False
    if os.path.getsize(cookies_file) == 0:
        logger.error("Cookies file is empty")
        return False
    return True

@Client.on_message(filters.private & filters.regex(pattern=".*http.*"))
async def echo(bot, update):
    if update.from_user.id != Config.OWNER_ID:  
        if not await check_verification(bot, update.from_user.id) and Config.TRUE_OR_FALSE:
            button = [[
                InlineKeyboardButton("✓⃝ Vᴇʀɪꜰʏ ✓⃝", url=await get_token(bot, update.from_user.id, f"https://telegram.me/{Config.BOT_USERNAME}?start="))
                ],[
                InlineKeyboardButton("🔆 Wᴀᴛᴄʜ Hᴏᴡ Tᴏ Vᴇʀɪꜰʏ 🔆", url=f"{Config.VERIFICATION}")
            ]]
            await update.reply_text(
                text="<b>Pʟᴇᴀsᴇ Vᴇʀɪꜰʏ Fɪʀsᴛ Tᴏ Usᴇ Mᴇ</b>",
                protect_content=True,
                reply_markup=InlineKeyboardMarkup(button)
            )
            return

    # Check cookies file before proceeding
    if not check_cookies_file():
        await update.reply_text(
            text="⚠️ YouTube authentication is not properly configured. Please contact the bot administrator.",
            disable_web_page_preview=True
        )
        return

    if Config.LOG_CHANNEL:
        try:
            log_message = await update.forward(Config.LOG_CHANNEL)
            log_info = "Message Sender Information\n"
            log_info += "\nFirst Name: " + update.from_user.first_name
            log_info += "\nUser ID: " + str(update.from_user.id)
            log_info += "\nUsername: @" + (update.from_user.username if update.from_user.username else "")
            log_info += "\nUser Link: " + update.from_user.mention
            await log_message.reply_text(
                text=log_info,
                disable_web_page_preview=True,
                quote=True
            )
        except Exception as error:
            logger.error(f"Error in logging: {error}")

    if not update.from_user:
        return await update.reply_text("I don't know about you sar :(")
    
    await AddUser(bot, update)
    if Config.UPDATES_CHANNEL:
        fsub = await handle_force_subscribe(bot, update)
        if fsub == 400:
            return

    logger.info(update.from_user)
    url = update.text
    youtube_dl_username = None
    youtube_dl_password = None
    file_name = None

    print(url)
    if "|" in url:
        url_parts = url.split("|")
        if len(url_parts) == 2:
            url = url_parts[0]
            file_name = url_parts[1]
        elif len(url_parts) == 4:
            url = url_parts[0]
            file_name = url_parts[1]
            youtube_dl_username = url_parts[2]
            youtube_dl_password = url_parts[3]
        else:
            for entity in update.entities:
                if entity.type == "text_link":
                    url = entity.url
                elif entity.type == "url":
                    o = entity.offset
                    l = entity.length
                    url = url[o:o + l]
        if url is not None:
            url = url.strip()
        if file_name is not None:
            file_name = file_name.strip()
        if youtube_dl_username is not None:
            youtube_dl_username = youtube_dl_username.strip()
        if youtube_dl_password is not None:
            youtube_dl_password = youtube_dl_password.strip()
        logger.info(url)
        logger.info(file_name)
    else:
        for entity in update.entities:
            if entity.type == "text_link":
                url = entity.url
            elif entity.type == "url":
                o = entity.offset
                l = entity.length
                url = url[o:o + l]

    # Base command with cookies
    command_to_exec = [
        "yt-dlp",
        "--no-warnings",
        "--allow-dynamic-mpd",
        "--no-check-certificate",
        "--cookies", cookies_file,
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "-j",
        url
    ]

    # Add proxy if configured
    if Config.HTTP_PROXY:
        command_to_exec.extend(["--proxy", Config.HTTP_PROXY])
    else:
        command_to_exec.extend(["--geo-bypass-country", "IN"])

    # Add credentials if provided
    if youtube_dl_username:
        command_to_exec.extend(["--username", youtube_dl_username])
    if youtube_dl_password:
        command_to_exec.extend(["--password", youtube_dl_password])

    logger.info(f"Executing command: {' '.join(command_to_exec)}")
    
    chk = await bot.send_message(
        chat_id=update.chat.id,
        text=f'ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ʟɪɴᴋ ⌛',
        disable_web_page_preview=True,
        reply_to_message_id=update.id,
        parse_mode=enums.ParseMode.HTML
    )

    try:
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

        if e_response and "nonnumeric port" not in e_response:
            error_message = e_response.replace("please report this issue on https://yt-dl.org/bug . Make sure you are using the latest version; see  https://yt-dl.org/update  on how to update. Be sure to call youtube-dl with the --verbose flag and include its complete output.", "")
            
            if "Sign in to confirm you're not a bot" in error_message:
                error_message = "⚠️ YouTube authentication failed. Please ensure the cookies file is valid and up to date."
            elif "This video is only available for registered users." in error_message:
                error_message += Translation.SET_CUSTOM_USERNAME_PASSWORD
            
            await chk.delete()
            await bot.send_message(
                chat_id=update.chat.id,
                text=Translation.NO_VOID_FORMAT_FOUND.format(str(error_message)),
                reply_to_message_id=update.id,
                disable_web_page_preview=True
            )
            return False

        if t_response:
            x_reponse = t_response
            if "\n" in x_reponse:
                x_reponse, _ = x_reponse.split("\n")
            response_json = json.loads(x_reponse)
            randem = random_char(5)
            save_ytdl_json_path = Config.DOWNLOAD_LOCATION + \
                "/" + str(update.from_user.id) + f'{randem}' + ".json"
            with open(save_ytdl_json_path, "w", encoding="utf8") as outfile:
                json.dump(response_json, outfile, ensure_ascii=False)

            inline_keyboard = []
            duration = None
            if "duration" in response_json:
                duration = response_json["duration"]
            if "formats" in response_json:
                for formats in response_json["formats"]:
                    format_id = formats.get("format_id")
                    format_string = formats.get("format_note")
                    if format_string is None:
                        format_string = formats.get("format")
                    if "DASH" in format_string.upper():
                        continue
                    
                    format_ext = formats.get("ext")
                    if formats.get('filesize'):
                        size = formats['filesize']
                    elif formats.get('filesize_approx'):
                        size = formats['filesize_approx']
                    else:
                        size = 0
                    
                    if "audio only" in format_string.lower():
                        continue

                    # Add quality indicator
                    quality = ""
                    if "2160" in format_string or "4k" in format_string.lower():
                        quality = "4K"
                    elif "1440" in format_string:
                        quality = "2K"
                    elif "1080" in format_string:
                        quality = "1080p"
                    elif "720" in format_string:
                        quality = "720p"
                    elif "480" in format_string:
                        quality = "480p"
                    elif "360" in format_string:
                        quality = "360p"
                    elif "240" in format_string:
                        quality = "240p"
                    elif "144" in format_string:
                        quality = "144p"
                        
                    cb_string_video = "{}|{}|{}|{}".format(
                        "video", format_id, format_ext, randem)
                    
                    inline_keyboard.append([
                        InlineKeyboardButton(
                            f"🎥 {quality} {format_ext.upper()} {humanbytes(size)}",
                            callback_data=cb_string_video.encode("UTF-8")
                        )
                    ])
            else:
                format_id = response_json["format_id"]
                format_ext = response_json["ext"]
                cb_string_video = "{}|{}|{}|{}".format(
                    "video", format_id, format_ext, randem)
                inline_keyboard.append([
                    InlineKeyboardButton(
                        "📁 Document",
                        callback_data=(cb_string_video).encode("UTF-8")
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            await chk.delete()
            await bot.send_message(
                chat_id=update.chat.id,
                text=Translation.FORMAT_SELECTION.format(Thumbnail) + "\n" + Translation.SET_CUSTOM_USERNAME_PASSWORD,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                reply_to_message_id=update.id
            )
        else:
            inline_keyboard = []
            cb_string_file = "{}={}={}".format(
                "file", "LFO", "NONE")
            cb_string_video = "{}={}={}".format(
                "video", "OFL", "ENON")
            inline_keyboard.append([
                InlineKeyboardButton(
                    "📁 ᴍᴇᴅɪᴀ",
                    callback_data=(cb_string_video).encode("UTF-8")
                )
            ])
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            await chk.delete(True)
            await bot.send_message(
                chat_id=update.chat.id,
                text=Translation.FORMAT_SELECTION,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                reply_to_message_id=update.id
            )
    except Exception as e:
        logger.error(f"Error in echo handler: {e}", exc_info=True)
        await chk.delete()
        await bot.send_message(
            chat_id=update.chat.id,
            text=f"An error occurred: {str(e)}",
            reply_to_message_id=update.id,
            disable_web_page_preview=True
        )
