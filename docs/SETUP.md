# JARVIS Local Setup Guide (Windows)

## Step 1: Install Python Dependencies
Open PowerShell in the `jarvis` folder:
```powershell
cd c:\Users\Nikhil\Desktop\NR\ALEXA\jarvis
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Configure Environment
1. Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```
2. Open `.env` and fill in:
   - `GROQ_API_KEY`: Get your free key at [Groq Console](https://console.groq.com/keys).
   - `GROQ_MODEL`: Default is `meta-llama/llama-4-maverick-17b-128e-instruct`, or another available model like `llama-3.3-70b-versatile`.

## Step 3: Run Automated Tests
```powershell
pytest backend/tests -v
```

## Step 4: Run the Assistant
- **Option A: Terminal Chat (Fastest way to test AI & Tools)**:
  ```powershell
  python -m scripts.terminal_chat
  ```
- **Option B: Web Dashboard**:
  ```powershell
  uvicorn backend.app.main:app --reload --port 8000
  ```
  Visit: `http://localhost:8000`
