import re

PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def mask_open_id(open_id: str) -> str:
    if len(open_id) <= 4:
        return "***"
    return f"{open_id[0]}***{open_id[-2:]}"
