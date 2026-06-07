from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import redis
import json
import os
import threading
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SmartInbox Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

redis_client = redis.from_url(REDIS_URL)


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


def get_user_telegram_id(user_id: int):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT telegram_chat_id FROM user_email_config WHERE user_id = %s",
            (user_id,)
        )
        config = cur.fetchone()
        cur.close()
        conn.close()
        return config["telegram_chat_id"] if config else None
    except Exception as e:
        print(f"[notification] DB error: {e}")
        return None


def send_telegram(chat_id: str, message: str):
    if not TELEGRAM_BOT_TOKEN:
        print("[notification] No Telegram bot token set")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)
        return response.ok
    except Exception as e:
        print(f"[notification] Telegram error: {e}")
        return False


def format_message(em: dict, classification: dict) -> str:
    category = classification.get("category", "unknown").upper()
    subject = em.get("subject", "No subject")
    sender = em.get("from", "Unknown")
    summary = classification.get("summary", "")

    icons = {
        "JOB": "💼",
        "IMMIGRATION": "🛂",
        "UNIVERSITY": "🎓",
        "FINANCE": "💰",
        "PERSONAL": "👤",
    }
    icon = icons.get(category, "📧")

    return (
        f"{icon} *SmartInbox Alert*\n\n"
        f"*Category:* {category}\n"
        f"*From:* {sender}\n"
        f"*Subject:* {subject}\n\n"
        f"*Summary:* {summary}"
    )


def process_notification_queue():
    print("[notification] Queue worker started...")
    while True:
        try:
            item = redis_client.blpop("notification_queue", timeout=5)
            if item:
                _, data = item
                payload = json.loads(data)
                user_id = payload["user_id"]
                em = payload["email"]
                classification = payload["classification"]

                chat_id = get_user_telegram_id(user_id)
                if not chat_id:
                    print(f"[notification] No Telegram ID for user {user_id}")
                    continue

                message = format_message(em, classification)
                sent = send_telegram(chat_id, message)
                print(f"[notification] Alert for '{em.get('subject')}' → {'sent' if sent else 'failed'}")

        except Exception as e:
            print(f"[notification] Queue error: {e}")


@app.on_event("startup")
def startup():
    thread = threading.Thread(target=process_notification_queue, daemon=True)
    thread.start()
    print("[notification] Background worker started")


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}


class SendRequest(BaseModel):
    user_id: int
    message: str


@app.post("/send")
def send_manual(req: SendRequest):
    chat_id = get_user_telegram_id(req.user_id)
    if not chat_id:
        return {"status": "error", "detail": "No Telegram ID configured for this user"}
    sent = send_telegram(chat_id, req.message)
    return {"status": "sent" if sent else "failed"}


@app.get("/queue/size")
def queue_size():
    return {"notification_queue": redis_client.llen("notification_queue")}