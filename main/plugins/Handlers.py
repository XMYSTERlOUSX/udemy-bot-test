import asyncio
import os
from os import execl as osexecl
import re
import signal
from sys import executable
import signal
from subprocess import run as srun
from pyrogram import filters
from pyrogram.filters import regex
from main.plugins.authUserCheck import is_admin, is_auth
from main.plugins import premiumUser
from main.plugins.download import download
from main.plugins.downloaded import make_downloaded, make_undownloaded
from main.plugins.getcourses import get_all_courses, get_course_info
from main.plugins.messageFunc import deleteMessage
from main.plugins.progress_for_pyrogram import humanbytes
from main.plugins.utils import clean_all, get_size
from main.plugins.constants import COOKIE_FILE_PATH
from .. import GLOBAL_RC_INST, SessionVars, bot, logger, uptime
from main.plugins.human_format import human_readable_bytes, human_readable_timedelta
import shutil
import subprocess
import psutil
from psutil import net_io_counters
import time
from pyrogram import Client
from pyrogram.types import Message

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)


@bot.on_message(filters= filters.command(["start", "help", "about", "yardım"]))
async def handle_start(client:Client, message:Message):
    if not is_auth(message): return
    toSendStr = f"well-being {message.from_user.mention}\n"\
        "udbv5'e hoş geldiniz\nhttps://telegra.ph/udb-01-21"
    await message.reply_text(toSendStr,quote=True, disable_web_page_preview=True)

#######################################################

@bot.on_message(filters= filters.command("cookies"))
async def handle_cookies(client:Client, message:Message):
    if not is_admin(message): return
    replied_message= message.reply_to_message
    beklemes = await message.reply("waiting...")
    token = str()
    if replied_message:
        token = replied_message.text.strip()
    else:
        token = message.text.split(' ',1)
        if len(token) != 2:
            await beklemes.edit('example usage: /cookies asdf9sa8df89asdf898s9d')
            return
        token = token[1].strip()

    # if len(token) > 100:
        # await beklemes.edit('The token must be 40 centimeters.')
        # return
    
    with open(COOKIE_FILE_PATH, encoding="utf-8", mode='w') as cookiefile:
        cookiefile.write(token)
    SessionVars.update_var("COOKIES", token) 
    SessionVars.update_var("BEARER_TOKEN", token) 
    await beklemes.edit(f"Your token has been set: {token}")

#######################################################

@bot.on_message(filters= filters.command("restart"))
async def handle_restart(client:Client, message:Message):
    if not is_admin(message): return
    restart_message= await message.reply("Restarting...")
    try:
        for line in os.popen("ps ax | grep " + "rclone" + " | grep -v grep"):
            fields = line.split()
            pid = fields[0]
            os.kill(int(pid), signal.SIGKILL
            )
    except Exception as exc:
        logger.error(f"Error: {exc}")
    clean_all()
    srun(["pkill", "-f", "aria2c|ffmpeg|yt-dlp"])
    srun(["python3", "update.py"])
    logger.warning(restart_message)
    with open(".updatemsg", "w") as f:
                f.truncate(0)
                f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "main")

#######################################################

@bot.on_callback_query(filters= regex("upcancel"))
async def cancel_callback(client, query):
   data = query.data.split("_")
   id= data[1]
   for rc_up in GLOBAL_RC_INST:
        if rc_up.id == id:
            rc_up.cancel = True
            break 

######################################################

@bot.on_message(filters.command("boyut"))
async def boyut(client: Client, message: Message):
    if not is_auth(message): return
    outDir = "out_dir"
    arr = os.listdir(outDir)
    if len(arr) == 0:
        sendo = await message.reply_text("none of them have landed yet.", quote=True)
        await asyncio.sleep(20)
        await deleteMessage(sendo)
        await deleteMessage(message)
        return
    toret = ""
    for file in arr:
        yol = os.path.join(outDir, file)
        boyut = humanbytes(get_size(yol))
        icon = '📄' if os.path.isfile(yol) else '📂'
        toret += f"{icon} {file} ({boyut})\n"

    sendo = await message.reply_text(toret, quote=True)
    await asyncio.sleep(20)
    await deleteMessage(sendo)
    await deleteMessage(message)

######################################################

