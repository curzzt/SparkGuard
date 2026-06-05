import re

MAX_LENGTH = 100
FORBIDDEN_WORDS = ["广告", "外链", "敏感词"]
URL_PATTERN = re.compile(r"https?://|www\.", re.I)
PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
WECHAT_PATTERN = re.compile(r"微信|vx|weixin", re.I)


def is_compliant(message: str) -> tuple[bool, str | None]:
    if not message or not message.strip():
        return False, "消息内容为空"
    if len(message) > MAX_LENGTH:
        return False, "消息内容超过长度上限"
    for word in FORBIDDEN_WORDS:
        if word in message:
            return False, f"消息包含禁止内容: {word}"
    if URL_PATTERN.search(message):
        return False, "消息包含外链"
    if PHONE_PATTERN.search(message):
        return False, "消息包含手机号"
    if WECHAT_PATTERN.search(message):
        return False, "消息包含微信号相关内容"
    return True, None
