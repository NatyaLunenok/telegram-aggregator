import psycopg2
from loguru import logger
from datetime import datetime
from typing import Optional, Dict, Any
from config import Config
from filters import is_relevant
from data_storage import DataStorage


class MessageHandler:
    def __init__(self, ds):
        self.ds = ds
        self.conn = psycopg2.connect(Config.DB_URL)

    def process_message(self, message: Dict[str, Any], ds: DataStorage) -> None:
        """Основной метод обработки входящего сообщения."""
        logger.debug(f"Входящее сообщение {message.get('content')}")
        try:
            if not self.should_process(message):
                return

            message_db = {}
            message_db['id'] = message['id']
            message_db['chat_id'] = message['chat_id']
            message_db['user_id'] = self.extract_user_id(message.get('sender_id'))
            message_db['date'] = datetime.fromtimestamp(message.get('date', 0))
            if message.get('content').get('text'):
                message_db['text'] = str(message.get('content', {}).get('text', {}).get('text', '')).lower()
            elif message.get('content').get('caption'):
                message_db['text'] = str(message.get('content').get('caption', {}).get('text', ''))
            message_db['is_outgoing'] = message.get('is_outgoing', False)
            message_db['forward_user_id'] = None
            if message.get('forward_info'):
                message_db['forward_user_id'] = message.get('forward_info').get('origin').get('sender_user_id')

            message_db['reply_to_message_id'] = None
            if message.get('reply_to'):
                message_db['reply_to_message_id'] = message.get('reply_to').get('message_id')

            ds.save_regular_message(message_db)

            if message['content'].get('document'):
                attachment = message['content']['document']['document']
                message_db['attachment_type_id'] = self.get_attachment_type_id(attachment.get('@type'))
                message_db['attachment_id'] = attachment.get('file_id') or attachment.get('id')
            elif message['content'].get('photo'):
                attachment = message['content']['photo'] #['photo']
                message_db['attachment_type_id'] = self.get_attachment_type_id(attachment.get('@type'))
                # message_db['attachment_id'] = attachment.get('file_id') or attachment.get('id')
                message_db['attachment_id'] = None
            elif message['content'].get('video'):
                attachment = message['content']['video']['video']
                message_db['attachment_type_id'] = self.get_attachment_type_id(attachment.get('@type'))
                message_db['attachment_id'] = attachment.get('file_id') or attachment.get('id')

            if message_db.get('attachment_type_id'):
                ds.save_attachments(message_db)

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {str(e)}")
            logger.debug(f"Сообщение вызвавшее ошибку: {message}")

    def should_process(self, message: Dict[str, Any]) -> bool:
        """Проверяет, нужно ли обрабатывать сообщение."""
        if not message or not isinstance(message, dict):
            return False
        return is_relevant(message)

    @staticmethod
    def extract_user_id(sender: Any) -> Optional[int]:
        if isinstance(sender, dict):
            return sender.get('user_id')
        elif isinstance(sender, (int, str)):
            return int(sender)
        return None

    def get_attachment_type_id(self, attachment_type: Optional[str]) -> int:
        """Получает ID типа вложения из БД по названию типа"""
        if not attachment_type:
            return 3

        cursor = self.ds.conn.cursor()
        try:
            attachment_type = str(attachment_type).lower()

            cursor.execute(
                "SELECT type_id FROM attachment_types WHERE type_name = %s LIMIT 1",
                (attachment_type,)
            )
            result = cursor.fetchone()

            return result[0] if result else 3
        except Exception as e:
            logger.error(f"Ошибка получения type_id для вложения {attachment_type}: {e}")
            return 3
        finally:
            cursor.close()
