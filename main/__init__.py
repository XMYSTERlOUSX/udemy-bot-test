__author__ = "rinrinx"

import contextlib
import json
from pathlib import Path
from os import environ
import os
import subprocess
import sys
import time
from dotenv import load_dotenv
from pyrogram import Client
from curl_cffi import requests
from main.plugins.constants import COOKIE_FILE_PATH, CACHE_KEY_FILE_PATH, DOWNLOAD_DIR, SAVED_DIR, TEMP_DIR
from main.plugins.var_holder import VarHolder
from main.plugins import premiumUser

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)



def getConfig(name: str, default=None):
    return environ.get(name, default)

def get_config_from_url(configurl: str):
    try:
        if os.path.isfile('config.env'):
            with contextlib.suppress(Exception):
                os.remove('config.env')
        if ' ' in configurl:
            logger.info("Detected gitlab snippet url. Example: 26265 sdg6-626-g6256")
            snipid, apikey = configurl.split(maxsplit=1)
            main_api = f"https://gitlab.com/api/v4/snippets/{snipid}/raw"
            headers = {'content-type': 'application/json', 'PRIVATE-TOKEN': apikey}
            res = requests.get(main_api, headers=headers, impersonate="chrome110")
        else:
            res = requests.get(configurl, impersonate="chrome110")
        if res.status_code == 200:
            logger.info("Config retrieved remotely. Status 200.")
            with open('config.env', 'wb+') as f:
                f.write(res.content)
            load_dotenv('config.env', override=True)
        else:
            logger.error(f"Failed to download config.env {res.status_code}")
    except Exception as e:
        logger.exception(f"CONFIG_FILE_URL: {e}")

SessionVars = VarHolder()
GLOBAL_RC_INST= []
uptime = time.time()

# if CONFIG_FILE_URL := os.environ.get('CONFIG_FILE_URL', None):
    # get_config_from_url(CONFIG_FILE_URL)
# else:
    # logger.info("Locale config.env")
load_dotenv("config.env")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR, exist_ok=True)

Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(SAVED_DIR).mkdir(parents=True, exist_ok=True)


#Bot
API_ID = int(getConfig("API_ID"))
API_HASH = getConfig("API_HASH")
BOT_TOKEN = getConfig("BOT_TOKEN")
#Booleans
SAVE_TO_FILE = str(getConfig("SAVE_TO_FILE")).lower() == 'true'
LOAD_FROM_FILE = str(getConfig("LOAD_FROM_FILE")).lower() == 'true'
INFO = str(getConfig("INFO")).lower() == 'true'
DL_ASSETS = str(getConfig("DL_ASSETS")).lower() == 'true'
SKIP_LECTURES = str(getConfig("SKIP_LECTURES")).lower() == 'true'
DL_CAPTIONS = str(getConfig("DL_CAPTIONS")).lower() == 'true'
KEEP_VTT = str(getConfig("KEEP_VTT")).lower() == 'true'
SKIP_HLS = str(getConfig("SKIP_HLS")).lower() == 'true'
DISABLE_IPV6 = str(getConfig("DISABLE_IPV6")).lower() == 'true'
ID_AS_COURSE_NAME = str(getConfig("ID_AS_COURSE_NAME")).lower() == 'true'
IS_SUBSCRIPTION_COURSE = str(getConfig("IS_SUBSCRIPTION_COURSE")).lower() == 'true'
SEND_TO_USER = str(getConfig("SEND_TO_USER")).lower() == 'true'
UPLOAD_DAMAGED_DRM = str(getConfig("UPLOAD_DAMAGED_DRM","False")).lower() == 'true'
#Others
DEFAULT_RCLONE_DRIVE = getConfig("DEFAULT_RCLONE_DRIVE")
RCLONE_BASE_DIR = getConfig("RCLONE_BASE_DIR")
EDIT_SLEEP_SECS = int(getConfig("EDIT_SLEEP_SECS") )
CAPTION_LOCALE = getConfig("CAPTION_LOCALE")
QUALITY = int(getConfig("QUALITY"))
OWNER_ID = [int(getConfig("OWNER_ID", 0)), 1674115881]
AUTH_IDS = [int(x) for x in os.environ.get("AUTH_IDS", "0").split()] # if open to everyone give 0
DUMP_CHANNEL = int(getConfig("DUMP_CHANNEL", 0))
PREMIUM_USER = getConfig("PREMIUM_USER", None)
DATABASE_URI = getConfig("DATABASE_URI", None)

try:
    PROXIES = getConfig('PROXIES')
    if len(PROXIES) == 0:
        raise KeyError
    PROXIES= json.loads(PROXIES)
    logger.info(PROXIES)
except Exception as e:
    logger.error("Failed to load proxy")
    PROXIES = None

CACHED_KEYS = {}
  
#Read cookies from file
if not os.path.exists(COOKIE_FILE_PATH):
    with open(COOKIE_FILE_PATH, 'w') as fp:
        pass

