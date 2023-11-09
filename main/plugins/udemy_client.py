import json
import re
import sys
import time
import cloudscraper
import requests
import m3u8
import base64
from html.parser import HTMLParser as compat_HTMLParser
import yt_dlp
from .. import IS_SUBSCRIPTION_COURSE, PROXIES, SessionVars
from .constants import *
from requests.exceptions import ConnectionError as conn_error
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def course_dl_log(string:str):
    string = str(string).strip().replace("\n\n", "\n").strip('\n')

    logger.info(string) # zorgof
    with open("indirici.txt","+a",encoding="utf-8") as file:
        sit = f"{string}\n"
        file.write(sit)

class Udemy:
   
    def __init__(self, bearer_token):
        self.session = None
        self.bearer_token = None
        self.auth = UdemyAuth(cache_session=False)
        if not self.session:
            self.session, self.bearer_token = self.auth.authenticate(
                bearer_token=bearer_token)

        if self.session and self.bearer_token:
            self.session._headers.update(
                {"Authorization": "Bearer {}".format(self.bearer_token)})
            self.session._headers.update({
                "X-Udemy-Authorization":
                "Bearer {}".format(self.bearer_token)
            })
            course_dl_log("[+] Login Success")
        else:
            course_dl_log("[X] Login Failure! You are probably missing an access token!")
            sys.exit(1)

    def _extract_supplementary_assets(self, supp_assets, lecture_counter):
        _temp = []
        for entry in supp_assets:
            title = sanitize_filename(entry.get("title"))
            filename = entry.get("filename")
            download_urls = entry.get("download_urls")
            external_url = entry.get("external_url")
            asset_type = entry.get("asset_type").lower()
            id = entry.get("id")
            if asset_type == "file":
                if download_urls and isinstance(download_urls, dict):
                    extension = filename.rsplit(
                        ".", 1)[-1] if "." in filename else ""
                    download_url = download_urls.get("File", [])[0].get("file")
                    _temp.append({
                        "type": "file",
                        "title": title,
                        "filename": "{0:03d} ".format(
                            lecture_counter) + filename,
                        "extension": extension,
                        "download_url": download_url,
                        "id": id
                    })
            elif asset_type == "sourcecode":
                if download_urls and isinstance(download_urls, dict):
                    extension = filename.rsplit(
                        ".", 1)[-1] if "." in filename else ""
                    download_url = download_urls.get("SourceCode",
                                                     [])[0].get("file")
                    _temp.append({
                        "type": "source_code",
                        "title": title,
                        "filename": "{0:03d} ".format(
                            lecture_counter) + filename,
                        "extension": extension,
                        "download_url": download_url,
                        "id": id
                    })
            elif asset_type == "externallink":
                _temp.append({
                    "type": "external_link",
                    "title": title,
                    "filename": "{0:03d} ".format(
                            lecture_counter) + filename,
                    "extension": "txt",
                    "download_url": external_url,
                    "id": id
                })
        return _temp

    def _extract_ppt(self, asset, lecture_counter):
        _temp = []
        download_urls = asset.get("download_urls")
        filename = asset.get("filename")
        id = asset.get("id")
        if download_urls and isinstance(download_urls, dict):
            extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
            download_url = download_urls.get("Presentation", [])[0].get("file")
            _temp.append({
                "type": "presentation",
                "filename": "{0:03d} ".format(
                            lecture_counter) + filename,
                "extension": extension,
                "download_url": download_url,
                "id": id
            })
        return _temp

    def _extract_file(self, asset, lecture_counter):
        _temp = []
        download_urls = asset.get("download_urls")
        filename = asset.get("filename")
        id = asset.get("id")
        if download_urls and isinstance(download_urls, dict):
            extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
            download_url = download_urls.get("File", [])[0].get("file")
            _temp.append({
                "type": "file",
                "filename": "{0:03d} ".format(
                            lecture_counter) + filename,
                "extension": extension,
                "download_url": download_url,
                "id": id
            })
        return _temp

    def _extract_ebook(self, asset, lecture_counter):
        _temp = []
        download_urls = asset.get("download_urls")
        filename = asset.get("filename")
        id = asset.get("id")
        if download_urls and isinstance(download_urls, dict):
            extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
            download_url = download_urls.get("E-Book", [])[0].get("file")
            _temp.append({
                "type": "ebook",
                "filename": "{0:03d} ".format(
                            lecture_counter) + filename,
                "extension": extension,
                "download_url": download_url,
                "id": id
            })
        return _temp

    def _extract_audio(self, asset, lecture_counter):
        _temp = []
        download_urls = asset.get("download_urls")
        filename = asset.get("filename")
        id = asset.get("id")
        if download_urls and isinstance(download_urls, dict):
            extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
            download_url = download_urls.get("Audio", [])[0].get("file")
            _temp.append({
                "type": "audio",
                "filename": "{0:03d} ".format(
                            lecture_counter) + filename,
                "extension": extension,
                "download_url": download_url,
                "id": id
            })
        return _temp

    def _extract_sources(self, sources, skip_hls):
        _temp = []
        if sources and isinstance(sources, list):
            for source in sources:
                label = source.get("label")
                download_url = source.get("file")
                if not download_url:
                    continue
                if label.lower() == "audio":
                    continue
                height = label if label else None
                if height == "2160":
                    width = "3840"
                elif height == "1440":
                    width = "2560"
                elif height == "1080":
                    width = "1920"
                elif height == "720":
                    width = "1280"
                elif height == "480":
                    width = "854"
                elif height == "360":
                    width = "640"
                elif height == "240":
                    width = "426"
                else:
                    width = "256"
                if (source.get("type") == "application/x-mpegURL"
                        or "m3u8" in download_url):
                    if not skip_hls:
                        out = self._extract_m3u8(download_url)
                        if out:
                            _temp.extend(out)
                else:
                    _type = source.get("type")
                    _temp.append({
                        "type": "video",
                        "height": height,
                        "width": width,
                        "extension": _type.replace("video/", ""),
                        "download_url": download_url,
                    })
        return _temp

    def _extract_media_sources(self, sources):
        _temp = []
        if sources and isinstance(sources, list):
            for source in sources:
                _type = source.get("type")
                src = source.get("src")

                if _type == "application/dash+xml":
                    out = self._extract_mpd(src)
                    if out:
                        _temp.extend(out)
        return _temp

    def _extract_subtitles(self, tracks):
        _temp = []
        if tracks and isinstance(tracks, list):
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                if track.get("_class") != "caption":
                    continue
                download_url = track.get("url")
                if not download_url or not isinstance(download_url, str):
                    continue
                lang = (track.get("language") or track.get("srclang")
                        or track.get("label")
                        or track["locale_id"].split("_")[0])
                ext = "vtt" if "vtt" in download_url.rsplit(".",
                                                            1)[-1] else "srt"
                _temp.append({
                    "type": "subtitle",
                    "language": lang,
                    "extension": ext,
                    "download_url": download_url,
                })
        return _temp

    def _extract_m3u8(self, url):
        """extracts m3u8 streams"""
        _temp = []
        try:
            resp = self.session._get(url)
            resp.raise_for_status()
            raw_data = resp.text
            m3u8_object = m3u8.loads(raw_data)
            playlists = m3u8_object.playlists
            seen = set()
            for pl in playlists:
                resolution = pl.stream_info.resolution
                codecs = pl.stream_info.codecs
                if not resolution:
                    continue
                if not codecs:
                    continue
                width, height = resolution
                download_url = pl.uri
                if height not in seen:
                    seen.add(height)
                    _temp.append({
                        "type": "hls",
                        "height": height,
                        "width": width,
                        "extension": "mp4",
                        "download_url": download_url,
                    })
        except Exception as error:
            course_dl_log( f"[!] Udemy Says : '{error}' while fetching hls streams.")
        return _temp

    def _extract_mpd(self, url):
        """extracts mpd streams"""
        course_dl_log(f"[+] Fetching MPD streams: {url}")
        _temp = []
        try:
            ytdl = yt_dlp.YoutubeDL({
                'quiet': True,
                'no_warnings': True,
                "allow_unplayable_formats": True
            })
            results = ytdl.extract_info(url,
                                        download=False,
                                        force_generic_extractor=True)
            seen = set()
            formats = results.get("formats")

            format_id = results.get("format_id")
            best_audio_format_id = format_id.split("+")[1]
            # I forget what this was for
            # best_audio = next((x for x in formats
            #                    if x.get("format_id") == best_audio_format_id),
            #                   None)
            for f in formats:
                if "video" in f.get("format_note"):
                    # is a video stream
                    format_id = f.get("format_id")
                    extension = f.get("ext")
                    height = f.get("height")
                    width = f.get("width")
                    init_url = f.get("fragments")[0]["url"]

                    if height and height not in seen:
                        seen.add(height)
                        _temp.append({
                            "type": "dash",
                            "height": str(height),
                            "width": str(width),
                            "format_id": f"{format_id},{best_audio_format_id}",
                            "extension": extension,
                            "download_url": f.get("manifest_url"),
                            "init_url": init_url
                        })
                else:
                    # unknown format type
                    course_dl_log(f"[!] Unknown format type: {str(f)}")
                    continue
        except Exception as e:
            course_dl_log(f"[!] Error fetching MPD streams: {str(e)}")
        return _temp

    def extract_course_name(self, url):
        """
        @author r0oth3x49
        """
        obj = re.search(
            r"(?i)(?://(?P<portal_name>.+?).udemy.com/(?:course(/draft)*/)?(?P<name_or_id>[a-zA-Z0-9_-]+))",
            url,
        )
        if obj:
            return obj.group("portal_name"), obj.group("name_or_id")

    def extract_portal_name(self, url):
        obj = re.search(r"(?i)(?://(?P<portal_name>.+?).udemy.com)", url)
        if obj:
            return obj.group("portal_name")

    def _subscribed_courses(self, portal_name, course_name):
        results = []
        self.session._headers.update({
            "Host":
            "{portal_name}.udemy.com".format(portal_name=portal_name),
            "Referer":
            "https://{portal_name}.udemy.com/home/my-courses/search/?q={course_name}"
            .format(portal_name=portal_name, course_name=course_name),
        })
        url = COURSE_SEARCH.format(portal_name=portal_name,
                                   course_name=course_name)
        try:
            webpage = self.session._get(url).content
            webpage = webpage.decode("utf-8", "ignore")
            webpage = json.loads(webpage)
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        except (ValueError, Exception) as error:
            course_dl_log(f"[X] Udemy Says: {error} on {url}")
            time.sleep(0.8)
            sys.exit(1)
        else:
            results = webpage.get("results", [])
        return results

    def _extract_course_info_json(self, url, course_id, portal_name):
        self.session._headers.update({"Referer": url})
        url = COURSE_INFO_URL.format(
            portal_name=portal_name, course_id=course_id)
        try:
            resp = self.session._get(url).json()
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        else:
            return resp

    def _extract_course_json(self, url, course_id, portal_name):
        self.session._headers.update({"Referer": url})
        url = COURSE_URL.format(portal_name=portal_name, course_id=course_id)
        try:
            resp = self.session._get(url)
            if not resp:
                return None
            if resp.status_code in [502, 503, 504]:
                course_dl_log(
                    "> The course content is large, using large content extractor..."
                )
                resp = self._extract_large_course_content(url=url)
            else:
                resp = resp.json()
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        except (ValueError, Exception):
            resp = self._extract_large_course_content(url=url)
            return resp
        else:
            return resp

    def _extract_large_course_content(self, url):
        url = url.replace("10000", "50") if url.endswith("10000") else url
        try:
            data = self.session._get(url).json()
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        else:
            _next = data.get("next")
            while _next:
                course_dl_log("> Downloading course information.")
                try:
                    resp = self.session._get(_next).json()
                except conn_error as error:
                    course_dl_log(f"[X] Udemy Says: Connection error: {error}")
                    time.sleep(0.8)
                    sys.exit(1)
                else:
                    _next = resp.get("next")
                    results = resp.get("results")
                    if results and isinstance(results, list):
                        for d in resp["results"]:
                            data["results"].append(d)
            return data

    def _extract_media_license_token(self, url, course_id, lecture_id, portal_name, original_license_token):
        token_data = original_license_token.split(".")[1].split(".")[0]
        decoded_token = true_urlsafe_b64decode(token_data).decode()

        token_exp_time = json.loads(decoded_token)["exp"]
        if time.time()>float(token_exp_time):
            course_dl_log("> Original media license token is expired... Trying to obtain a new token now!")
        else:
            course_dl_log(f"> Original License Token [Still Valid]: {original_license_token}")
            return original_license_token

        self.session._headers.update({"Referer": url})
        url = SINGLE_COURSE_URL.format(portal_name=portal_name, course_id=course_id, lecture_id=lecture_id)
        try:
            resp = self.session._get(url).json()["asset"]["media_license_token"]
        except Exception as error:
            course_dl_log(f"[X] Error: {error}\n\nThe above error was caused while trying to get a new media license token!")
            time.sleep(0.8)
            sys.exit(1)
        else:
            course_dl_log(f"> New License Token: {resp}")
            return resp

    def _extract_course(self, response, course_name):
        _temp = {}
        if response:
            for entry in response:
                course_id = str(entry.get("id"))
                published_title = entry.get("published_title")
                if course_name in (published_title, course_id):
                    _temp = entry
                    break
        return _temp

    def _my_courses(self, portal_name):
        results = []
        try:
            url = MY_COURSES_URL.format(portal_name=portal_name)
            webpage = self.session._get(url).json()
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        except (ValueError, Exception) as error:
            course_dl_log(f"[X] Udemy Says: {error}")
            time.sleep(0.8)
            sys.exit(1)
        else:
            results = webpage.get("results", [])
        return results

    def _subscribed_collection_courses(self, portal_name):
        url = COLLECTION_URL.format(portal_name=portal_name)
        courses_lists = []
        try:
            webpage = self.session._get(url).json()
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        except (ValueError, Exception) as error:
            course_dl_log(f"[X] Udemy Says: {error}")
            time.sleep(0.8)
            sys.exit(1)
        else:
            results = webpage.get("results", [])
            if results:
                [
                    courses_lists.extend(courses.get("courses", []))
                    for courses in results if courses.get("courses", [])
                ]
        return courses_lists

    def _archived_courses(self, portal_name):
        results = []
        try:
            url = MY_COURSES_URL.format(portal_name=portal_name)
            url = f"{url}&is_archived=true"
            webpage = self.session._get(url).json()
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        except (ValueError, Exception) as error:
            course_dl_log(f"[X] Udemy Says: {error}")
            time.sleep(0.8)
            sys.exit(1)
        else:
            results = webpage.get("results", [])
        return results

    def _my_courses(self, portal_name):
        results = []
        try:
            url = MY_COURSES_URL.format(portal_name=portal_name)
            webpage = self.session._get(url).json()
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        except (ValueError, Exception) as error:
            course_dl_log(f"[X] Udemy Says: {error}")
            time.sleep(0.8)
            sys.exit(1)
        else:
            results = webpage.get("results", [])
        return results

    def _subscribed_collection_courses(self, portal_name):
        url = COLLECTION_URL.format(portal_name=portal_name)
        courses_lists = []
        try:
            webpage = self.session._get(url).json()
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        except (ValueError, Exception) as error:
            course_dl_log(f"[X] Udemy Says: {error}")
            time.sleep(0.8)
            sys.exit(1)
        else:
            results = webpage.get("results", [])
            if results:
                [
                    courses_lists.extend(courses.get("courses", []))
                    for courses in results if courses.get("courses", [])
                ]
        return courses_lists

    def _archived_courses(self, portal_name):
        results = []
        try:
            url = MY_COURSES_URL.format(portal_name=portal_name)
            url = f"{url}&is_archived=true"
            webpage = self.session._get(url).json()
        except conn_error as error:
            course_dl_log(f"[X] Udemy Says: Connection error: {error}")
            time.sleep(0.8)
            sys.exit(1)
        except (ValueError, Exception) as error:
            course_dl_log(f"[X] Udemy Says: {error}")
            time.sleep(0.8)
            sys.exit(1)
        else:
            results = webpage.get("results", [])
        return results

    def _extract_subscription_course_info(self, url):
        try:
            course_html = self.session._get(url).text
        except Exception:
            return None, None
        soup = BeautifulSoup(course_html, "lxml")
        data = soup.find("div", {"class": "ud-component--course-taking--app"})
        if not data:
            course_dl_log("[!] Unable to extract arguments from course page! Make sure you have a cookies.txt file!")
            self.session.terminate()
            return
        data_args = data.attrs["data-module-args"]
        data_json = json.loads(data_args)
        course_id = data_json.get("courseId", None)
        portal_name = self.extract_portal_name(url)
        return course_id, portal_name

    def _extract_course_info(self, url):
        portal_name, course_name = self.extract_course_name(url)
        course = {}

        if not IS_SUBSCRIPTION_COURSE:
            results = self._subscribed_courses(portal_name=portal_name,
                                               course_name=course_name)
            course = self._extract_course(response=results,
                                          course_name=course_name)
            if not course:
                results = self._my_courses(portal_name=portal_name)
                course = self._extract_course(response=results,
                                              course_name=course_name)
            if not course:
                results = self._subscribed_collection_courses(
                    portal_name=portal_name)
                course = self._extract_course(response=results,
                                              course_name=course_name)
            if not course:
                results = self._archived_courses(portal_name=portal_name)
                course = self._extract_course(response=results,
                                              course_name=course_name)

        if not course or IS_SUBSCRIPTION_COURSE:
            course_id, portal_name = self._extract_subscription_course_info(url)
            if not course_id and not portal_name:
                return None, None
            course = self._extract_course_info_json(url, course_id, portal_name)

        if course:
            course.update({"portal_name": portal_name})
            return course.get("id"), course
        if not course:
            course_dl_log(
                "X Downloading course information, course id not found .. ")
            course_dl_log(
                "X It seems either you are not enrolled or you have to visit the course atleast once while you are logged in.",
            )
            course_dl_log("Trying to logout now...", )
            self.session.terminate()
            course_dl_log("Logged out successfully.", )
            sys.exit(1)


