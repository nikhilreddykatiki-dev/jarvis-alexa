# PROJECT JARVIS — ZERO COST EDITION

JARVIS is a completely free, personal voice-enabled AI assistant running on your **Amazon Echo Dot (5th Gen)**, powered by **Groq Cloud API** and a local/cloud **Python FastAPI** backend.

---

## 🌟 Key Architecture & Philosophy
1. **Zero-Cost Constraint**: Strictly uses free-tier services. No paid OpenAI API, no paid databases, no paid voice APIs.
2. **Groq Llama 3 / OSS AI Brain**: Lightning-fast inference (sub-500ms) suitable for real-time voice conversations.
3. **Local SQLite Memory**: Stores user preferences, conversations, and reminders locally with strict privacy.
4. **Alexa Skill Kit (ASK) Compliance**: Uses standard voice intents, SSML formatting, and security request verification.

---

## 📁 Repository Structure
```
jarvis/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI server entry point
│   │   ├── config.py            # Pydantic settings & env validation
│   │   ├── database.py          # SQLite engine & session management
│   │   ├── models.py            # SQLAlchemy database schemas
│   │   ├── agents/
│   │   │   ├── jarvis_agent.py  # Conversational orchestration & reasoning
│   │   │   ├── prompts.py       # Custom personality & Alexa-specific prompts
│   │   │   └── tools.py         # Explicitly allowlisted tool calling
│   │   ├── providers/
│   │   │   └── groq_provider.py # Groq API wrapper with rate-limit protection
│   │   ├── memory/
│   │   │   └── manager.py       # CRUD operations for long-term memory
│   │   ├── reminders/
│   │   │   └── manager.py       # Local scheduler and reminder state
│   │   ├── integrations/
│   │   │   └── alexa/
│   │   │       ├── handler.py   # Intent & launch request handler
│   │   │       ├── security.py  # SHA256 / X.509 cert request validation
│   │   │       └── intents.py   # SSML & JSON ASK response builder
│   │   ├── api/
│   │   │   └── routes.py        # REST endpoints & Alexa webhook
│   │   └── static/
│   │       └── index.html       # Web dashboard interface
│   └── tests/
│       ├── test_health.py       # Config, database, & model unit tests
│       └── test_agent.py        # Tool verification & prompt safety tests
├── docs/
│   ├── SETUP.md                 # Local setup & environment guide
│   ├── ALEXA_SETUP.md           # Alexa Developer Console step-by-step
│   ├── DEPLOYMENT.md            # Free hosting guide (Lambda / Render / Local)
│   └── TROUBLESHOOTING.md       # Common errors & solutions
├── scripts/
│   └── terminal_chat.py         # Interactive CLI terminal chat
├── .env.example
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start (Local Development)

### 1. Prerequisites
- Python 3.10+ installed.
- Free Groq API Key from [console.groq.com](https://console.groq.com/keys).

### 2. Setup Virtual Environment
```powershell
cd c:\Users\Nikhil\Desktop\NR\ALEXA\jarvis
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure `.env`
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Edit `.env` and paste your `GROQ_API_KEY`:
```ini
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct
```

### 4. Run the Terminal Assistant (Phase 2 Test)
```powershell
python -m scripts.terminal_chat
```

### 5. Launch Local Web Dashboard & Server
```powershell
uvicorn backend.app.main:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.
