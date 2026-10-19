import bcrypt

class PasswordHandler:

    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_bytes.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'),
                                   hashed_password.encode('utf-8'))
        except ValueError:
            return False