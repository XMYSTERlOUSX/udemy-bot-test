from main import DATABASE_URI
from main.plugins import premiumUser
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)

from pymongo import MongoClient
dbcli = MongoClient(DATABASE_URI)
mydb = dbcli["Cluster0"]
coursedb = mydb['course']
coursedb.create_index("i",unique=True)


def is_downloaded(courseID:int) -> bool:
    courseID = int(courseID)
    return courseID in premiumUser.downloaded_courses
    # return coursedb.count_documents({'i':courseID}) == 1

def make_downloaded(courseID:int):
    courseID = int(courseID)
    if courseID not in premiumUser.downloaded_courses:
        premiumUser.downloaded_courses.append(courseID)
    coursedb.insert_one({'i':courseID})

def make_undownloaded(courseID:int):
    courseID = int(courseID)
    if courseID in premiumUser.downloaded_courses:
        premiumUser.downloaded_courses.remove(courseID)
    coursedb.delete_one({'i':courseID})

def get_down_count() -> int:
    return coursedb.count_documents({})

def get_courses_list() -> list:
    return [i['i'] for i in coursedb.find({})]
