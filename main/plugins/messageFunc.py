# HuzunluArtemis - 2021 (Licensed under GPL-v3)

import asyncio
import time
from pyrogram import Client
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified
from pyrogram.errors import FloodWait
from pyrogram.types.messages_and_media.message import Message
from pyrogram.enums.parse_mode import ParseMode
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

async def replyMessage(toReplyMessage:Message, replyText:str, replyButtons = None, disablePreview = True):
    try:
        return await toReplyMessage.reply_text(replyText,
            disable_web_page_preview=disablePreview,
            quote=True,
            reply_markup = replyButtons)
    except FloodWait as e:
        asyncio.sleep(e.value)
        return await replyMessage(toReplyMessage, replyText, replyButtons, disablePreview)
    except Exception as e:
        logger.info(str(e))

async def sendMessage(client:Client, chat_id, replyText:str, replyButtons = None, disablePreview = True):
    try:
        return await client.send_message(chat_id, replyText,
            disable_web_page_preview=disablePreview,
            reply_markup = replyButtons)
    except FloodWait as e:
        asyncio.sleep(e.value)
        return await sendMessage(client, chat_id, replyText, replyButtons, disablePreview)
    except Exception as e:
        logger.info(str(e))

async def editMessage(toEditMessage:Message, editText, replyButtons = None):
    try:
        return await toEditMessage.edit(text=editText,
            disable_web_page_preview=True,
            reply_markup = replyButtons)
    except FloodWait as e:
        asyncio.sleep(e.value)
        return await editMessage(toEditMessage, editText, replyButtons)
    except Exception as e:
        logger.info(str(e))

async def copyMessage(message:Message, toCopyChatId):
    try:
        return await message.copy(chat_id=toCopyChatId)
    except FloodWait as e:
        asyncio.sleep(e.value)
        return await copyMessage(message, toCopyChatId)
    except Exception as e:
        logger.info(str(e))

async def sendDocument(toReplyDocument:Message, filePath):
    try:
        return await toReplyDocument.reply_document(filePath)
    except FloodWait as e:
        asyncio.sleep(e.value)
        return await sendDocument(toReplyDocument, filePath)
    except Exception as e:
        logger.info(str(e))

async def deleteMessage(todelete:Message):
    try:
        return await todelete.delete()
    except FloodWait as e:
        asyncio.sleep(e.value)
        return await deleteMessage(todelete)
    except Exception as e:
        logger.info(str(e))