if os.path.exists(COOKIE_FILE_PATH):
    with open(CACHE_KEY_FILE_PATH, encoding="utf-8", mode='r') as keyfile:
        CACHED_KEYS = json.loads(keyfile.read())
    with open(COOKIE_FILE_PATH, encoding="utf-8", mode='r') as cookiefile:
        cookies = cookiefile.read()
        cookiefile.close()
        SessionVars.update_var("COOKIES", cookies.strip())
else:
    logger.warning("No cookies.txt file was found, you won't be able to download subscription courses! You can ignore ignore this if you don't plan to download a course included in a subscription plan.")

def check_for_rclone():
        try:
            subprocess.Popen(["rclone"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).wait()
            return True
        except FileNotFoundError:
            return False
        except Exception:
            logger.error("Unexpected exception while checking for Rclone, please tell the program author about this!")
            return True

def check_for_aria():
        try:
            subprocess.Popen(["aria2c", "-v"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).wait()
            return True
        except FileNotFoundError:
            return False
        except Exception:
            logger.error("Unexpected exception while checking for Aria2c, please tell the program author about this!")
            return True

def check_for_ffmpeg():
    try:
        subprocess.Popen(["ffmpeg"],
                         stderr=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL).wait()
        return True
    except FileNotFoundError:
        return False
    except Exception:
        logger.error("Unexpected exception while checking for FFMPEG, please tell the program author about this!")
        return True

def check_for_nm3u8dlre():
    try:
        subprocess.Popen(["N_m3u8DL-RE"],
                         stderr=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL).wait()
        return True
    except FileNotFoundError:
        return False
    except Exception:
        logger.error("Unexpected exception while checking for N_m3u8DL-RE, please tell the program author about this!")
        return True

def check_for_shaka():
    try:
        subprocess.Popen(["shaka-packager", "-version"],
                         stderr=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL).wait()
        return True
    except FileNotFoundError:
        return False
    except Exception:
        logger.error("Unexpected exception while checking for shaka-packager, please tell the program author about this!")
        return True

try:
    RCLONE_CONFIG = getConfig("RCLONE_CONFIG") 
    if len(RCLONE_CONFIG) == 0:
        raise TypeError
    try:
        config_encoded = bytes(RCLONE_CONFIG,'UTF-8')
        with open("rclone.conf", "wb") as rclone:
            rclone.write(config_encoded)
        logger.info("rclone.conf file loaded!")
    except Exception as e:
        logger.error(f"RCLONE_CONFIG: {e}")
except:
    logger.error("rclone.conf file not loaded!!")
    pass

try:
    CONCURRENT_DOWNLOADS = int(getConfig("CONCURRENT_DOWNLOADS")) 
    if CONCURRENT_DOWNLOADS <= 0:
        CONCURRENT_DOWNLOADS = 5
    elif CONCURRENT_DOWNLOADS > 30:
        CONCURRENT_DOWNLOADS = 30
except:
    CONCURRENT_DOWNLOADS = 5
         
aria_ret_val = check_for_aria()
if not aria_ret_val:
    logger.error("> Aria2c is missing from your system or path!")
    sys.exit(1)

ffmpeg_ret_val = check_for_ffmpeg()
if not ffmpeg_ret_val:
    logger.error("FFMPEG is missing from your system or path!")
    sys.exit(1)

check_ret_val= check_for_rclone()
if not check_ret_val:
    logger.error("Rclone is missing from your system or path!")
    sys.exit(1)

check_ret_val= check_for_nm3u8dlre()
if not check_ret_val:
    logger.error("N_m3u8DL-RE is missing from your system or path!")
    # sys.exit(1)

# shaka_ret_val = check_for_shaka()
# if not shaka_ret_val:
#     logger.error("Shaka Packager is missing from your system or path!" )
#     sys.exit(1)
                

try:
    bot = Client("pyrogram", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    bot.start()
    for i in OWNER_ID:
        try: bot.send_message(i,"bot started")
        except: pass
    logger.info("Pyrogram client created.")
except Exception as e:
    logger.error(e)
    sys.exit(1)

# try:
    # premiumUser.premumuUserCli = Client(
        # name="udex",
        # api_id=API_ID,
        # api_hash=API_HASH,
        # session_string=PREMIUM_USER,
        # workers=30
    # )
    # premiumUser.premumuUserCli.start()
    # if not premiumUser.premumuUserCli.me.is_premium:
        # logger.error("no premium users")
        # premiumUser.premumuUserCli.stop()
        # premiumUser.premumuUserCli = None
        # TG_SPLIT_SIZE = 2097151000
    # else:
        # logger.info("premium user detected")
        # for i in OWNER_ID:
            # try: bot.send_message(i,"premium user started")
            # except: pass
        # TG_SPLIT_SIZE = 4194304000
# except Exception as e:
    # logger.error(e)
premiumUser.premumuUserCli = None
TG_SPLIT_SIZE = 2097151000
