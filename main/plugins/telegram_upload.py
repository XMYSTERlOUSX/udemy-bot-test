#Adapted from:
#Github.com/Vasusen-code

import asyncio
import logging
import os
import time
from pyrogram import enums
from main import DUMP_CHANNEL, SEND_TO_USER
from main.plugins.g_vid_res import get_video_resolution
from main.plugins.get_media_info import get_m_info
from main.plugins.progress_for_pyrogram import progress_for_pyrogram
from main.plugins.screenshot import screenshot
from main.plugins.messageFunc import deleteMessage
from main.plugins import premiumUser
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait

logger= logging.getLogger(__name__)

VIDEO_SUFFIXES = ["mkv", "mp4", "mov", "wmv", "3gp", "mpg", "webm", "avi", "flv", "m4v", "gif"]

async def upload_media_pyro(client:Client, message:Message, sender:int, file:str, capt=None):
    logger.info("Uploading...")
    c_time = time.time()
    file_name = str(file).split("/")[-1]

    if premiumUser.premumuUserCli:
        uploadCli = premiumUser.premumuUserCli
        uploadChat = DUMP_CHANNEL
    else:
        uploadCli = client
        uploadChat = sender

    try:
        if str(file).split(".")[-1] in VIDEO_SUFFIXES:
            logger.info("Video Found")
            if not str(file).split(".")[-1] in ['mp4', 'mkv']:
                path = str(file).split(".")[0] + ".mp4"
                os.rename(file, path) 
                file = str(file).split(".")[0] + ".mp4"
            caption= str(file).split("/")[-1]
            logger.info(caption)  
            duration= get_m_info(file)[0]
            logger.info(duration)
            logger.info("screenshot...")
            thumb_path = await screenshot(file, duration, sender)
            logger.info("get_video_resolution...")
            width, height = get_video_resolution(thumb_path)
            logger.info("Sending video...")
            
            x = await uploadCli.send_video(
                chat_id=uploadChat,
                video=file,
                width=width,
                height=height,
                caption= caption,
                parse_mode= enums.ParseMode.MARKDOWN ,
                thumb= thumb_path,
                supports_streaming=True,
                duration= duration,
                progress=progress_for_pyrogram,
                progress_args=(
                    f"`{file_name}`",
                    'Uploading..:',
                    message,
                    c_time
                )
            )
            os.remove(thumb_path)
        else:
            caption = str(file).split("/")[-1]
            caption = f"{capt}\n`{caption}`"
            thumb = "filethumb.jpg" if os.path.isfile("filethumb.jpg") else None
            x = await uploadCli.send_document(
                chat_id= uploadChat,
                document= file, 
                caption= caption,
                thumb=thumb,
                parse_mode= enums.ParseMode.MARKDOWN,
                progress=progress_for_pyrogram,
                progress_args=(
                    f"`{file_name}`",
                    'Uploading..:',
                    message,
                    c_time
                )
            )
        if SEND_TO_USER and uploadChat == DUMP_CHANNEL:
            try:
                await client.copy_message(sender, x.chat.id, x.id)
            except FloodWait as fw:
                asyncio.sleep(fw.value + 2)
                await client.copy_message(sender, x.chat.id, x.id)
            except Exception as e:
                logger.error(e)
    except Exception as e:
        logger.error(e)
        await deleteMessage(message)
        await client.send_message(sender, f"Failed to save: {file_name} - cause: {e}")  
        return
