from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import requests
import psycopg2
import psycopg2.extras
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SmartInbox Scheduler")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
EMAIL_FETCHER_URL = os.getenv("EMAIL_FETCHER_URL", "http://email-fetcher:8002")
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "5"))

scheduler = BackgroundScheduler()


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


def get_all_users():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT u.id as user_id, c.gmail_address, c.gmail_app_password
            FROM users u
            JOIN user_email_config c ON u.id = c.user_id
            WHERE u.is_active = TRUE
              AND c.gmail_address IS NOT NULL
              AND c.gmail_app_password IS NOT NULL
        """)
        users = cur.fetchall()
        cur.close()
        conn.close()
        return users
    except Exception as e:
        print(f"[scheduler] DB error: {e}")
        return []


def fetch_emails_for_all_users():
    print("[scheduler] Running scheduled email fetch...")
    users = get_all_users()

    if not users:
        print("[scheduler] No users configured yet")
        return

    for user in users:
        try:
            response = requests.post(
                f"{EMAIL_FETCHER_URL}/fetch",
                json={
                    "user_id": user["user_id"],
                    "gmail_address": user["gmail_address"],
                    "gmail_app_password": user["gmail_app_password"]
                },
                timeout=30
            )
            if response.ok:
                data = response.json()
                print(f"[scheduler] User {user['user_id']} → fetched {data.get('fetched', 0)} emails")
            else:
                print(f"[scheduler] User {user['user_id']} → fetch failed: {response.text}")
        except Exception as e:
            print(f"[scheduler] User {user['user_id']} → error: {e}")


@app.on_event("startup")
def startup():
    scheduler.add_job(
        fetch_emails_for_all_users,
        trigger=IntervalTrigger(minutes=FETCH_INTERVAL_MINUTES),
        id="fetch_emails",
        replace_existing=True
    )
    scheduler.start()
    print(f"[scheduler] Started — fetching every {FETCH_INTERVAL_MINUTES} minutes")


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()


@app.get("/health")
def health():
    return {"status": "ok", "service": "scheduler"}


@app.get("/jobs")
def get_jobs():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time),
            "trigger": str(job.trigger)
        })
    return {"jobs": jobs}


@app.post("/run-now")
def run_now():
    fetch_emails_for_all_users()
    return {"status": "triggered"}