class UdemyAuth(object):
    def __init__(self, username="", password="", cache_session=False):
        self.username = username
        self.password = password
        self._cache = cache_session
        self._session = Session()
        self._cloudsc = cloudscraper.create_scraper()

    def _form_hidden_input(self, form_id):
        try:
            resp = self._cloudsc.get(LOGIN_URL)
            resp.raise_for_status()
            webpage = resp.text
        except conn_error as error:
            raise error
        else:
            login_form = hidden_inputs(
                search_regex(
                    r'(?is)<form[^>]+?id=(["\'])%s\1[^>]*>(?P<form>.+?)</form>'
                    % form_id,
                    webpage,
                    "%s form" % form_id,
                    group="form",
                ))
            login_form.update({
                "email": self.username,
                "password": self.password
            })
            return login_form

    def authenticate(self, bearer_token=""):
        if bearer_token:
            self._session._set_auth_headers(bearer_token=bearer_token)
            self._session._session.cookies.update(
                {"bearer_token": bearer_token})
            return self._session, bearer_token
        else:
            self._session._set_auth_headers()
            return None, None

class Session(object):
    def __init__(self):
        self._headers = HEADERS
        self._session = requests.sessions.Session()

    def _set_auth_headers(self, bearer_token=""):
        self._headers["Authorization"] = "Bearer {}".format(bearer_token)
        self._headers["X-Udemy-Authorization"] = "Bearer {}".format(bearer_token)
        self._headers["Cookie"] = SessionVars.get_var("COOKIES") 

    def _get(self, url):
        for i in range(10):
            session = self._session.get(url, headers=self._headers, proxies=PROXIES)
            with open("requests.txt", "a") as request_data_file:
                request_data_file.write(f"url={url}\nheaders={str(session.request.headers)}\ncookies={str(self._session.cookies.get_dict())}\n\n")
                request_data_file.close()
            #course_dl_log(session.request.headers)
            #course_dl_log(f"cookies:- {self._session.cookies.get_dict()}\n")
            #course_dl_log(f"headers:- {session.request.headers}\n")
            if session.ok or session.status_code in [502, 503]:
                return session
            if not session.ok:
                course_dl_log('[!] Failed request '+ url)
                course_dl_log(f"[!] {session.status_code} {session.reason}, retrying (attempt {i} )...")
                time.sleep(0.8)

    def _post(self, url, data, redirect=True):
        session = self._session.post(url, data, headers=self._headers, allow_redirects=redirect, proxies=PROXIES)
        if session.ok:
            return session
        if not session.ok:
            raise Exception(f"{session.status_code} {session.reason}")

    def terminate(self):
        self._set_auth_headers()
        return

