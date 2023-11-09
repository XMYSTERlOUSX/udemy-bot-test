from os import walk
import os
from pyrogram.errors import FloodWait
import asyncio
from pyrogram import Client
from pyrogram.types import Message
from main import TG_SPLIT_SIZE
from main.plugins.messageFunc import deleteMessage, replyMessage
from main.plugins.telegram_upload import upload_media_pyro
from main.plugins.zip_utils import split_in_zip

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class RcloneLeech:
    def __init__(self, client, user_msg, chat_id, out_dir, ziple, capt) -> None:
        self.__client:Client = client
        self.__user_msg:Message = user_msg
        self.__chat_id:int = chat_id
        self.cancel:bool = False
        self.__out_dir = out_dir
        self.ziple:bool = ziple
        self.capt:str = capt

    async def leech(self):
        if not os.path.exists(self.__out_dir):
            await self.__user_msg.reply('the path not found')
            return
        if self.ziple:
            message = await replyMessage(self.__user_msg, "Archiving...")
            logger.debug(f"self.__out_dir: {self.__out_dir}")
            split_dir = await split_in_zip(self.__out_dir, size=TG_SPLIT_SIZE)
            self.__out_dir = split_dir
            await deleteMessage(message)
            logger.debug(f"split_dir: {split_dir}")
        for dirpath, _, filenames in walk(self.__out_dir):
            if len(filenames) == 0:
                continue 
            for file in sorted(filenames):
                timer = 5  
                f_path = os.path.join(dirpath, file)
                f_size = os.path.getsize(f_path)
                if int(f_size) > TG_SPLIT_SIZE:
                    message = await replyMessage(self.__user_msg, "Splitting...")
                    split_dir= await split_in_zip(f_path, size=TG_SPLIT_SIZE)
                    os.remove(f_path)
                    dir_list= os.listdir(split_dir)
                    dir_list.sort() 
                    for file in dir_list:
                        f_path = os.path.join(split_dir, file)
                        try:
                            await upload_media_pyro(self.__client, message, self.__chat_id, f_path)
                        except FloodWait as fw:
                            await asyncio.sleep(fw.value + 5)
                            await upload_media_pyro(self.__client, message, self.__chat_id, f_path)     
                        asyncio.sleep(timer)
                else:
                    try:
                        await upload_media_pyro(self.__client, self.__user_msg, self.__chat_id, f_path, self.capt)
                    except FloodWait as fw:
                        await asyncio.sleep(fw.value + 5)
                        await upload_media_pyro(self.__client, self.__user_msg, self.__chat_id, f_path, self.capt)
                    asyncio.sleep(timer)
        #await clear_stuff("./Downloads")
        await deleteMessage(message)
        x = await replyMessage(self.__user_msg, "Finished completed.")
        await asyncio.sleep(5)
        await deleteMessage(x)
