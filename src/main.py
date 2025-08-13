from telegram.client import Telegram
from message_handler import MessageHandler
import psycopg2
from config import Config
from data_storage import DataStorage
from chat_preloader import ChatPreloader


tg = Telegram(
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    phone=Config.PHONE_NUMBER,
    database_encryption_key='changeme1234',
    library_path=Config.TDLIB_PATH
)
state = tg.login()

data_storage = DataStorage(psycopg2.connect(Config.DB_URL))
preloader = ChatPreloader(tg, psycopg2.connect(Config.DB_URL))

preloader.preload_allowed_chats_data()

message_handler = MessageHandler(data_storage)
def new_message_handler(update):
     if 'message' in update:
         message_handler.process_message(update['message'], data_storage)

tg.add_message_handler(new_message_handler)
tg.idle()