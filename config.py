import os
from dotenv import load_dotenv
load_dotenv("inform.env")


MySQL_PSW = os.getenv("MYSQL_PSW", "default_password")
SESSION_KEY = os.getenv("SESSION_KEY")
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "http://127.0.0.1:5000/img/")
LOCAL_PATH = os.getenv("LOCAL_PATH")
OFFICIAL_PATH = os.getenv("OFFICIAL_PATH")
MemoryFactor = float( 4/7)