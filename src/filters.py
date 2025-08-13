from config import Config

def is_relevant(message: dict) -> bool:
    if not message or not isinstance(message, dict):
        return False

    text = ""
    if message.get('content').get('text'):
        text = str(message.get('content', {}).get('text', {}).get('text', ''))
    elif message.get('content').get('caption'):
        text = str(message.get('content').get('caption', {}).get('text', ''))
    chat_id = message.get('chat_id')
    sender = message.get('sender_id')

    if Config.ALLOWED_CHATS and chat_id not in Config.ALLOWED_CHATS:
        return False
    if isinstance(sender, dict) and sender.get('user_id') in Config.BLOCKED_USERS:
        return False
    elif isinstance(sender, (int, str)) and sender in Config.BLOCKED_USERS:
        return False

    has_keywords = any(keyword in text.lower() for keyword in Config.KEYWORDS)
    has_flags = any(flag in text.lower() for flag in Config.FLAG_WORDS)

    return has_keywords or has_flags