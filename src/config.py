import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    PHONE_NUMBER = os.getenv("PHONE_NUMBER")
    TDLIB_PATH = os.getenv("TDLIB_PATH")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")

    DB_URL = os.getenv("DB_URL") or f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"

    ALLOWED_CHATS = list(map(int, os.getenv("ALLOWED_CHATS", "").split(',')))  # Разрешенные чаты
    BLOCKED_USERS = list(map(int, os.getenv("BLOCKED_USERS", "").split(','))) # Игнорируемые пользователи

    # Фильтр по ключевым словам
    KEYWORDS = os.getenv("KEYWORDS", "").split(',')
    FLAG_WORDS = os.getenv("FLAG_WORDS", "").split(',')

    SAVE_ATTACHMENTS = True  # Сохранять ли вложения
    IGNORE_BOTS = True  # Игнорировать сообщения от ботов