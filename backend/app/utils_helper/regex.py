import re

class RegexClass :

    @staticmethod
    def is_strong_password(password: str) -> bool:
        _PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$')
        return bool(_PASSWORD_PATTERN.match(password))
