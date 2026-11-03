import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from utils.validators.password_validator import PasswordValidator
from utils.validators.user_validator import UserValidator
from utils.hash.password_hasher import PasswordHandler
from utils.db.db_handler import DatabaseHandler
import jwt_service
from utils.sanitizer import sanitize_user_input
from middleware import SecurityMiddleware

load_dotenv()

API_PORT = int(os.getenv("API_PORT", 8000))
security = HTTPBearer(auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    DatabaseHandler.init_db()
    yield

app = FastAPI(
    title="Secure DocVault API",
    version="0.3.0",
    lifespan=lifespan
)

app.add_middleware(SecurityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class DocumentComment(BaseModel):
    title: str
    comment: str

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = None
    
    if request.cookies.get("access_token"):
        token = request.cookies.get("access_token")
    elif credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Відсутній або некоректний токен авторизації"
        )
    
    try:
        payload = jwt_service.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Надано некоректний тип токена (очікується Access token)"
            )
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@app.post("/register", status_code=status.HTTP_201_CREATED)
@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserRegister):
    clean_username = sanitize_user_input(user.username)
    is_user_valid, user_errors = UserValidator.validate_username(clean_username)
    is_email_valid, email_errors = UserValidator.validate_email(user.email)
    is_pass_valid, pass_errors = PasswordValidator.validate_password_complexity(user.password)

    all_errors = user_errors + email_errors + pass_errors
    if all_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Помилки валідації даних", "errors": all_errors}
        )

    hashed_password = PasswordHandler.hash_password(user.password)
    success = DatabaseHandler.register_user(clean_username, user.email, hashed_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Користувач з таким ім'ям або email уже існує."
        )

    return {"message": "Користувач успішно зареєстрований", "username": clean_username}

@app.post("/login")
@app.post("/api/v1/auth/login")
def login_user(user: UserLogin, response: Response):
    clean_username = sanitize_user_input(user.username)
    is_login_valid, login_errors = UserValidator.validate_login_input(clean_username)
    if not is_login_valid or not user.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Помилки валідації", "errors": login_errors + (["Пароль не може бути порожнім"] if not user.password else [])}
        )

    db_user = DatabaseHandler.get_user_by_username(clean_username)
    if not db_user or not PasswordHandler.verify_password(user.password, db_user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірне ім'я користувача або пароль."
        )

    user_dict = dict(db_user)
    user_id = user_dict.get('id', 1)
    role = user_dict.get('role', 'user')

    access_token = jwt_service.create_access_token(user_id, clean_username, role)
    refresh_token = jwt_service.create_refresh_token(user_id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=900
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/api/v1/auth/refresh")
def refresh_token(req: RefreshRequest):
    token = req.refresh_token
    
    if jwt_service.is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Спроба повторного використання токена (Replay Attack)! Токен анульовано."
        )
    
    try:
        payload = jwt_service.decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Надано некоректний тип токена (очікується Refresh token)"
            )
        
        user_id = int(payload["sub"])
        jwt_service.revoke_refresh_token(token)
        
        new_access = jwt_service.create_access_token(user_id, "testuser", "user")
        new_refresh = jwt_service.create_refresh_token(user_id)
        
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@app.get("/api/v1/user/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "message": "Доступ надано!",
        "user_data": {
            "user_id": current_user.get("sub"),
            "username": current_user.get("username"),
            "role": current_user.get("role")
        }
    }

@app.post("/api/v1/documents/comment")
def add_document_comment(
    doc: DocumentComment,
    current_user: dict = Depends(get_current_user)
):
    clean_title = sanitize_user_input(doc.title)
    clean_comment = sanitize_user_input(doc.comment)
    
    return {
        "status": "success",
        "original_comment": doc.comment,
        "sanitized_comment": clean_comment,
        "sanitized_title": clean_title
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=API_PORT, reload=True)