#######################################################

from main import GLOBAL_RC_INST
from main.plugins.constants import DOWNLOAD_DIR
from main.plugins.rclone_leech import RcloneLeech
from main.plugins.rclone_mirror import RcloneMirror
from pyrogram import filters
from .. import GLOBAL_RC_INST, bot
from pyrogram import Client
from pyrogram.types import Message

@bot.on_message(filters= filters.command("testmirror"))
async def handle_test(client:Client, message:Message):
    mess_age = await message.reply_text("Testing mirror...")
    rclone_mirror= RcloneMirror(DOWNLOAD_DIR, mess_age, "title", False)
    GLOBAL_RC_INST.append(rclone_mirror)
    await rclone_mirror.mirror()
    GLOBAL_RC_INST.remove(rclone_mirror)

#######################################################

@bot.on_message(filters= filters.command("testleech"))
async def handle_test(client:Client, message:Message):
    mess_age = await message.reply_text("Testing leech...")
    chat_id= mess_age.chat.id
    rclone_leech= RcloneLeech(client, mess_age, chat_id, DOWNLOAD_DIR)
    GLOBAL_RC_INST.append(rclone_leech)
    await rclone_leech.leech()
    GLOBAL_RC_INST.remove(rclone_leech)  