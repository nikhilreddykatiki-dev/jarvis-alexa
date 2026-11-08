"""JARVIS Terminal Chat — a simple command-line interface.

Usage:
    cd jarvis
    python -m scripts.terminal_chat
"""

import sys
import os
import threading
import time
from backend.app.reminders.manager import ReminderManager

def start_reminder_daemon(user_id: str):
    """Background thread that alerts the user when a reminder is due."""
    def checker():
        mgr = ReminderManager(user_id=user_id)
        while True:
            time.sleep(2)
            try:
                due = mgr.get_due_reminders()
                for r in due:
                    print(f"\a\n\n🔔 [JARVIS REMINDER ALERT]: {r['title']}! (Due at {r.get('due_at')})")
                    print("🧑 You: ", end="", flush=True)
                    mgr.complete(r["id"])
            except Exception:
                pass

    t = threading.Thread(target=checker, daemon=True)
    t.start()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.agents.jarvis_agent import JarvisAgent
from backend.app.database import init_db
from backend.app.providers.groq_provider import GroqProvider
from backend.app.config import get_settings

# Load .env
from dotenv import load_dotenv
load_dotenv()


def print_banner():
    print("\n" + "=" * 60)
    print("  ╔═══════════════════════════════════════╗")
    print("  ║     J.A.R.V.I.S. Terminal v1.0        ║")
    print("  ║   Zero Cost Personal AI Assistant      ║")
    print("  ╚═══════════════════════════════════════╝")
    print("=" * 60)


def check_setup():
    """Verify API key and model."""
    settings = get_settings()
    groq = GroqProvider()

    if not groq.is_available:
        print("\n❌ GROQ_API_KEY not set!")
        print("   1. Get a free key at https://console.groq.com/keys")
        print("   2. Copy .env.example to .env")
        print("   3. Paste your key in the .env file")
        return False

    print(f"\n✅ Groq API key configured")
    print(f"📡 Model: {settings.groq_model}")

    # Check model availability
    check = groq.check_model()
    if check["available"]:
        print(f"✅ Model '{settings.groq_model}' is available")
    else:
        print(f"⚠️  Model '{settings.groq_model}' not found on your account.")
        if check["suggestion"]:
            print(f"   Available models (first 10):")
            for m in check["suggestion"]:
                print(f"     - {m}")
            print(f"\n   Update GROQ_MODEL in your .env file to one of these.")
        return False

    return True


def main():
    print_banner()

    # Initialize database
    init_db()
    print("✅ Database ready")

    if not check_setup():
        print("\n⚠️  Fix the issues above and restart.")
        sys.exit(1)

    # Create agent
    agent = JarvisAgent(user_id="terminal_user")
    start_reminder_daemon(agent.user_id)
    print(f"\n🆔 Session: {agent.session_id}")
    print("\nType your message. Commands:")
    print("  /quit     - Exit")
    print("  /new      - Start new session")
    print("  /history  - Show conversation history")
    print("  /models   - List available models")
    print("-" * 60)

    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() == "/quit":
            print("\nGoodbye! 👋")
            break

        if user_input.lower() == "/new":
            agent = JarvisAgent(user_id="terminal_user")
            print(f"\n🔄 New session: {agent.session_id}")
            continue

        if user_input.lower() == "/history":
            history = agent.get_history()
            if not history:
                print("\n📭 No messages in this session yet.")
            else:
                print("\n📜 Conversation History:")
                for msg in history:
                    icon = "🧑" if msg["role"] == "user" else "🤖"
                    print(f"  {icon} {msg['role'].title()}: {msg['content'][:200]}")
            continue

        if user_input.lower() == "/models":
            groq = GroqProvider()
            models = groq.list_models()
            print(f"\n📋 Available models ({len(models)}):")
            for m in models:
                marker = " ← current" if m["id"] == get_settings().groq_model else ""
                print(f"  • {m['id']}{marker}")
            continue

        # Chat with JARVIS
        print("\n🤖 JARVIS: ", end="", flush=True)
        response = agent.chat(user_input)
        print(response)


if __name__ == "__main__":
    main()
