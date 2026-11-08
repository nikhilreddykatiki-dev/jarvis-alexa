"""Reminder manager with local scheduler support."""

import logging
from datetime import datetime
from typing import Optional
from backend.app.database import get_session_factory
from backend.app.models import Reminder

logger = logging.getLogger(__name__)


class ReminderManager:
    """Manages reminders with SQLite persistence."""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id

    def _get_db(self):
        SessionLocal = get_session_factory()
        return SessionLocal()

    def create(self, title: str, due_at: Optional[datetime] = None, description: str = "") -> dict:
        db = self._get_db()
        try:
            reminder = Reminder(
                user_id=self.user_id, title=title, description=description, due_at=due_at
            )
            db.add(reminder)
            db.commit()
            return {"id": reminder.id, "title": title, "due_at": str(due_at) if due_at else None}
        finally:
            db.close()

    def list_active(self, include_done: bool = False) -> list[dict]:
        db = self._get_db()
        try:
            query = db.query(Reminder).filter(Reminder.user_id == self.user_id)
            if not include_done:
                query = query.filter(Reminder.is_done == False)  # noqa: E712
            reminders = query.order_by(Reminder.due_at.asc().nullslast()).all()
            return [
                {
                    "id": r.id, "title": r.title, "due_at": str(r.due_at) if r.due_at else None,
                    "is_done": r.is_done, "description": r.description,
                }
                for r in reminders
            ]
        finally:
            db.close()

    def complete(self, reminder_id: int) -> bool:
        db = self._get_db()
        try:
            r = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.user_id == self.user_id).first()
            if not r:
                return False
            r.is_done = True
            db.commit()
            return True
        finally:
            db.close()

    def delete(self, reminder_id: int) -> bool:
        db = self._get_db()
        try:
            r = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.user_id == self.user_id).first()
            if not r:
                return False
            db.delete(r)
            db.commit()
            return True
        finally:
            db.close()

    def get_due_reminders(self) -> list[dict]:
        """Get reminders that are past due and not completed."""
        db = self._get_db()
        try:
            now = datetime.now()
            reminders = (
                db.query(Reminder)
                .filter(
                    Reminder.user_id == self.user_id,
                    Reminder.is_done == False,  # noqa: E712
                    Reminder.due_at <= now,
                )
                .all()
            )
            return [{"id": r.id, "title": r.title, "due_at": str(r.due_at)} for r in reminders]
        finally:
            db.close()