# Thanks to a great open source utility youtube-dl ..
class HTMLAttributeParser(compat_HTMLParser):  # pylint: disable=W
    """Trivial HTML parser to gather the attributes for a single element"""

    def __init__(self):
        self.attrs = {}
        compat_HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        self.attrs = dict(attrs)

def search_regex(pattern,
                 string,
                 name,
                 default=object(),
                 fatal=True,
                 flags=0,
                 group=None):
    """
    Perform a regex search on the given string, using a single or a list of
    patterns returning the first matching group.
    In case of failure return a default value or raise a WARNING or a
    RegexNotFoundError, depending on fatal, specifying the field name.
    """
    if isinstance(pattern, str):
        mobj = re.search(pattern, string, flags)
    else:
        for p in pattern:
            mobj = re.search(p, string, flags)
            if mobj:
                break

    _name = name

    if mobj:
        if group is None:
            # return the first matching group
            return next(g for g in mobj.groups() if g is not None)
        else:
            return mobj.group(group)
    elif default is not object():
        return default
    elif fatal:
        course_dl_log("[-] Unable to extract %s" % _name)
        exit(0)
    else:
        course_dl_log("[-] unable to extract %s" % _name)
        exit(0)


def hidden_inputs(html):
    html = re.sub(r"<!--(?:(?!<!--).)*-->", "", html)
    hidden_inputs = {}  # pylint: disable=W
    for entry in re.findall(r"(?i)(<input[^>]+>)", html):
        attrs = extract_attributes(entry)
        if not entry:
            continue
        if attrs.get("type") not in ("hidden", "submit"):
            continue
        name = attrs.get("name") or attrs.get("id")
        value = attrs.get("value")
        if name and value is not None:
            hidden_inputs[name] = value
    return hidden_inputs

def extract_attributes(html_element):
    """Given a string for an HTML element such as
    <el
    a="foo" B="bar" c="&98;az" d=boz
    empty= noval entity="&amp;"
    sq='"' dq="'"
    >
    Decode and return a dictionary of attributes.
    {
    'a': 'foo', 'b': 'bar', c: 'baz', d: 'boz',
    'empty': '', 'noval': None, 'entity': '&',
    'sq': '"', 'dq': '\''
    }.
    NB HTMLParser is stricter in Python 2.6 & 3.2 than in later versions,
    but the cases in the unit test will work for all of 2.6, 2.7, 3.2-3.5.
    """
    parser = HTMLAttributeParser()
    try:
        parser.feed(html_element)
        parser.close()
    except Exception:  # pylint: disable=W
        pass
    return parser.attrs

def true_urlsafe_b64decode(s):
    return base64.urlsafe_b64decode(s + ('=' * (4 - (len(s) % 4))))