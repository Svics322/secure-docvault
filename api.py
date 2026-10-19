import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from utils.validators.password_validator import PasswordValidator
from utils.validators.user_validator import UserValidator
from utils.hash.password_hasher import PasswordHandler
from utils.db.db_handler import DatabaseHandler

load_dotenv()

API_PORT = int(os.getenv("API_PORT", 8000))

@asynccontextmanager
async def lifespan(app: FastAPI):
    DatabaseHandler.init_db()
    yield

app = FastAPI(title="Secure DocVault API", lifespan=lifespan)

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserRegister):
    is_user_valid, user_errors = UserValidator.validate_username(user.username)
    is_email_valid, email_errors = UserValidator.validate_email(user.email)
    is_pass_valid, pass_errors = PasswordValidator.validate_password_complexity(user.password)

    all_errors = user_errors + email_errors + pass_errors
    if all_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Помилки валідації даних", "errors": all_errors}
        )

    hashed_password = PasswordHandler.hash_password(user.password)

    success = DatabaseHandler.register_user(user.username, user.email, hashed_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Користувач з таким ім'ям або email уже існує."
        )

    return {"message": "Користувач успішно зареєстрований", "username": user.username}

@app.post("/login")
def login_user(user: UserLogin):
    is_login_valid, login_errors = UserValidator.validate_login_input(user.username)
    if not is_login_valid or not user.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Помилки валідації", "errors": login_errors + (["Пароль не може бути порожнім"] if not user.password else [])}
        )

    db_user = DatabaseHandler.get_user_by_username(user.username)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірне ім'я користувача або пароль."
        )

    is_correct = PasswordHandler.verify_password(user.password, db_user['password_hash'])
    if not is_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірне ім'я користувача або пароль."
        )

    return {"message": f"Вітаємо, {user.username}! Успішний вхід."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=API_PORT, reload=True)