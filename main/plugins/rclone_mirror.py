import asyncio
from configparser import ConfigParser
import logging, os
from random import randrange
import re
import subprocess, time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main.plugins.messageFunc import deleteMessage, replyMessage

from main.plugins.utils import get_rc_config
from main.plugins.zip_utils import split_in_zip
from .. import DEFAULT_RCLONE_DRIVE, EDIT_SLEEP_SECS, RCLONE_BASE_DIR

logger = logging.getLogger(__name__)

class RcloneMirror:
    def __init__(self, path, user_msg, title, ziple) -> None:
        self.id = self.__create_id(8)
        self.__path = path
        self.__title= title
        self.__user_msg = user_msg
        self.cancel = False
        self.__rclone_pr = None
        self.ziple = ziple

    def __create_id(self, count):
        map = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        id = ''
        i = 0
        while i < count:
            rnd = randrange(len(map))
            id += map[rnd]
            i += 1
        return id

    async def mirror(self):
          if self.ziple:
            message = await replyMessage(self.__user_msg, "Archiving...")
            self.__path = await split_in_zip(self.__path, size=999999999999)
            await deleteMessage(message)

          dest_drive = DEFAULT_RCLONE_DRIVE
          dest_dir= os.path.join(RCLONE_BASE_DIR, self.__title, "")  
          general_drive = None
          conf_path = await get_rc_config()
          conf = ConfigParser()
          conf.read(conf_path)

          for sections in conf.sections():
               if dest_drive == str(sections):
                    if conf[sections]['type'] == 'drive':
                         logger.info('Google Drive Upload Detected.')
                    else:
                         general_drive = conf[sections]['type']
                         logger.info(f"{general_drive} Upload Detected.")
                    break
        
          if not os.path.exists(self.__path):
               await self.__user_msg.reply('the path not found')
               return
                
          rclone_copy_cmd = ['rclone', 'copy', f"--config={conf_path}", str(self.__path),
                            f"{dest_drive}:{dest_dir}", '-P']
          
          self.__rclone_pr = subprocess.Popen(
                rclone_copy_cmd,
                stdout=(subprocess.PIPE),
                stderr=(subprocess.PIPE)
          )
          
          logger.info('Uploading...')
          rcres = await self.__rclone_update()
          
          if rcres == False:
               self.__rclone_pr.kill()
               await self.__user_msg.edit('Upload cancelled')
               logger.info('Upload cancelled')
               return

          logger.info('Successfully uploaded ✅')
          await self.__user_msg.edit('Successfully uploaded ✅')

    async def __rclone_update(self):
        blank = 0
        process = self.__rclone_pr
        user_message = self.__user_msg
        sleeps = False
        start = time.time()
        edit_time = EDIT_SLEEP_SECS
        msg = ''
        msg1 = ''
        while True:
            data = process.stdout.readline().decode()
            data = data.strip()
            mat = re.findall('Transferred:.*ETA.*', data)
            
            if mat is not None and len(mat) > 0:
                sleeps = True
                nstr = mat[0].replace('Transferred:', '')
                nstr = nstr.strip()
                nstr = nstr.split(',')
                percent = nstr[1].strip('% ')
                try:
                    percent = int(percent)
                except:
                    percent = 0
                prg = self.__progress_bar(percent)
                
                msg = '<b>{}...\n{} \n{} \nSpeed:- {} \nETA:- {}\n</b>'.format('Uploading...', nstr[0], prg, nstr[2], nstr[3].replace('ETA', ''))
                
                if time.time() - start > edit_time:
                    if msg1 != msg:
                        start = time.time()
                        await user_message.edit(text=msg, reply_markup=(InlineKeyboardMarkup([
                            [InlineKeyboardButton('Cancel', callback_data=(f"upcancel_{self.id}"))]
                            ])))                            
                        msg1 = msg
                
            if data == '':
                blank += 1
                if blank == 20:
                    break
            else:
                blank = 0

            if sleeps:
                sleeps = False
                if self.cancel:
                    return False
                await asyncio.sleep(2)
                process.stdout.flush()
    
    def __progress_bar(self, percentage):
        comp ="▪️"
        ncomp ="▫️"
        pr = ""

        try:
            percentage=int(percentage)
        except:
            percentage = 0

        for i in range(1, 11):
            if i <= int(percentage/10):
                pr += comp
            else:
                pr += ncomp
        return pr