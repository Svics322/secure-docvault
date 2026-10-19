import re
from typing import List, Tuple

class PasswordValidator:

    @staticmethod
    def validate_password_complexity(password: str) -> Tuple[bool, List[str]]:
        errors = []

        if len(password) < 8:
            errors.append("Мінімальна довжина паролю 8 символів")
        if len(password.encode("utf-8")) > 72:
            errors.append("Максимальна довжина паролю 72 байти")
        if not re.search(r"[A-Z]", password):
            errors.append("Пароль має містити одну велику літеру")
        if not re.search(r"[a-z]", password):
            errors.append("Пароль має містити одну маленьку літеру")
        if not re.search(r"[0-9]", password):
            errors.append("Пароль має містити одну цифру")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Пароль має містити один спеціальний символ")

        is_valid = len(errors) == 0
        return (is_valid, errors)