@bot.on_message(filters.command("bilgi"))
async def bilgi(client: Client, message: Message):
    if not is_auth(message): return
    if len(message.command) != 3:
        return await message.reply('usage: /information link')

    kursid = message.command[1]
    aksestoken = message.command[2]
    Cid, Curl, Ctitle, Cprice, Ccourser, Cjob_title, Ccourser_url = await get_course_info(kursid, aksestoken)
    capt = f"🧪 `{Ctitle}` (`{Cprice}`)\n"
    capt +=  f"`{Curl}`\n\n"
    capt += f"🧬 `{Ccourser}` (`{Cjob_title}`)\n"
    capt +=  f"`{Ccourser_url}`\n"
    capt +=  f"#udbc{Cid}"
    await message.reply(capt)
    
######################################################

@bot.on_message(filters.command(["mirror","allmirror","zipmirror", "allzipmirror","leech","allleech","zipleech", "allzipleech"]))
async def handle_mirror_leech(client:Client, message:Message):
    if not is_auth(message): return
    ziple = "zip" in message.command[0].lower()
    isleech = "leech" in message.command[0].lower()
    ismirror = "mirror" in message.command[0].lower()
    hepsi = "all" in message.command[0].lower()

    if not is_admin(message) and message.command[0].lower() not in ["zipleech","allzipleech"]:
        return
    
    if premiumUser.is_downloading:
        await message.reply_text("Another download is currently in progress. Try it when it's done.")
        return
    
    premiumUser.is_downloading = True
    beklemes = await message.reply_text(f"please wait {message.from_user.mention} ({message.from_user.id})")
    replied_message= message.reply_to_message

    # get link or token
    link_or_token = str()
    if replied_message:
        link_or_token = replied_message.text.strip()
    else:
        link_or_token = message.text.split(' ',1)
        if len(link_or_token) != 2:
            await beklemes.edit('example usage: /zipleech htpps://udemy.com/abc/learn/')
            premiumUser.is_downloading = False
            return
        link_or_token = link_or_token[1].strip()

    # if len(token) != 40
    # if hepsi and len(link_or_token) > 100:
        # await beklemes.edit('The token must be 40 centimeters.')
        # premiumUser.is_downloading = False
        # return
    # set dl_links
    if hepsi:
        await beklemes.edit(f"Your courses are being reviewed {message.from_user.mention} ({message.from_user.id}).\nIt may take a while. be patient.")
        dl_links = await get_all_courses(ACCESS_TOKEN=link_or_token, sadelink=True, tumu=False, count=False)

        with open(COOKIE_FILE_PATH, encoding="utf-8", mode='w') as cookiefile:
            cookiefile.write(link_or_token)
        SessionVars.update_var("COOKIES", link_or_token) 
        SessionVars.update_var("BEARER_TOKEN", link_or_token) 
    else:
        dl_links = link_or_token
    # get urls
    urls = re.findall(r"\bhttps?://.*\.\S+", dl_links)
    logger.info(urls)
    if not urls:
        await beklemes.edit("udemy link not found.")
        premiumUser.is_downloading = False
        return

    try: await beklemes.pin()
    except: pass
    await download(client, beklemes, urls, leech=isleech, mirror=ismirror, ziple=ziple)
    beklemes.edit("Your transaction is finished.")
    try: await beklemes.unpin()
    except: pass
    premiumUser.is_downloading = False

#######################################################

@bot.on_message(filters.command(["kapat", "exit"]))
async def exit_handler(client: Client, message: Message):
    if not is_admin(message): return
    await message.reply("bot is shutting down")
    try:
        if premiumUser.premumuUserCli:
            premiumUser.premumuUserCli.stop()
    except Exception as e:
        logger.error(e)
    logger.warning("The boot was closed manually.")
    exit(0)

#######################################################

@bot.on_message(filters.command(["log", "logs"]))
async def log_handler(client: Client, message: Message):
    if not is_admin(message): return
    await message.reply_document("log.txt")

######################################################

@bot.on_message(filters.command(["getir", "getirlink", "tgetir", "tgetirlink"]))
async def getco(client: Client, message: Message):
    if not is_admin(message): return
    cmd = message.text.split(' ', 1)
    if len(cmd) == 1:
        return await message.reply_text(
                '/getir - those who did not land in detailı\n'\
                '/tgetir - all detailed\n'\
                '/getirlink - dead links in detail\n'\
                '/tgetirlink - all links are detailed'
            )
    cmd = cmd[1]
    # if len(str(cmd)) > 100:
        # return await message.reply_text('The token must be 40 centimeters.')
    bekle:Message = await message.reply_text('Waiting..', reply_to_message_id = message.id)
    komut = message.command[0].lower()
    sadelink = 'link' in komut
    tumu = komut.startswith('t')
    getstring = await get_all_courses(cmd, sadelink, tumu)

    if len(getstring) > 3000:
        with open('courses.txt', 'w') as file:
            file.write(getstring)

        with open('courses.txt', 'rb') as doc:
            await client.send_document(
                document=doc,
                file_name =doc.name,
                caption="kurs listesi",
                reply_to_message_id=message.id,
                chat_id=message.chat.id)
    else:
        await bekle.edit_text(getstring, disable_web_page_preview=True)

