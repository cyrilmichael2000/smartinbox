from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import json
import os
import imaplib
import threading
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SmartInbox Action Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
DATABASE_URL = os.getenv("DATABASE_URL")

redis_client = redis.from_url(REDIS_URL)


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            email_id VARCHAR(100),
            subject TEXT,
            sender TEXT,
            category VARCHAR(50),
            important BOOLEAN,
            summary TEXT,
            action_taken VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.close()
    conn.close()
    print("[action-engine] Database initialized")


def get_user_gmail_config(user_id: int):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT gmail_address, gmail_app_password FROM user_email_config WHERE user_id = %s",
        (user_id,)
    )
    config = cur.fetchone()
    cur.close()
    conn.close()
    return config


def move_to_trash(gmail_address: str, app_password: str, email_id: str):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_address, app_password)
        mail.select("inbox")
        mail.store(email_id, "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.logout()
        return True
    except Exception as e:
        print(f"[action-engine] Trash error: {e}")
        return False


def log_email(user_id, email_id, subject, sender, category, important, summary, action):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO email_logs (user_id, email_id, subject, sender, category, important, summary, action_taken)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, email_id, subject, sender, category, important, summary, action))
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[action-engine] Log error: {e}")


def process_action_queue():
    print("[action-engine] Queue worker started...")
    while True:
        try:
            item = redis_client.blpop("action_queue", timeout=5)
            if item:
                _, data = item
                payload = json.loads(data)
                user_id = payload["user_id"]
                em = payload["email"]
                classification = payload["classification"]

                category = classification.get("category", "unknown")
                important = classification.get("important", False)
                summary = classification.get("summary", "")

                action = "kept"

                # Auto delete spam
                if category == "spam":
                    config = get_user_gmail_config(user_id)
                    if config:
                        deleted = move_to_trash(
                            config["gmail_address"],
                            config["gmail_app_password"],
                            em["id"]
                        )
                        action = "deleted" if deleted else "delete_failed"

                # Log to database
                log_email(
                    user_id, em.get("id"), em.get("subject"),
                    em.get("from"), category, important, summary, action
                )

                # If important push to notification queue
                if important:
                    notif_payload = {
                        "user_id": user_id,
                        "email": em,
                        "classification": classification
                    }
                    redis_client.rpush("notification_queue", json.dumps(notif_payload))

                print(f"[action-engine] '{em.get('subject', '')}' → {category} → {action}")

        except Exception as e:
            print(f"[action-engine] Queue error: {e}")


@app.on_event("startup")
def startup():
    init_db()
    thread = threading.Thread(target=process_action_queue, daemon=True)
    thread.start()


@app.get("/health")
def health():
    return {"status": "ok", "service": "action-engine"}


@app.get("/logs/{user_id}")
def get_logs(user_id: int):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM email_logs WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
        (user_id,)
    )
    logs = cur.fetchall()
    cur.close()
    conn.close()
    return {"logs": logs}


@app.get("/stats/{user_id}")
def get_stats(user_id: int):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN important THEN 1 ELSE 0 END) as important,
            SUM(CASE WHEN action_taken = 'deleted' THEN 1 ELSE 0 END) as deleted,
            category,
            COUNT(*) as count
        FROM email_logs
        WHERE user_id = %s
        GROUP BY category
    """, (user_id,))
    stats = cur.fetchall()
    cur.close()
    conn.close()
    return {"stats": stats}