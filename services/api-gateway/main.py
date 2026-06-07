from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import jwt
import os
import json
import redis
import asyncio
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SmartInbox API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("JWT_SECRET", "changethisinproduction")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

SERVICES = {
    "auth":         os.getenv("AUTH_SERVICE_URL",         "http://auth-service:8001"),
    "email-fetcher": os.getenv("EMAIL_FETCHER_URL",       "http://email-fetcher:8002"),
    "ai-classifier": os.getenv("AI_CLASSIFIER_URL",       "http://ai-classifier:8003"),
    "action-engine": os.getenv("ACTION_ENGINE_URL",       "http://action-engine:8004"),
    "notification":  os.getenv("NOTIFICATION_SERVICE_URL","http://notification-service:8005"),
    "scheduler":     os.getenv("SCHEDULER_URL",           "http://scheduler:8006"),
}

redis_client = redis.from_url(REDIS_URL)
security = HTTPBearer()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except:
                    pass

manager = ConnectionManager()


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return decode_token(credentials.credentials)


# Health
@app.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway"}


@app.get("/health/all")
async def health_all():
    results = {}
    async with httpx.AsyncClient() as client:
        for name, url in SERVICES.items():
            try:
                r = await client.get(f"{url}/health", timeout=3)
                results[name] = "ok" if r.status_code == 200 else "error"
            except:
                results[name] = "unreachable"
    return results


# Auth routes
@app.post("/api/auth/register")
async def register(body: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{SERVICES['auth']}/register", json=body)
        return r.json()


@app.post("/api/auth/login")
async def login(body: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{SERVICES['auth']}/login", json=body)
        return r.json()


@app.get("/api/auth/me")
async def me(user=Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{SERVICES['auth']}/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"}
        )
        return r.json()


@app.post("/api/auth/config/email")
async def save_email_config(body: dict, user=Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SERVICES['auth']}/config/email",
            json=body,
            headers={"Authorization": f"Bearer {credentials.credentials}"}
        )
        return r.json()


# Email routes
@app.post("/api/emails/fetch")
async def fetch_emails(user=Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    async with httpx.AsyncClient() as client:
        config_r = await client.get(
            f"{SERVICES['auth']}/config/email",
            headers={"Authorization": f"Bearer {credentials.credentials}"}
        )
        if config_r.status_code != 200:
            raise HTTPException(status_code=400, detail="Email config not found. Please configure your Gmail first.")
        config = config_r.json()

        r = await client.post(
            f"{SERVICES['email-fetcher']}/fetch",
            json={
                "user_id": user["user_id"],
                "gmail_address": config["gmail_address"],
                "gmail_app_password": config.get("gmail_app_password", "")
            },
            timeout=30
        )

        result = r.json()

        # Notify connected WebSocket clients
        await manager.send_to_user(user["user_id"], {
            "event": "emails_fetched",
            "count": result.get("fetched", 0)
        })

        return result


@app.get("/api/emails/logs")
async def get_logs(user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SERVICES['action-engine']}/logs/{user['user_id']}")
        return r.json()


@app.get("/api/emails/stats")
async def get_stats(user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SERVICES['action-engine']}/stats/{user['user_id']}")
        return r.json()


# Scheduler routes
@app.get("/api/scheduler/jobs")
async def get_jobs(user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SERVICES['scheduler']}/jobs")
        return r.json()


@app.post("/api/scheduler/run-now")
async def run_now(user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{SERVICES['scheduler']}/run-now")
        return r.json()


# Queue stats
@app.get("/api/queues")
async def queue_stats(user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SERVICES['ai-classifier']}/queue/size")
        return r.json()


# WebSocket for real-time updates
@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        user = decode_token(token)
        user_id = user["user_id"]
    except:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # Send live queue stats every 5 seconds
            try:
                email_q = redis_client.llen("email_queue")
                action_q = redis_client.llen("action_queue")
                notif_q = redis_client.llen("notification_queue")
                await websocket.send_json({
                    "event": "queue_update",
                    "email_queue": email_q,
                    "action_queue": action_q,
                    "notification_queue": notif_q
                })
            except:
                pass
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        print(f"[gateway] User {user_id} disconnected")