import glob
from pathlib import Path
from os import path as ospath, remove as osremove
from main.plugins.downloaded import get_courses_list
from main.plugins import premiumUser
from main.utils import load_plugins

from . import bot
from pyrogram import idle

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)

path = "main/plugins/*.py"
files = glob.glob(path)
for name in files:
    with open(name) as a:
        patt = Path(a.name)
        plugin_name = patt.stem
        load_plugins(plugin_name.replace(".py", ""))
premiumUser.downloaded_courses = get_courses_list()
if ospath.isfile(".updatemsg"):
        with open(".updatemsg") as f:
            chat_id, msg_id = map(int, f)
        bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text="Restarted successfully!"
        )
        osremove(".updatemsg")

logger.info("Successfully deployed!")
logging.getLogger('pyrogram').setLevel(logging.WARNING)
idle()