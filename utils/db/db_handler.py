import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "docvault.db"

class DatabaseHandler:
    @staticmethod
    def get_db_connection():
        try:            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError as e:
            print(f"Помилка підключення до бази даних (docvault.db): {e}")
            raise RuntimeError(f"Не вдалося підключитися до бази даних. Перевірте права та шлях.") from e
        except Exception as e:
            print(f"Непередбачувана помилка бази даних: {e}")
            raise

    @staticmethod
    def init_db():
        try:
            with closing(DatabaseHandler.get_db_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active INTEGER DEFAULT 1
                        );
                ''')
                conn.commit()
        except (sqlite3.Error, RuntimeError) as e:
            print(f"Ініціалізація БД не вдалася: {e}")

    @staticmethod
    def register_user(username, email, password_hash):
        try:
            with closing(DatabaseHandler.get_db_connection()) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?);",
                    (username, email, password_hash)
                    )
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    print(f"Користувач з такими даними уже існує")
                    return False
        except (sqlite3.Error, RuntimeError) as e:
            print(f"Реєстрація нового користувача не вдалась: {e}")
            return False

    @staticmethod
    def get_user_by_username(username):
        try:
            with closing(DatabaseHandler.get_db_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
                return user
        except (sqlite3.Error, RuntimeError) as e:
            print(f"Помилка при отриманні користувача ({username}) : {e}")
            return None