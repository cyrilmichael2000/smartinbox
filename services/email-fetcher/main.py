from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import imaplib
import email
from email.header import decode_header
import os
import redis
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SmartInbox Email Fetcher")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = redis.from_url(REDIS_URL)


class FetchRequest(BaseModel):
    user_id: int
    gmail_address: str
    gmail_app_password: str


def decode_str(value):
    if value is None:
        return ""
    decoded, encoding = decode_header(value)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(encoding or "utf-8", errors="ignore")
    return str(decoded)


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="ignore")
    return ""


def fetch_unread_emails(gmail_address: str, app_password: str):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(gmail_address, app_password)
    mail.select("inbox")

    status, messages = mail.search(None, "UNSEEN")
    email_ids = messages[0].split()

    emails = []
    for eid in email_ids[-20:]:  # max 20 unread
        status, msg_data = mail.fetch(eid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        emails.append({
            "id": eid.decode(),
            "subject": decode_str(msg.get("Subject", "No subject")),
            "from": decode_str(msg.get("From", "Unknown")),
            "date": decode_str(msg.get("Date", "")),
            "body": get_body(msg)[:2000]
        })

    mail.logout()
    return emails


@app.get("/health")
def health():
    return {"status": "ok", "service": "email-fetcher"}


@app.post("/fetch")
def fetch_emails(req: FetchRequest):
    try:
        emails = fetch_unread_emails(req.gmail_address, req.gmail_app_password)

        # Push each email to Redis queue for ai-classifier to consume
        for em in emails:
            payload = {"user_id": req.user_id, "email": em}
            redis_client.rpush("email_queue", json.dumps(payload))

        print(f"Fetched {len(emails)} emails for user {req.user_id}, pushed to queue")
        return {"fetched": len(emails), "emails": emails}

    except imaplib.IMAP4.error as e:
        raise HTTPException(status_code=401, detail=f"Gmail auth failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/queue/size")
def queue_size():
    size = redis_client.llen("email_queue")
    return {"queue_size": size}