from dotenv import load_dotenv
import os


load_dotenv()

ROOT_DIR = os.getcwd()

IS_PROD = bool(int(os.getenv("IS_PROD")))

PORT = os.getenv("PORT")
APP_LOGIN = os.getenv("APP_LOGIN")
APP_PASSWORD = os.getenv("APP_PASSWORD")

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

PG_BOUNCER_HOST = os.getenv("PG_BOUNCER_HOST")
PG_BOUNCER_PORT = os.getenv("PG_BOUNCER_PORT")

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")

ADMIN_LOGIN = os.getenv("ADMIN_LOGIN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
ADMIN_UUID = os.getenv("ADMIN_UUID")

SECRET_KEY = os.getenv("SECRET_KEY")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

SIGNAL_URL = os.getenv("SIGNAL_URL")
SIGNAL_LOGIN = os.getenv("SIGNAL_LOGIN")
SIGNAL_PASSWORD = os.getenv("SIGNAL_PASSWORD")
