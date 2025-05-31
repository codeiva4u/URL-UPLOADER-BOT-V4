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
import ssl

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
        # Configure SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create aiohttp session with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
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
        # Configure SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create aiohttp session with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # First get CSRF token
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0"
            }
            
            # Get login page first to get CSRF token
            async with session.get("https://app.degoo.com/login", headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to get login page: {response.status}")
                    return False, None
                
                # Extract CSRF token from cookies
                cookies = response.cookies
                csrf_token = cookies.get('csrf_token', '')
                
                # Get session cookie
                session_cookie = cookies.get('session', '')
            
            # Now try to login
            login_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Content-Type": "application/json",
                "Origin": "https://app.degoo.com",
                "Referer": "https://app.degoo.com/login",
                "X-CSRF-Token": csrf_token,
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Cookie": f"session={session_cookie}; csrf_token={csrf_token}"
            }
            
            login_data = {
                "email": email,
                "password": password,
                "remember": True,
                "csrf_token": csrf_token
            }
            
            login_url = "https://app.degoo.com/api/auth/login"
            
            async with session.post(login_url, json=login_data, headers=login_headers) as response:
                response_text = await response.text()
                logger.info(f"Login response: {response_text}")
                
                if response.status == 200:
                    try:
                        login_response = await response.json()
                        if 'token' in login_response:
                            # Get all cookies from response
                            response_cookies = response.cookies
                            auth_token = login_response.get('token', '')
                            
                            cookies = {
                                "cookies": [
                                    {
                                        "domain": "app.degoo.com",
                                        "name": "session",
                                        "value": response_cookies.get('session', session_cookie)
                                    },
                                    {
                                        "domain": "app.degoo.com",
                                        "name": "auth_token",
                                        "value": auth_token
                                    },
                                    {
                                        "domain": "app.degoo.com",
                                        "name": "csrf_token",
                                        "value": response_cookies.get('csrf_token', csrf_token)
                                    }
                                ]
                            }
                            
                            with open(Config.COOKIES_FILE, 'w') as f:
                                json.dump(cookies, f)
                            
                            return True, auth_token
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse login response: {e}")
                        return False, None
                else:
                    logger.error(f"Login failed with status {response.status}: {response_text}")
                    return False, None
    except Exception as e:
        logger.error(f"Error logging in to Degoo: {e}")
        return False, None

async def handle_degoo_url(bot, update, youtube_dl_url, tmp_directory_for_each_user):
    try:
        # First ask for email
        status_message = await update.reply_text(text="Please send your Degoo email address:")
        
        try:
            # Create a filter for the specific chat and user
            def message_filter(client, message):
                return message.chat.id == update.chat.id and message.from_user.id == update.from_user.id

            # Wait for email
            email_response = await bot.wait_for_message(
                chat_id=update.chat.id,
                filters=message_filter,
                timeout=300
            )
            
            if not email_response or not email_response.text:
                await status_message.edit_text(text="No email provided. Process cancelled.")
                return
            
            email = email_response.text.strip()
            
            # Now ask for password
            await status_message.edit_text(text="Please send your Degoo password:")
            
            # Wait for password
            password_response = await bot.wait_for_message(
                chat_id=update.chat.id,
                filters=message_filter,
                timeout=300
            )
            
            if not password_response or not password_response.text:
                await status_message.edit_text(text="No password provided. Process cancelled.")
                return
            
            password = password_response.text.strip()
            
            await status_message.edit_text(text="Logging in to Degoo...")
            
            login_success, auth_token = await login_to_degoo(email, password)
            if not login_success:
                await status_message.edit_text(text="Login failed. Please check your credentials and try again.")
                return
            
            share_id = youtube_dl_url.split('/')[-1]
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://app.degoo.com",
                "Referer": youtube_dl_url,
                "X-Requested-With": "XMLHttpRequest",
                "Authorization": f"Bearer {auth_token}",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }
            
            share_url = f"https://app.degoo.com/api/share/{share_id}"
            async with aiohttp.ClientSession(connector=connector) as session:
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