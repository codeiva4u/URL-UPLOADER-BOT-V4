# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL | @NT_BOTS_SUPPORT | LISA-KOREA/UPLOADER-BOT-V4

# [⚠️ Do not change this repo link ⚠️] :- https://github.com/LISA-KOREA/UPLOADER-BOT-V4


import os
import time
import logging
from pyrogram import Client as PyrogramClient
from pyrogram.errors import FloodWait
from plugins.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_bot():
    if not os.path.isdir(Config.DOWNLOAD_LOCATION):
        os.makedirs(Config.DOWNLOAD_LOCATION)
    
    plugins = dict(root="plugins")
    client = PyrogramClient(
        "@UploaderXNTBot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        sleep_threshold=300,
        plugins=plugins
    )
    
    max_retries = 5
    retry_count = 0
    base_delay = 2  # Base delay in seconds
    
    while retry_count < max_retries:
        try:
            logger.info("Starting bot...")
            print("🎊 I AM ALIVE 🎊  • Support @NT_BOTS_SUPPORT")
            client.run()
            break
        except FloodWait as e:
            wait_time = e.value
            logger.warning(f"FloodWait error occurred. Waiting for {wait_time} seconds")
            print(f"⚠️ FloodWait error: Need to wait {wait_time} seconds")
            time.sleep(wait_time)
            retry_count += 1
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            if retry_count < max_retries - 1:
                delay = base_delay * (2 ** retry_count)  # Exponential backoff
                logger.info(f"Retrying in {delay} seconds... (Attempt {retry_count + 1}/{max_retries})")
                time.sleep(delay)
                retry_count += 1
            else:
                logger.error("Max retries reached. Giving up.")
                raise

if __name__ == "__main__":
    run_bot()
