# HuzunluArtemis - 2021 (Licensed under GPL-v3)

from pyrogram.types.messages_and_media.message import Message
from main import AUTH_IDS, OWNER_ID

def is_auth(message: Message):
    if 0 in AUTH_IDS:
        return True
    elif message.from_user.id in OWNER_ID:
        return True
    elif message.from_user.id in AUTH_IDS:
        return True
    elif message.chat.id in AUTH_IDS:
        return True
    else:
        return False

def is_admin(message: Message):
    return message.from_user.id in OWNER_ID
   