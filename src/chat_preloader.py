from datetime import datetime
from typing import Dict, Any
from config import Config
from loguru import logger


class ChatPreloader:
    def __init__(self, tg_client, dbconn):
        self.tg = tg_client
        self.dbconn = dbconn

    def preload_allowed_chats_data(self):
        for chat_id in Config.ALLOWED_CHATS:
            self.load_and_update_chat_data(chat_id)

    def load_and_update_chat_data(self, chat_id: int):
        """Загружает и обновляет данные чата и его участников"""
        logger.info(f"Обновление данных для чата {chat_id}")

        try:
            chat_result = self.tg.get_chat(chat_id)
            chat_result.wait()

            if hasattr(chat_result, 'update'):
                chat_info = chat_result.update
            elif isinstance(chat_result, dict):
               chat_info = chat_result
            else:
                logger.error(f"Неподдерживаемый формат данных чата: {type(chat_result)}")
                return
            logger.debug(f"Информация о чате: {chat_info}")

            if not all(key in chat_info for key in ['id', 'type']):
                logger.error(f"Неполные данные чата: {chat_info.keys()}")
                return

            self.upsert_chat_info(chat_info)
            logger.debug(f"Завершение обновления информации чата")
            logger.debug(f"Тип чата {chat_info['type']['@type']}")

            if chat_info['type']['@type'] in ['chatTypeBasicGroup', 'chatTypeSupergroup']:
                if chat_info['type']['@type'] == 'chatTypeBasicGroup':
                    group_result = self.tg.call_method('getBasicGroupFullInfo', {'basic_group_id': chat_info['type']['basic_group_id']})
                    group_result.wait()
                    group_info = group_result.update
                else:
                    group_info = self.tg.get_supergroup_full_info(
                        chat_info['type']['supergroup_id']
                    )
                    group_info.wait()
                if hasattr(group_info, 'members'):
                    self.process_group_members(chat_id, group_info.members)
                elif isinstance(group_info, dict):
                    self.process_group_members(chat_id, group_info.get('members', []))

        except RuntimeError as e:
            logger.error(f"Ошибка при обработке чата {chat_id}: {str(e)}")
        finally:
            pass

    def upsert_chat_info(self, chat_info: dict):
        """Обновляет или создает запись о чате"""
        logger.debug(f"Обновление информации чата {chat_info['id']}")

        chat_data = {
            'chat_id': chat_info['id'],
            'title': chat_info.get('title'),
            'type_id': self.get_chat_type_id(chat_info['type']['@type']),
            'description': chat_info.get('description', ''),
            'chatname': chat_info.get('usernames', {}).get('active_usernames', [None])[0],
            'is_verified': chat_info.get('is_verified', False),
            'is_scam': chat_info.get('is_scam', False),
        }

        cursor = self.dbconn.cursor()
        try:
            cursor.execute("""
                INSERT INTO chats (
                    chat_id, title, type_id, description,
                    chatname, is_verified, is_scam
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chat_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    chatname = EXCLUDED.chatname,
                    is_verified = EXCLUDED.is_verified,
                    is_scam = EXCLUDED.is_scam
            """, tuple(chat_data.values()))
            self.dbconn.commit()
            logger.debug(f"Чат {chat_info['id']} обновлен")
        except Exception as e:
            logger.error(f"Ошибка обновления чата {chat_info['id']}: {e}")
            self.dbconn.rollback()
        finally:
            cursor.close()

    def process_group_members(self, chat_id: int, members):
        """Обрабатывает список участников группы"""
        logger.debug(f"Обработка список участников группы {chat_id}")

        current_members = self.get_current_members(chat_id)

        for member in members:
            try:
                user_id = member.get('user_id') or member.get('member_id').get('user_id')
                if not user_id:
                    continue
                self.upsert_user(user_id)

                member_info = {
                    'chat_id': chat_id,
                    'user_id': user_id,
                    'joined_chat_date' : datetime.fromtimestamp(member.get('joined_chat_date', 0)),
                    'role_id' : self.get_role_id(member.get('status', {}).get('@type'))
                }
                self.upsert_chat_membership(member_info)

                if user_id in current_members:
                    current_members.remove(user_id)

            except Exception as e:
                logger.error(f"Ошибка обработки участника: {str(e)}")

        self.mark_left_members(chat_id, current_members)

    def upsert_user(self, user_id: int):
        """Обновляет или создает запись о пользователе"""
        try:
            user_result = self.tg.call_method('getUser', {'user_id': user_id})
            user_result.wait()
            if not user_result:
                logger.error(f"Не удалось получить данные пользователя {user_id}")
                return

            user_info = user_result.update

            if not isinstance(user_info, dict):
                logger.error(f"Некорректный формат данных пользователя {user_id}: {user_info}")
                return

            user_data = {
                'user_id': user_info.get('id'),
                'first_name': user_info.get('first_name'),
                'last_name': user_info.get('last_name'),
                'username': user_info.get('usernames', {}).get('active_usernames', [None])[0],
                'phone_number': user_info.get('phone_number'),
                'last_online': self.get_last_online(user_info.get('status', {}))
            }
            self.save_user(user_data)

        except Exception as e:
            logger.error(f"Ошибка при обновлении пользователя: {str(e)}")

    def save_user(self, user: Dict[str, Any]) -> None:
        """Сохраняет информацию о пользователе."""
        cursor = None
        try:
            cursor = self.dbconn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, first_name, last_name, username, phone_number, is_bot, last_online)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    username = EXCLUDED.username,
                    phone_number = EXCLUDED.phone_number,
                    last_online = EXCLUDED.last_online
            """, (
                user['user_id'],
                user['first_name'],
                user['last_name'],
                user['username'],
                user['phone_number'],
                False,
                user['last_online']
            ))

            self.dbconn.commit()
            logger.debug(f"Пользователь {user['user_id']} сохранен")
        except Exception as e:
            logger.error(f"Ошибка сохранения пользователя {user['user_id']}: {str(e)}")
            self.dbconn.rollback()
        finally:
            if cursor:
                cursor.close()


    def upsert_chat_membership(self, member: Dict[str, Any]):
        """Обновляет или создает запись об участии в чате"""
        cursor = self.dbconn.cursor()
        try:
            cursor.execute("""
                INSERT INTO chat_members (
                    chat_id, user_id, join_date, left_date, role_id
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (chat_id, user_id) DO UPDATE SET
                    join_date = GREATEST(chat_members.join_date, EXCLUDED.join_date),
                    left_date = NULL,
                    role_id = EXCLUDED.role_id
                WHERE chat_members.left_date IS NOT NULL
            """, (
                member['chat_id'],
                member['user_id'],
                member['joined_chat_date'],
                None,
                member['role_id']
            ))
            self.dbconn.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления участника {member['user_id']}: {e}")
            self.dbconn.rollback()
        finally:
            cursor.close()

    def mark_left_members(self, chat_id: int, left_members: list):
        """Помечает участников как покинувших чат"""
        if not left_members:
            return

        cursor = self.dbconn.cursor()
        try:
            cursor.execute("""
                UPDATE chat_members
                SET left_date = NOW(),
                    role_id = %s
                WHERE chat_id = %s 
                AND user_id = ANY(%s)
                AND left_date IS NULL
            """, (
                self.get_role_id('chatMemberStatusLeft'),
                chat_id,
                left_members
            ))
            self.dbconn.commit()
            logger.info(f"Помечено как покинувших: {len(left_members)} участников")
        except Exception as e:
            logger.error(f"Ошибка пометки покинувших участников: {e}")
            self.dbconn.rollback()
        finally:
            cursor.close()

    def get_current_members(self, chat_id: int) -> list:
        """Возвращает список текущих участников чата из БД"""
        cursor = self.dbconn.cursor()
        try:
            cursor.execute("""
                SELECT user_id FROM chat_members
                WHERE chat_id = %s AND left_date IS NULL
            """, (chat_id,))
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()


    @staticmethod
    def get_last_online(status: dict) -> datetime:
        """Преобразует статус в дату последнего онлайна"""
        if status.get('@type') == 'userStatusOnline':
            return datetime.now()
        elif status.get('@type') == 'userStatusOffline':
            return datetime.fromtimestamp(status.get('was_online', 0))
        return None


    def get_chat_type_id(self, tdlib_type: str) -> int:
        """Получает ID типа чата"""
        cursor = self.dbconn.cursor()
        try:
            type_name_mapping = {
                'chatTypePrivate': 'private',
                'chatTypeBasicGroup': 'group',
                'chatTypeSupergroup': 'supergroup',
                'chatTypeChannel': 'channel'
            }
            db_type_name = type_name_mapping.get(tdlib_type, 'private')

            cursor.execute(
                "SELECT type_id FROM chat_types WHERE type_name = %s LIMIT 1",
                (db_type_name,)
            )
            result = cursor.fetchone()
            return result[0] if result else 1
        except Exception as e:
            logger.error(f"Ошибка получения type_id для {tdlib_type}: {e}")
            return 1
        finally:
            cursor.close()

    def get_role_id(self, tdlib_status: str) -> int:
        """Получает ID роли"""
        cursor = self.dbconn.cursor()
        try:
            role_name_mapping = {
                'chatMemberStatusCreator': 'creator',
                'chatMemberStatusAdministrator': 'administrator',
                'chatMemberStatusMember': 'member',
                'chatMemberStatusRestricted': 'restricted',
                'chatMemberStatusLeft': 'left',
                'chatMemberStatusBanned': 'banned'
            }
            db_role_name = role_name_mapping.get(tdlib_status, 'member')

            cursor.execute(
                "SELECT role_id FROM chat_roles WHERE role_name = %s LIMIT 1",
                (db_role_name,)
            )
            result = cursor.fetchone()
            return result[0] if result else 3
        except Exception as e:
            logger.error(f"Ошибка получения role_id для {tdlib_status}: {e}")
            return 3
        finally:
            cursor.close()