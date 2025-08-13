from typing import Dict, Any
from loguru import logger

class DataStorage:
    def __init__(self, conn):
        self.conn = conn

    def save_regular_message(self, message: Dict[str, Any]) -> None:
        """Сохраняет пересланное сообщение."""
        forward_info = message.get('forward_info', {})
        origin = forward_info.get('origin', {})


        message_id = None

        if message.get('reply_to_message_id'):
            cursor_select = None
            try:
                cursor_select = self.conn.cursor()
                cursor_select.execute("""
                        SELECT message_id 
                        FROM messages 
                        WHERE chat_id = %s AND telegram_message_id = %s
                        LIMIT 1
                    """, (message['chat_id'], message['reply_to_message_id']))

                result = cursor_select.fetchone()
                if result:
                    message_id = result[0]

            except Exception as e:
                logger.error(f"Ошибка поиска reply_to_message: {str(e)}")
            finally:
                if cursor_select:
                    cursor_select.close()

        cursor = None
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO messages (
                    telegram_message_id,
                    chat_id,
                    sender_id,
                    message_date,
                    text,
                    reply_to_message_id,
                    forward_from_chat_id,
                    forward_from_user_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chat_id, telegram_message_id) DO NOTHING
            """, (
                message['id'],
                message['chat_id'],
                message['user_id'],
                message['date'],
                message['text'],
                message_id,
                origin.get('chat_id'),
                message['forward_user_id']
            ))

            self.conn.commit()
            logger.debug(f"Сообщение {message['id']} сохранено")

        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения: {str(e)}")
            self.conn.rollback()
        finally:
            if cursor:
                cursor.close()


    def save_attachments(self, message: Dict[str, Any]) -> None:
        """Сохраняет вложения сообщения."""
        message_id = None

        if message.get('attachment_type_id'):
            cursor_select = None
            try:
                cursor_select = self.conn.cursor()
                cursor_select.execute("""
                                SELECT message_id 
                                FROM messages 
                                WHERE chat_id = %s AND telegram_message_id = %s
                                LIMIT 1
                            """, (message['chat_id'], message['id']))

                result = cursor_select.fetchone()
                if result:
                    message_id = result[0]

            except Exception as e:
                logger.error(f"Ошибка поиска message_id: {str(e)}")
            finally:
                if cursor_select:
                    cursor_select.close()

        cursor = None
        try:
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO attachments (
                        message_id,
                        type_id,
                        file_id
                    ) VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    message_id,
                    message['attachment_type_id'],
                    message['attachment_id']
                ))
            except Exception as e:
                logger.error(f"Ошибка сохранения вложения: {str(e)}")
            self.conn.commit()
            logger.debug(f"Вложения сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения вложений : {str(e)}")
            self.conn.rollback()
        finally:
            if cursor:
                cursor.close()