from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import redis
import json
import re
import os
import threading
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SmartInbox AI Classifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")

redis_client = redis.from_url(REDIS_URL)

RULES = {
    "immigration": ["visa", "aima", "embassy", "residence", "permit", "immigration", "passport", "consulate", "sef", "autoriza"],
    "job": ["interview", "cv", "hiring", "job offer", "recruiter", "recruitment", "candidatura", "entrevista", "vaga", "emprego", "oferta"],
    "university": ["exam", "assignment", "course", "grade", "lecture", "professor", "exame", "nota", "aula", "universidade", "faculdade"],
    "finance": ["invoice", "payment", "bill", "bank", "transaction", "fatura", "pagamento", "conta", "saldo", "mbway", "iban"],
    "spam": ["unsubscribe", "click here", "limited offer", "winner", "congratulations", "discount", "promo", "newsletter", "marketing"],
}
IMPORTANT_CATEGORIES = {"immigration", "job", "university", "finance"}


class ClassifyRequest(BaseModel):
    user_id: int
    email: dict


def classify_with_ai(text: str):
    prompt = f"""You are an email classifier. Return ONLY valid JSON, nothing else.
Categories: immigration, job, university, finance, spam, personal
Important = true only for: immigration, job, university, finance

Return exactly:
{{"category": "", "important": true, "summary": "", "whatsapp_message": ""}}

Email:
{text[:500]}
"""
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}},
        timeout=30
    )
    result = response.json()["response"]
    match = re.search(r'\{.*\}', result, re.DOTALL)
    if match:
        return json.loads(match.group())
    return None


def classify_with_keywords(text: str):
    text_lower = (text or "").lower()
    scores = {cat: 0 for cat in RULES}
    for category, keywords in RULES.items():
        for kw in keywords:
            if kw in text_lower:
                scores[category] += 1
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = "personal"
    important = best in IMPORTANT_CATEGORIES
    snippet = text.strip()[:200].replace("\n", " ")
    labels = {"job": "Job opportunity", "immigration": "Immigration update", "university": "University notice", "finance": "Financial alert"}
    whatsapp_message = f"{labels.get(best, best)}: {snippet[:120]}" if important else ""
    return {"category": best, "important": important, "summary": snippet, "whatsapp_message": whatsapp_message}


def classify_email(text: str):
    try:
        result = classify_with_ai(text)
        if result:
            print("[classifier] Used AI (tinyllama)")
            return result
    except requests.exceptions.ConnectionError:
        print("[classifier] Ollama not running — using keywords")
    except requests.exceptions.ReadTimeout:
        print("[classifier] AI timed out — using keywords")
    except Exception as e:
        print(f"[classifier] AI error ({e}) — using keywords")
    result = classify_with_keywords(text)
    print(f"[classifier] Used keywords → {result['category']}")
    return result


def process_queue():
    print("[classifier] Queue worker started, waiting for emails...")
    while True:
        try:
            item = redis_client.blpop("email_queue", timeout=5)
            if item:
                _, data = item
                payload = json.loads(data)
                user_id = payload["user_id"]
                em = payload["email"]

                text = f"{em.get('subject', '')} {em.get('body', '')}"
                result = classify_email(text)

                # Push result to action queue
                action_payload = {
                    "user_id": user_id,
                    "email": em,
                    "classification": result
                }
                redis_client.rpush("action_queue", json.dumps(action_payload))
                print(f"[classifier] Email '{em.get('subject', '')}' → {result['category']}")
        except Exception as e:
            print(f"[classifier] Queue error: {e}")


@app.on_event("startup")
def startup():
    thread = threading.Thread(target=process_queue, daemon=True)
    thread.start()
    print("[classifier] Background worker started")


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-classifier"}


@app.post("/classify")
def classify_single(req: ClassifyRequest):
    text = f"{req.email.get('subject', '')} {req.email.get('body', '')}"
    result = classify_email(text)
    return {"user_id": req.user_id, "email_id": req.email.get("id"), "classification": result}


@app.get("/queue/size")
def queue_size():
    return {
        "email_queue": redis_client.llen("email_queue"),
        "action_queue": redis_client.llen("action_queue")
    }