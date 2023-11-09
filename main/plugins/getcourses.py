# HuzunluArtemis - 2021 (Licensed under GPL-v3)

from curl_cffi import requests

from main import PROXIES
from main.plugins.downloaded import is_downloaded
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_json_data(page_num, ACCESS_TOKEN):
    headers = {
        'authority': 'www.udemy.com',
        'authorization': f'Bearer {ACCESS_TOKEN}',
        'user-agent':
        "Opera/9.80 (Windows NT 5.1; U; sk) Presto/2.5.22 Version/10.50",
        'x-udemy-authorization':
        f'Bearer {ACCESS_TOKEN}',
    }

    params = (
        ('ordering', '-enroll_time'),
        ('fields^/[course^/]',
         '^@min,visible_instructors,image_240x135,favorite_time,archive_time,completion_ratio,last_accessed_time,enrollment_time,is_practice_test_course,features,num_collections,published_title,is_private,is_published,buyable_object_type'
         ),
        ('fields^/[user^/]', '^@min,job_title'),
        ('page', str(page_num)),
        ('page_size', '100'),
        ('is_archived', 'false'),
    )

    response = requests.get(
        'https://www.udemy.com/api-2.0/users/me/subscribed-courses/',
        headers=headers, params = params, proxies=PROXIES, impersonate="chrome110")
    print(response.text)
    return response.json()


async def get_all_courses(ACCESS_TOKEN, sadelink, tumu, count=True):
    allUrls = ""
    say = 1
    last_page_reached = False
    curr_page = 1
    total_courses = 0
    while True:
        json_data = get_json_data(curr_page, ACCESS_TOKEN)
        logger.info(f"get_all_courses page: {curr_page}")
        rtru = json_data.get('detail', None) # detail
        # with open('courses' + str(curr_page) + ".txt", 'w', encoding="utf-8") as file: file.write(json.dumps(json_data, indent=4))
        if rtru in ['Invalid page.', 'Ge\u00e7ersiz sayfa.']:
            last_page_reached = True
            break
        if not json_data.get('results', None):
            return 'wrong token?'
        total_courses += len(json_data["results"])
        for course in json_data['results']:
            if (not tumu) and is_downloaded(course['id']):
                continue
            if sadelink:
                if count:
                    allUrls += f"{say}: "
                allUrls += f"https://www.udemy.com{course['url']}\n"
                say += 1
                continue
            course_url = f"https://www.udemy.com{course['url']}"
            allUrls += f"{say}: " + course['title']
            allUrls += f" ({course['price']})"
            allUrls += "\n" + course_url
            allUrls += "\n" + course['visible_instructors'][0]['title']
            allUrls += f" ({course['visible_instructors'][0]['job_title']})"
            allUrls += "\nhttps://www.udemy.com" + course['visible_instructors'][0]['url']
            allUrls += "\n\n"
            say += 1
        curr_page += 1
    return allUrls.strip("\n") if last_page_reached else 'son sayfaya gelinemedi'

async def get_course_info(courseid:str, ACCESS_TOKEN):
    courseid = str(courseid).replace('https://www.udemy.com/course/draft/', '')
    courseid  = courseid.replace('https://www.udemy.com/course/', '')
    courseid = courseid.replace('/learn/', '')

    toget = f"https://www.udemy.com/api-2.0/courses/{courseid}/"
    headers = {
        'Accept-Language': 'tr-TR',
        'authority': 'www.udemy.com',
        'authorization': f'Bearer {ACCESS_TOKEN}',
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A",
            #"Opera/9.80 (Windows NT 5.1; U; sk) Presto/2.5.22 Version/10.50",
        'x-udemy-authorization': f'Bearer {ACCESS_TOKEN}',
        # sonrasını ben ekledim
        'ud_cache_language': 'en',
        'ud_cache_price_country': 'TR',
        'ud_cache_logged_in': '1',
        'seen': '1',

    }
    json = requests.get(url=toget,headers=headers,impersonate="chrome110").json()
    # LOGGER.info(json)
    id = json.get('id')
    url = json.get('url')
    url = f'https://www.udemy.com{url}learn/'
    title = json.get('title')

    price = json.get('price_detail')
    price = price.get('price_string') if price else'Ücretsiz'
    
    courser = json.get('visible_instructors')[0].get('title')
    job_title = json.get('visible_instructors')[0].get('job_title') 
    courser_url = json.get('visible_instructors')[0].get('url')
    courser_url = f'https://www.udemy.com{courser_url}'
    return id, url, title, price, courser, job_title, courser_url
