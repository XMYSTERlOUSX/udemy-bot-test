import logging
from shutil import rmtree
from main.plugins.constants import DOWNLOAD_DIR
from . import mp4parse
import codecs
import base64
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# def extract_kid(mp4_file):
    # """
    # Parameters
    # ----------
    # mp4_file : str
        # MP4 file with a PSSH header

    # Returns
    # -------
    # String

    # """

    # boxes = mp4parse.F4VParser.parse(filename=mp4_file)
    # if not os.path.exists(mp4_file):
        # raise Exception("File does not exist")
    # for box in boxes:
        # if box.header.box_type == 'moov':
            # pssh_box = next(x for x in box.pssh if x.system_id == "edef8ba979d64acea3c827dcd51d21ed")
            # hex = codecs.decode(pssh_box.payload, "hex")

            # pssh = widevine_pssh_pb2.WidevinePsshData()
            # pssh.ParseFromString(hex)
            # content_id = base64.b16encode(pssh.content_id)
            # return content_id.decode("utf-8")

    # # No Moof or PSSH header found
    # return None

def clean_all():
    try:
        rmtree(DOWNLOAD_DIR)
    except:
        pass

def clean_download(path: str):
     if os.path.exists(path):
        logger.info(f"Cleaning Download: {path}")
        try:
            rmtree(path)
        except:
            pass
        os.makedirs(DOWNLOAD_DIR)

async def get_rc_config():
        config = os.path.join(os.getcwd(), 'rclone.conf')
        if config is not None:
            if isinstance(config, str):
                if os.path.exists(config):
                    return config
        return None

def get_size(start_path = '.'):
    if os.path.isfile(start_path):
        return os.path.getsize(start_path)
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


def progress_bar(percentage):
    # percentage is on the scale of 0-1
    comp = "▰"
    ncomp = "▱"
    pr = ""

    if isinstance(percentage, str):
        return "NaN"

    try:
        percentage = int(percentage)
    except:
        percentage = 0

    for i in range(1, 11):
        if i <= int(percentage / 10):
            pr += comp
        else:
            pr += ncomp
    return pr                             


