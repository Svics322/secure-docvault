import re
from typing import List, Tuple


class PasswordValidator:

    @staticmethod
    def validate_password_complexity(password: str) -> Tuple[bool, List[str]]:
        errors = []

        if not password:
            errors.append("Пароль є обов'язковим")
            return False, errors

        if len(password) < 8:
            errors.append("Пароль має містити щонайменше 8 символів")
        if len(password.encode("utf-8")) > 72:
            errors.append("Пароль не повинен перевищувати 72 байти")
        if not re.search(r"[A-Z]", password):
            errors.append("Пароль має містити щонайменше одну велику літеру")
        if not re.search(r"[a-z]", password):
            errors.append("Пароль має містити щонайменше одну малу літеру")
        if not re.search(r"[0-9]", password):
            errors.append("Пароль має містити щонайменше одну цифру")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Пароль має містити щонайменше один спеціальний символ")

        is_valid = len(errors) == 0
        return (is_valid, errors)
