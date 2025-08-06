import os
from dotenv import load_dotenv

load_dotenv(".env")  # 直接加载当前目录下的 .env 文件

MySQL_PSW = os.getenv("MYSQL_PSW")
MySQL_USER = os.getenv("MYSQL_USER", "root")
MySQL_NAME = os.getenv("MYSQL_NAME", "WTB_SQL")

SESSION_KEY = os.getenv("SESSION_KEY")
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "http://127.0.0.1:5000/img/")
LOCAL_PATH = os.getenv("LOCAL_PATH")
OFFICIAL_PATH = os.getenv("OFFICIAL_PATH")

MemoryFactor = os.getenv("MemoryFactor")