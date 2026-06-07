from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SmartInbox Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("JWT_SECRET", "changethisinproduction")
JWT_EXPIRY_HOURS = 24
security = HTTPBearer()

DB_URL = os.getenv("DATABASE_URL")


def get_db():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_email_config (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            gmail_address VARCHAR(255),
            gmail_app_password VARCHAR(255),
            telegram_chat_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.close()
    conn.close()
    print("Database initialized")


# Models
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class EmailConfigRequest(BaseModel):
    gmail_address: str
    gmail_app_password: str
    telegram_chat_id: str


# Helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: int, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Routes
@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-service"}


@app.post("/register")
def register(req: RegisterRequest):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id FROM users WHERE email = %s", (req.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = hash_password(req.password)
        cur.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (%s, %s, %s) RETURNING id",
            (req.email, hashed, req.full_name)
        )
        user_id = cur.fetchone()["id"]
        token = create_token(user_id, req.email)
        return {"token": token, "user_id": user_id, "email": req.email}
    finally:
        cur.close()
        conn.close()


@app.post("/login")
def login(req: LoginRequest):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM users WHERE email = %s", (req.email,))
        user = cur.fetchone()

        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_token(user["id"], user["email"])
        return {"token": token, "user_id": user["id"], "email": user["email"], "full_name": user["full_name"]}
    finally:
        cur.close()
        conn.close()


@app.get("/me")
def get_me(user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id, email, full_name, created_at FROM users WHERE id = %s", (user["user_id"],))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


@app.post("/config/email")
def save_email_config(req: EmailConfigRequest, user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM user_email_config WHERE user_id = %s", (user["user_id"],))
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE user_email_config
                SET gmail_address=%s, gmail_app_password=%s, telegram_chat_id=%s
                WHERE user_id=%s
            """, (req.gmail_address, req.gmail_app_password, req.telegram_chat_id, user["user_id"]))
        else:
            cur.execute("""
                INSERT INTO user_email_config (user_id, gmail_address, gmail_app_password, telegram_chat_id)
                VALUES (%s, %s, %s, %s)
            """, (user["user_id"], req.gmail_address, req.gmail_app_password, req.telegram_chat_id))
        return {"status": "saved"}
    finally:
        cur.close()
        conn.close()


@app.get("/config/email")
def get_email_config(user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT gmail_address, telegram_chat_id FROM user_email_config WHERE user_id = %s",
            (user["user_id"],)
        )
        config = cur.fetchone()
        if not config:
            raise HTTPException(status_code=404, detail="No config found")
        return config
    finally:
        cur.close()
        conn.close()