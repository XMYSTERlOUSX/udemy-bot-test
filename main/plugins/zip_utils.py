#https://github.com/yash-dk/TorToolkit-Telegram/blob/master/tortoolkit/functions/zip7_utils.py

import asyncio,shlex,os,time
from typing import Union,List,Tuple
from .. import logger

async def cli_call(cmd: Union[str,List[str]]) -> Tuple[str,str]:
    if isinstance(cmd,str):
        cmd = shlex.split(cmd)
    elif isinstance(cmd,(list,tuple)):
        pass
    else:
        return None,None

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()
    
    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()
    
    return stdout, stderr, process.returncode

def get_folder_size(start_path = '.'):
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

async def split_in_zip(path:str, size=None):
    if not os.path.isdir(path) and not os.path.isfile(path):
        return None
    logger.debug(f"Starting the split for {path}")

    file_path = os.path.basename(path.rstrip("/"))
    logger.debug(f"file_path: {file_path}")
    # ahmet-birkan-temel-linux-egitimi

    full_path = os.path.dirname(path)
    logger.debug(f"full_path: {full_path}")
    # /usr/src/app/out_dir/ahmet-birkan-temel-linux-egitimi

    # compress level
    indirilenBoyut = get_folder_size(full_path)
    compressLevel = 2
    if indirilenBoyut > 5*1024*1024*1024:
      compressLevel = 1
    elif indirilenBoyut > 10*1024*1024*1024:
      compressLevel = 0

    is_file = os.path.isfile(path)

    if is_file:
        full_path = os.path.join(full_path, str(time.time()).replace(".",""))
        logger.debug(f"full_path: {full_path}")
        # /usr/src/app/out_dir/ahmet-birkan-temel-linux-egitimi/16840108342952096
        if not os.path.exists(full_path): os.mkdir(full_path)
        cmd = f'7z a -mx={compressLevel} -mmt=off -v{size}b -sdel "{full_path}/{file_path}.zip" "{path}"'
        logger.debug(f"cmd: {cmd}")
        # leech
    else:
        cmd = f'7z a -mx={compressLevel} -mmt=off -v{size}b -sdel "{full_path.rstrip("/")}.zip" "{full_path}"'
        logger.debug(f"cmd: {cmd}")
        full_path = os.path.dirname(full_path)
        logger.debug(f"full_path: {full_path}")
        # zipleech
    logger.debug(f"cmd: {cmd}")
    logger.debug(f"os.listdir(full_path): {os.listdir(full_path)}")
    _, err, _ = await cli_call(cmd)
    logger.debug(f"os.listdir(full_path): {os.listdir(full_path)}")
    if not is_file and len(os.listdir(full_path)) == 1:
        # tek dosya
        logger.debug(f"tek dosya çıktı: {cmd}")
        try:
            ad = os.listdir(full_path)[0]
            logger.debug(f"ad: {ad}")
            yeniad = '7z'.join(ad.rsplit('zip.001', 1))
            logger.debug(f"yeniad: {yeniad}")
            os.rename(os.path.join(full_path, ad), os.path.join(full_path, yeniad))
        except Exception as t:
            logger.error(str(t))
    if not err:
        logger.debug(f"full_path: {full_path}")
        return full_path
        # /usr/src/app/out_dir/ahmet-birkan-temel-linux-egitimi/16840108342952096
    logger.error(f"Error in zip split {err}")
    return None
    