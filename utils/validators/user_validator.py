import re
from typing import List, Tuple

class UserValidator:

    @staticmethod
    def validate_username(username: str) -> Tuple[bool, List[str]]:
        errors = []
        if not username or not username.strip():
            errors.append("Поле не може бути порожнім")
            return False, errors
            
        username_clean = username.strip()
        if len(username_clean) < 3:
            errors.append("Ім'я користувача має містити мінімум 3 символи")
        if len(username_clean) > 30:
            errors.append("Ім'я користувача не повинно перевищувати 30 символів")
        if not re.match(r"^[a-zA-Z0-9_]+$", username_clean):
            errors.append("Ім'я користувача може містити лише латинські літери, цифри та нижнє підкреслення")
        return len(errors) == 0, errors

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, List[str]]:
        errors = []
        if not email or not email.strip():
            errors.append("Поле не може бути порожнім")
            return False, errors
            
        email_clean = email.strip()
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email_clean) or ".." in email_clean:
            errors.append("Невірний формат електронної пошти")
        return len(errors) == 0, errors

    @staticmethod
    def validate_login_input(username: str) -> Tuple[bool, List[str]]:
        errors = []
        if not username or not username.strip():
            errors.append("Поле не може бути порожнім")
        return len(errors) == 0, errors