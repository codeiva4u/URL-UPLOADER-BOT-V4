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
import aiohttp
import re
import random
import string
import base64

cookies_file = Config.COOKIES_FILE
logger = logging.getLogger(__name__)

async def generate_degoo_cookies():
    try:
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
            
            share_id = url.split('/')[-1]
            
            share_url = f"https://app.degoo.com/api/share/{share_id}"
            async with session.get(share_url, headers=headers) as response:
                if response.status == 200:
                    share_data = await response.json()
                    if 'files' in share_data:
                        files = share_data['files']
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

async def login_to_degoo(email, password):
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
            
            login_data = {
                "email": email,
                "password": password
            }
            
            login_url = "https://app.degoo.com/api/auth/login"
            
            async with session.post(login_url, json=login_data, headers=headers) as response:
                if response.status == 200:
                    login_response = await response.json()
                    if 'token' in login_response:
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
                        
                        return True, login_response.get('token', '')
                return False, None
    except Exception as e:
        logger.error(f"Error logging in to Degoo: {e}")
        return False, None

async def handle_degoo_url(bot, update, youtube_dl_url, tmp_directory_for_each_user):
    try:
        # Send a new message to the user for credentials
        status_message = await update.reply_text(text="Please send your Degoo email and password in this format:\n\nemail:password")
        
        try:
            # Create a filter for the specific chat and user
            def message_filter(client, message):
                return message.chat.id == update.chat.id and message.from_user.id == update.from_user.id

            # Wait for the message with the filter
            response = await bot.wait_for_message(
                chat_id=update.chat.id,
                filters=message_filter,
                timeout=300
            )
            
            if not response or not response.text:
                await status_message.edit_text(text="No credentials provided. Process cancelled.")
                return
            
            try:
                email, password = response.text.strip().split(':')
                email = email.strip()
                password = password.strip()
            except ValueError:
                await status_message.edit_text(text="Invalid format. Please use format: email:password")
                return
            
            await status_message.edit_text(text="Logging in to Degoo...")
            
            login_success, auth_token = await login_to_degoo(email, password)
            if not login_success:
                await status_message.edit_text(text="Login failed. Please check your credentials.")
                return
            
            share_id = youtube_dl_url.split('/')[-1]
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://app.degoo.com",
                "Referer": youtube_dl_url,
                "X-Requested-With": "XMLHttpRequest",
                "Authorization": f"Bearer {auth_token}"
            }
            
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
                                    
                                    await status_message.edit_text(text=f"Downloading {file_name}...")
                                    
                                    download_url = f"https://app.degoo.com/api/share/{share_id}/file/{file_id}/download"
                                    
                                    if await download_degoo_file(download_url, file_path, headers):
                                        await status_message.edit_text(text=f"Uploading {file_name}...")
                                        
                                        if os.path.exists(file_path):
                                            await update.reply_document(
                                                document=file_path,
                                                caption=f"Downloaded from Degoo: {file_name}"
                                            )
                                    else:
                                        await status_message.edit_text(text=f"Failed to download {file_name}")
            
            await status_message.edit_text(text="All files processed!")
            
        except Exception as e:
            logger.error(f"Error waiting for credentials: {e}")
            await status_message.edit_text(text="Process timed out. Please try again.")
            return
    except Exception as e:
        logger.error(f"An error occurred in handle_degoo_url: {e}", exc_info=True)
        try:
            await status_message.edit_text(text=f"An unexpected error occurred during Degoo processing. Please check logs or try again.")
        except Exception as e_edit:
            logger.error(f"Failed to edit text on error in handle_degoo_url: {e_edit}") 