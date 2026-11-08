"""Tests for Memory and Reminder Managers."""

import os
import pytest
from backend.app.database import init_db
from backend.app.memory.manager import MemoryManager
from backend.app.reminders.manager import ReminderManager


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test_mem.db"
    import backend.app.database as db_mod
    db_mod._engine = None
    db_mod._SessionLocal = None
    init_db()
    yield
    db_mod._engine = None
    db_mod._SessionLocal = None


def test_memory_lifecycle():
    mem_mgr = MemoryManager(user_id="test_user")
    # Save
    res = mem_mgr.save("city", "Bengaluru", "preference")
    assert res["status"] == "created"

    # Recall
    memories = mem_mgr.recall()
    assert len(memories) == 1
    assert memories[0]["key"] == "city"
    assert memories[0]["value"] == "Bengaluru"

    # Update
    res_up = mem_mgr.save("city", "Mumbai", "preference")
    assert res_up["status"] == "updated"
    assert mem_mgr.recall()[0]["value"] == "Mumbai"

    # Delete
    mem_id = memories[0]["id"]
    assert mem_mgr.delete(mem_id)
    assert len(mem_mgr.recall()) == 0


def test_reminder_lifecycle():
    rem_mgr = ReminderManager(user_id="test_user")
    # Create
    r = rem_mgr.create(title="Drink water")
    assert r["id"] is not None

    # List active
    active = rem_mgr.list_active()
    assert len(active) == 1
    assert active[0]["title"] == "Drink water"

    # Complete
    assert rem_mgr.complete(r["id"])
    assert len(rem_mgr.list_active(include_done=False)) == 0
    assert len(rem_mgr.list_active(include_done=True)) == 1
