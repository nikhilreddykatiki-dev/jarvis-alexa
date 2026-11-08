"""Memory manager — CRUD operations for user memories."""

import logging
from typing import Optional
from backend.app.database import get_session_factory
from backend.app.models import Memory

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages persistent user memories."""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id

    def _get_db(self):
        SessionLocal = get_session_factory()
        return SessionLocal()

    def save(self, key: str, value: str, category: str = "general") -> dict:
        db = self._get_db()
        try:
            existing = (
                db.query(Memory)
                .filter(Memory.user_id == self.user_id, Memory.key == key)
                .first()
            )
            if existing:
                existing.value = value
                existing.category = category
                db.commit()
                return {"status": "updated", "id": existing.id}
            memory = Memory(user_id=self.user_id, key=key, value=value, category=category)
            db.add(memory)
            db.commit()
            return {"status": "created", "id": memory.id}
        finally:
            db.close()

    def recall(self, category: Optional[str] = None, limit: int = 50) -> list[dict]:
        db = self._get_db()
        try:
            query = db.query(Memory).filter(Memory.user_id == self.user_id)
            if category:
                query = query.filter(Memory.category == category)
            memories = query.order_by(Memory.created_at.desc()).limit(limit).all()
            return [
                {"id": m.id, "key": m.key, "value": m.value, "category": m.category, "created_at": str(m.created_at)}
                for m in memories
            ]
        finally:
            db.close()

    def delete(self, memory_id: int) -> bool:
        db = self._get_db()
        try:
            memory = db.query(Memory).filter(Memory.id == memory_id, Memory.user_id == self.user_id).first()
            if not memory:
                return False
            db.delete(memory)
            db.commit()
            return True
        finally:
            db.close()

    def clear_all(self) -> int:
        db = self._get_db()
        try:
            count = db.query(Memory).filter(Memory.user_id == self.user_id).delete()
            db.commit()
            return count
        finally:
            db.close()