######################################################

@bot.on_message(filters.command(["indi", "inmedi"]))
async def indi(client: Client, message: Message):
    if not is_admin(message): return
    cmd = message.text.split(' ', 2)
    if len(cmd) != 3:
        return await message.reply_text('Leave a space and enter a token, you ignorant fool.')
    link = cmd[1]
    token = cmd[2]
    id, _, _, _, _, _, _ = await get_course_info(link, token)
    if message.command[0] == "indi":
        make_downloaded(id)
        await message.reply_text('The course is set to downloaded.')
    elif message.command[0] == "inmedi":
        make_undownloaded(id)
        await message.reply_text('The course is set to not downloaded.')

######################################################

@bot.on_message(filters.command("shell"))
async def handle_shell(client: Client, message: Message):
    if not is_admin(message): return
    try:
        cmd = message.text.split(' ', 1)
        if len(cmd) == 1:
            await message.reply_text('No command to execute was given.')
            return
        cmd = cmd[1]
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        reply = ''
        stderr = stderr.decode()
        stdout = stdout.decode()
        if stdout:
            reply += f"Stdout:\n`{stdout}`\n"
            logger.info(f"Shell - {cmd} - {stdout}")
        if stderr:
            reply += f"Stderr:\n`{stderr}`\n"
            logger.info(f"Shell - {cmd} - {stderr}")
        if len(reply) > 3000:
            with open('shell.txt', 'w') as file:
                file.write(reply)
            with open('shell.txt', 'rb') as doc:
                await client.send_document(
                    document=doc,
                    file_name =doc.name,
                    reply_to_message_id=message.id,
                    chat_id=message.chat.id)
        else:
            await message.reply_text(reply)
    except:
        await message.reply_text("Maybe your shell message was empty.")
        
######################################################

@bot.on_message(filters.command("server"))
async def handle_server(client: Client, message: Message):
    if not is_admin(message): return
    e = await message.reply("bekleyin...")
    try:
        mem = psutil.virtual_memory()
        memavailable = human_readable_bytes(mem.available)
        memtotal = human_readable_bytes(mem.total)
        mempercent = mem.percent
        memfree = human_readable_bytes(mem.free)
    except:
        memavailable = "N/A"
        memtotal = "N/A"
        mempercent = "N/A"
        memfree = "N/A"

    try:
        cpufreq = psutil.cpu_freq()
        freqcurrent = cpufreq.current
        freqmax = cpufreq.max
    except:
        freqcurrent = "N/A"
        freqmax = "N/A"

    try:
        cores = psutil.cpu_count(logical=False)
        lcores = psutil.cpu_count()
    except:
        cores = "N/A"
        lcores = "N/A"

    try:
        cpupercent = psutil.cpu_percent()
    except:
        cpupercent = "N/A"

    try:
        usage = shutil.disk_usage("/")
        totaldsk = human_readable_bytes(usage.total)
        useddsk = human_readable_bytes(usage.used)
        freedsk = human_readable_bytes(usage.free)
    except:
        totaldsk = "N/A"
        useddsk = "N/A"
        freedsk = "N/A"

    try:
        recv = human_readable_bytes(net_io_counters().bytes_recv)
        sent = human_readable_bytes(net_io_counters().bytes_sent)
    except:
        recv = "N/A"
        sent = "N/A"

    diff = time.time() - uptime
    diff = human_readable_timedelta(diff)


    msg = (
        f"<b>BOT UPTIME:-</b> {diff}\n\n"
        "<b>CPU STATS:-</b>\n"
        f"Cores: {cores} Logical: {lcores}\n"
        f"CPU Frequency: {freqcurrent}  Mhz Max: {freqmax}\n"
        f"CPU Utilization: {cpupercent}%\n"
        "\n"
        "<b>STORAGE STATS:-</b>\n"
        f"Total: {totaldsk}\n"
        f"Used: {useddsk}\n"
        f"Free: {freedsk}\n"
        "\n"
        "<b>MEMORY STATS:-</b>\n"
        f"Available: {memavailable}\n"
        f"Total: {memtotal}\n"
        f"Usage: {mempercent}%\n"
        f"Free: {memfree}\n"
        "\n"
        "<b>TRANSFER INFO:</b>\n"
        f"Download: {recv}\n"
        f"Upload: {sent}\n"
    )
    await e.edit(msg)



