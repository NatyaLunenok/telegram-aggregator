-- Пользователи Telegram
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    username VARCHAR(32) UNIQUE,
    phone_number VARCHAR(15) UNIQUE,
    is_bot BOOLEAN NOT NULL,
    last_online TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL  -- Время записи пользователя в БД
);

--Типы чатов
CREATE TABLE chat_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(25) UNIQUE NOT NULL
);

INSERT INTO chat_types (type_name)
VALUES ('private'),
	   ('group'),
	   ('channel'),
	   ('supergroup');

-- Чаты
CREATE TABLE chats (
    chat_id BIGINT PRIMARY KEY,  -- Уникальный ID чата в Telegram
    title VARCHAR(255),
    type_id INT REFERENCES chat_types(type_id) NOT NULL,
	description TEXT,
	chatname VARCHAR(32) UNIQUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,  -- Верифицирован ли чат
    is_scam BOOLEAN NOT NULL DEFAULT FALSE,  -- Помечен ли чат как мошеннический
    created_at TIMESTAMP WITH TIME ZONE  -- Время создания чата в Telegram
);

--Роли участников
CREATE TABLE chat_roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(25) UNIQUE NOT NULL
);

INSERT INTO chat_roles (role_name)
VALUES ('creator'),
	   ('administrator'),
	   ('member'),
	   ('restricted'),
	   ('left'),
	   ('banned');

-- Участники чатов
CREATE TABLE chat_members (
    chat_id BIGINT REFERENCES chats(chat_id) ON DELETE CASCADE NOT NULL,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    join_date TIMESTAMP WITH TIME ZONE NOT NULL,
    left_date TIMESTAMP WITH TIME ZONE,
	role_id INT REFERENCES chat_roles(role_id) NOT NULL,
	UNIQUE (chat_id, user_id)
);

ALTER TABLE chat_members
ADD CONSTRAINT check_dates_valid
CHECK (left_date IS NULL OR left_date >= join_date);

-- Сообщения
CREATE TABLE messages (
    message_id BIGSERIAL PRIMARY KEY,
	telegram_message_id BIGINT NOT NULL,  -- ID сообщения в рамках данного чата Telegram
    chat_id BIGINT REFERENCES chats(chat_id) NOT NULL,
    sender_id BIGINT REFERENCES users(user_id),
	message_date TIMESTAMP WITH TIME ZONE NOT NULL,
    edit_date TIMESTAMP WITH TIME ZONE,
    text TEXT,
	reply_to_message_id BIGINT REFERENCES messages(message_id),  -- Ссылка на сообщение, на которое был дан ответ
    forward_from_user_id BIGINT REFERENCES users(user_id),  -- ID пользователя, от которого было переслано сообщение
    forward_from_chat_id BIGINT REFERENCES chats(chat_id),  -- ID чата, из которого было переслано сообщение
    is_outgoing BOOLEAN NOT NULL DEFAULT FALSE,        -- Было ли сообщение отправлено нашим агрегирующим аккаунтом
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,  -- Время записи сообщения в БД

    UNIQUE (chat_id, telegram_message_id)
);

-- Типы вложений
CREATE TABLE attachment_types (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(25) UNIQUE NOT NULL
);

INSERT INTO attachment_types (type_name)
VALUES ('photo'),
	   ('video'),
	   ('document'),
	   ('audio'),
	   ('voice'),
	   ('sticker'),
	   ('gif'),
	   ('video_note');

-- Вложения
CREATE TABLE attachments (
    message_id BIGINT REFERENCES messages(message_id) ON DELETE CASCADE NOT NULL,
    type_id INT REFERENCES attachment_types(type_id) NOT NULL,
    file_id VARCHAR(255),  -- Уникальный ID файла в Telegram

	UNIQUE (message_id, file_id)
);

-- Реакции на сообщения
CREATE TABLE message_reactions (
    message_id BIGINT REFERENCES messages(message_id) ON DELETE CASCADE NOT NULL,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    emoji VARCHAR(10) NOT NULL,

	UNIQUE (message_id, user_id, emoji)
);

--Индексы
CREATE INDEX idx_chats_type_id ON chats (type_id);
CREATE INDEX idx_chat_members_user_id ON chat_members (user_id);
CREATE INDEX idx_messages_chat_id_message_date ON messages (chat_id, message_date);
CREATE INDEX idx_messages_sender_id ON messages (sender_id);
CREATE INDEX idx_attachments_type_id ON attachments (type_id);
CREATE INDEX idx_message_reactions_user_id ON message_reactions (user_id);
