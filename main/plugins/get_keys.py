from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH
from .. import logger
from .constants import WVD_FILE_PATH
from curl_cffi import requests
import xmltodict
import base64
import logging 

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

device = Device.load(WVD_FILE_PATH)
cdm = Cdm.from_device(device)

def headers():
    return {
        'authority': 'www.udemy.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
        'accept': 'application/json, text/plain, */*',
        'dnt': '1',
        'content-type': 'application/octet-stream',
        'sec-ch-ua-mobile': '?0',
        # seems to cause cloudflare captchas to trigger
        # 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://www.udemy.com',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'accept-language': 'en-US,en;q=0.9',
    }
    
def read_pssh_from_bytes(bytes):
    pssh_offset = bytes.rfind(b'pssh')
    _start = pssh_offset - 4
    _end = pssh_offset - 4 + bytes[pssh_offset-1]
    pssh = bytes[_start:_end]
    return pssh

class UdemyKeysExtracter:
    def __init__(self) -> None:
        self.headers = headers()

    def get_pssh(self, init_url):
        logger.info(f"INIT URL: {init_url}")
        res = requests.get(init_url, headers=self.headers,impersonate="chrome110")
        if not res.ok:
            logger.exception("Could not download init segment: " + res.text)
            return
        pssh = read_pssh_from_bytes(res.content)
        return base64.b64encode(pssh).decode("utf-8")

    def extract(self, pssh, license_token):
        license_url=f"https://www.udemy.com/api-2.0/media-license-server/validate-auth-token?drm_type=widevine&auth_token={license_token}"
        logger.info(f"License URL: {license_url}")
        session_id = cdm.open()
        challenge = cdm.get_license_challenge(session_id, PSSH(pssh))
        logger.info("Sending license request now")
        license = requests.post(license_url, headers=self.headers, data=challenge,impersonate="chrome110")
        try:
            str(license.content, "utf-8")
        except:
            base64_license = base64.b64encode(license.content).decode()
            logger.info("[+] Acquired license sucessfully!")
        else:
            if "CAIS" not in license.text:
                logger.exception("[-] Couldn't to get license: [{}]\n{}".format(license.status_code, license.text))
                return

        logger.info("Trying to get keys now")
        cdm.parse_license(session_id, license.content)
        final_keys = ""
        for key in cdm.get_keys(session_id):
            logger.info(f"[+] Keys: [{key.type}] - {key.kid.hex}:{key.key.hex()}")
            if key.type == "CONTENT":
                final_keys += f"--key {key.kid.hex}:{key.key.hex()} "
        cdm.close(session_id)

        if final_keys == "":
            logger.exception("Keys were not extracted sucessfully.")
            return
        return final_keys.strip()