import math
import shutil
import time
from psutil import cpu_percent, virtual_memory
from main.plugins.human_format import human_readable_bytes, human_readable_timedelta
from .. import uptime

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)

FINISHED_PROGRESS_STR = "■" # "■"
UN_FINISHED_PROGRESS_STR = "□" # "□"
PROGRESSBAR_LENGTH = 10

async def progress_for_pyrogram(
        current,
        total,
        file_name,
        ud_type,
        message,
        start
):
    """ generic progress display for Telegram Upload / Download status """
    try:
        now = time.time()
        diff = now - start
        if round(diff % 20.00) == 0 or current == total:
            percentage = current * 100 / total
            speed = current / diff
            elapsed_time = round(diff) * 1000
            time_to_completion = round((total - current) / speed) * 1000
            estimated_total_time = elapsed_time + time_to_completion

            elapsed_time = time_formatter(milliseconds=elapsed_time)
            estimated_total_time = time_formatter(milliseconds=estimated_total_time)
            time_to_completion = time_formatter(milliseconds=time_to_completion)

            diff = time.time() - uptime
            diff = human_readable_timedelta(diff)
            usage = shutil.disk_usage("/")
            free = human_readable_bytes(usage.free) 

            bottom_status= ''
            bottom_status += f"\n<b>CPU:</b> {cpu_percent()}% | <b>FREE:</b> {free}" \
            f"\n<b>RAM:</b> {virtual_memory().percent}% | <b>UPTIME:</b> {diff}" 

            progress = "\n💦 [{0}{1}]\n".format(
                ''.join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / (100/PROGRESSBAR_LENGTH)))]),
                ''.join([UN_FINISHED_PROGRESS_STR for i in range(PROGRESSBAR_LENGTH - math.floor(percentage / (100/PROGRESSBAR_LENGTH)))])
                )
            progressReverse = "\n💦 [{1}{0}]\n".format(
                ''.join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / (100/PROGRESSBAR_LENGTH)))]),
                ''.join([UN_FINISHED_PROGRESS_STR for i in range(PROGRESSBAR_LENGTH - math.floor(percentage / (100/PROGRESSBAR_LENGTH)))])
                )

            tmp = progress \
                + f"`Percent Completed: % {round(percentage, 2)}\n"\
                f"Total Size: {humanbytes(total)}\n"\
                f"Finished Size: {humanbytes(current)}\n"\
                f"Remaining Size: {humanbytes(total-current)}\n"\
                f"Speed: {humanbytes(speed)}/s\n"\
                + progressReverse \
                + bottom_status
        
            try: await message.edit(f"{ud_type} {file_name}\n{tmp}")
            except: pass
    except Exception as e:
        logger.info(e, exc_info=True)


def humanbytes(size: int) -> str:
    """ converts bytes into human readable format """
    # https://stackoverflow.com/a/49361727/4723940
    # 2**10 = 1024
    if not size:
        return ""
    power = 2 ** 10
    number = 0
    dict_power_n = {
        0: " ",
        1: "Ki",
        2: "Mi",
        3: "Gi",
        4: "Ti"
    }
    while size > power:
        size /= power
        number += 1
    return str(round(size, 2)) + " " + dict_power_n[number] + 'B'


def time_formatter(milliseconds: int) -> str:
    """ converts seconds into human readable format """
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
          ((str(hours) + "h, ") if hours else "") + \
          ((str(minutes) + "m, ") if minutes else "") + \
          ((str(seconds) + "s, ") if seconds else "") + \
          ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

def get_progressbar(percent):
    try:
        return (int(percent)//10 * FINISHED_PROGRESS_STR + (10-int(percent)//10) * UN_FINISHED_PROGRESS_STR)
    except:
        percent = 100
        return (int(percent)//10 * FINISHED_PROGRESS_STR + (10-int(percent)//10) * UN_FINISHED_PROGRESS_STR)
