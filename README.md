# SmartInbox

> AI-powered email operations platform for individuals and small businesses.

SmartInbox automatically reads your emails, classifies them using AI, deletes junk, and sends real-time alerts for important messages via Telegram. Built as a cloud-native microservices application orchestrated with Kubernetes.

---

## Architecture

SmartInbox is composed of 8 microservices communicating via REST and asynchronous Redis queues, with a React frontend and PostgreSQL database.

```
┌─────────────────────────────────────────────────────┐
│                     Frontend (React)                 │
│              Dashboard · Inbox · Settings            │
└────────────────────────┬────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼────────────────────────────┐
│                   API Gateway :8000                  │
│         Routes · Auth middleware · WebSocket         │
└──┬──────┬──────┬──────┬──────┬──────┬───────────────┘
   │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼
 Auth  Fetcher  AI   Action  Notif  Scheduler
 8001   8002   8003   8004   8005    8006
   │      │      │      │      │
   └──────┴──────┴──────┴──────┘
                 │
         Redis Queues
      email_queue → action_queue → notification_queue
                 │
          PostgreSQL (Supabase PaaS)
```

---

## Microservices

| Service | Port | Description |
|---|---|---|
| **api-gateway** | 8000 | Single entry point, routes all requests, WebSocket hub |
| **auth-service** | 8001 | User registration, login, JWT tokens, email config storage |
| **email-fetcher** | 8002 | Connects to Gmail via IMAP, fetches unread emails |
| **ai-classifier** | 8003 | Classifies emails using Ollama (tinyllama) with keyword fallback |
| **action-engine** | 8004 | Executes actions (auto-delete spam, log to DB, route to notifications) |
| **notification-service** | 8005 | Sends Telegram alerts for important emails |
| **scheduler** | 8006 | Runs scheduled email fetches every N minutes using APScheduler |
| **frontend** | 5173 | React dashboard with live WebSocket updates, charts, inbox view |

---

## Requirements Coverage

| Requirement | Implementation |
|---|---|
| Synchronous services | REST APIs — auth, email fetch, classify |
| Asynchronous services | Redis queues between classifier → action → notification |
| Real-time communication | WebSocket in api-gateway, live queue stats in navbar |
| Storage services | PostgreSQL (email logs, users), Redis (queues) |
| Scheduled routines | APScheduler in scheduler service, runs every 5 minutes |
| Kubernetes orchestration | K8s deployments, services, configmaps, ingress in `/k8s` |
| External API integration | Gmail IMAP, Telegram Bot API, Ollama AI |
| PaaS solution | Supabase (managed PostgreSQL) |

---

## Tech Stack

- **Backend** — Python, FastAPI, Uvicorn
- **Frontend** — React, Vite, Recharts, Lucide
- **AI** — Ollama with tinyllama model (local inference)
- **Database** — PostgreSQL via Supabase
- **Queue** — Redis
- **Containerization** — Docker, Docker Compose
- **Orchestration** — Kubernetes (Minikube locally, GKE for live)
- **Auth** — JWT tokens with bcrypt password hashing

---

## Local Development

### Prerequisites

- Docker Desktop
- Node.js 18+
- Ollama (optional, falls back to keyword classifier)

### 1. Clone the repository

```bash
git clone https://github.com/cyrilmichael2000/smartinbox.git
cd smartinbox
```

### 2. Start all backend services

```bash
docker-compose up --build -d
```

Services will be available at:
- API Gateway → http://localhost:8000
- API Docs → http://localhost:8000/docs
- Auth Service → http://localhost:8001/docs
- Email Fetcher → http://localhost:8002/docs
- AI Classifier → http://localhost:8003/docs
- Action Engine → http://localhost:8004/docs
- Notification Service → http://localhost:8005/docs
- Scheduler → http://localhost:8006/docs

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at → http://localhost:5173

### 4. Configure your account

1. Open http://localhost:5173
2. Register an account
3. Go to **Settings**
4. Enter your Gmail address and Gmail App Password
   - Generate at: myaccount.google.com → Security → App Passwords
5. Enter your Telegram Chat ID
   - Get it by messaging @userinfobot on Telegram

### 5. Start the AI (optional)

```bash
ollama pull tinyllama
ollama serve
```

If Ollama is not running, the classifier automatically falls back to keyword-based classification.

---

## Environment Variables

Create a `.env` file in the root directory:

```env
DATABASE_URL=postgresql://smartinbox:smartinbox123@postgres:5432/smartinbox
JWT_SECRET=your_secret_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
OLLAMA_URL=http://host.docker.internal:11434/api/generate
```

---

## Email Classification Categories

| Category | Triggers | Action |
|---|---|---|
| **job** | interview, CV, hiring, recruitment | Alert via Telegram |
| **immigration** | visa, AIMA, embassy, residence permit | Alert via Telegram |
| **finance** | invoice, payment, bank, IBAN | Alert via Telegram |
| **university** | exam, assignment, course, grades | Alert via Telegram |
| **personal** | everything else important | Alert via Telegram |
| **spam** | newsletters, promotions, marketing | Auto-deleted |

---

## Project Structure

```
smartinbox/
├── frontend/                  React dashboard
│   └── src/
│       ├── pages/             Dashboard, Inbox, Settings, Login, Register
│       ├── components/        Sidebar, Navbar
│       └── context/           AuthContext
├── services/
│   ├── api-gateway/           Entry point, WebSocket
│   ├── auth-service/          Auth, JWT, user config
│   ├── email-fetcher/         Gmail IMAP integration
│   ├── ai-classifier/         Ollama + keyword fallback
│   ├── action-engine/         Rules execution, DB logging
│   ├── notification-service/  Telegram alerts
│   └── scheduler/             APScheduler cron jobs
├── k8s/                       Kubernetes manifests
│   ├── deployments/
│   ├── services/
│   ├── configmaps/
│   └── ingress/
├── docker-compose.yml
└── .env
```

---

## Kubernetes Deployment

```bash
# Apply all manifests
kubectl apply -f k8s/

# Check pods
kubectl get pods

# Get service URLs
kubectl get services
```

---

## Author

Cyril Michael — MSc Computer Engineering, Mobile Computing & Cloud Computing 2025/26
