"""Tests for JARVIS — Phase 1 & 2."""

import os
import sys
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.config import get_settings
from backend.app.database import init_db, get_engine, Base


class TestConfig:
    def test_settings_load(self):
        settings = get_settings()
        assert settings.app_name == "JARVIS"
        assert settings.app_port == 8000

    def test_default_model(self):
        settings = get_settings()
        assert settings.groq_model  # Should have a default


class TestDatabase:
    def test_init_db(self, tmp_path):
        """Test database initialization with temp file."""
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test.db"
        # Force re-creation
        import backend.app.database as db_mod
        db_mod._engine = None
        db_mod._SessionLocal = None
        init_db()
        engine = get_engine()
        assert engine is not None
        # Cleanup
        db_mod._engine = None
        db_mod._SessionLocal = None
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]


class TestModels:
    def test_conversation_message_table(self):
        from backend.app.models import ConversationMessage
        assert ConversationMessage.__tablename__ == "conversation_messages"

    def test_memory_table(self):
        from backend.app.models import Memory
        assert Memory.__tablename__ == "memories"

    def test_reminder_table(self):
        from backend.app.models import Reminder
        assert Reminder.__tablename__ == "reminders"

    def test_task_table(self):
        from backend.app.models import Task
        assert Task.__tablename__ == "tasks"
