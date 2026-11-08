"""JARVIS Agent — orchestrates conversation, tools, and memory."""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Optional

from backend.app.config import get_settings
from backend.app.providers.groq_provider import GroqProvider
from backend.app.agents.prompts import JARVIS_SYSTEM_PROMPT, ALEXA_ADDENDUM
from backend.app.agents.tools import TOOL_DEFINITIONS, ToolExecutor, validate_tool_call
from backend.app.database import get_session_factory
from backend.app.models import ConversationMessage

logger = logging.getLogger(__name__)


class JarvisAgent:
    """Main conversational agent with tool-calling support."""

    MAX_TOOL_ROUNDS = 3  # Prevent infinite tool loops
    MAX_CONTEXT_MESSAGES = 20  # Keep context window manageable

    def __init__(self, user_id: str = "default", session_id: Optional[str] = None, is_alexa: bool = False):
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.is_alexa = is_alexa
        self.groq = GroqProvider()
        self.settings = get_settings()

    def _get_system_prompt(self) -> str:
        prompt = JARVIS_SYSTEM_PROMPT
        if self.is_alexa:
            prompt += ALEXA_ADDENDUM
        now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        prompt += f"\n\nCurrent date/time: {now}"
        return prompt

    def _load_conversation_history(self, db_session) -> list[dict]:
        """Load recent conversation from database."""
        messages = (
            db_session.query(ConversationMessage)
            .filter(
                ConversationMessage.session_id == self.session_id,
                ConversationMessage.user_id == self.user_id,
            )
            .order_by(ConversationMessage.created_at.asc())
            .all()
        )
        recent = messages[-self.MAX_CONTEXT_MESSAGES:]
        return [{"role": m.role, "content": m.content} for m in recent]

    def _save_message(self, db_session, role: str, content: str):
        """Persist a message to database."""
        msg = ConversationMessage(
            session_id=self.session_id,
            user_id=self.user_id,
            role=role,
            content=content,
        )
        db_session.add(msg)
        db_session.commit()

    def _load_user_memories(self, db_session) -> str:
        """Load stored memories to inject into context."""
        from backend.app.models import Memory

        memories = (
            db_session.query(Memory)
            .filter(Memory.user_id == self.user_id)
            .limit(20)
            .all()
        )
        if not memories:
            return ""
        lines = [f"- {m.key}: {m.value}" for m in memories]
        return "\n## Known facts about the user:\n" + "\n".join(lines) + "\n"

    def chat(self, user_message: str) -> str:
        """
        Process a user message and return the assistant's response.
        Handles tool calls automatically.
        """
        SessionLocal = get_session_factory()
        db = SessionLocal()

        try:
            # Build messages
            system_content = self._get_system_prompt()
            memory_context = self._load_user_memories(db)
            if memory_context:
                system_content += memory_context

            history = self._load_conversation_history(db)
            messages = [{"role": "system", "content": system_content}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_message})

            # Save user message
            self._save_message(db, "user", user_message)

            tool_executor = ToolExecutor(db, self.user_id)

            # Auto-grounding: Check if query relates to current facts, sports, news, or weather
            lower_msg = user_message.lower()
            grounding_info = ""

            # Check overdue reminders to proactively alert the user
            from backend.app.reminders.manager import ReminderManager
            rem_mgr = ReminderManager(user_id=self.user_id)
            due_reminders = rem_mgr.get_due_reminders()
            if due_reminders:
                alerts = ", ".join([f"'{r['title']}'" for r in due_reminders])
                grounding_info += (
                    f"\n## OVERDUE REMINDER ALERT:\n"
                    f"The user has active overdue reminder(s) right now: {alerts}. "
                    f"You MUST verbally deliver and alert the user about this reminder first before answering their query.\n"
                )
                for r in due_reminders:
                    rem_mgr.complete(r["id"])

            # Check weather
            if any(w in lower_msg for w in ["weather", "temperature", "forecast", "rain", "sunny"]):
                loc = re.sub(r"(what|is|the|weather|in|for|at|\?|\.)", "", lower_msg).strip() or "London"
                weather_res = tool_executor._tool_get_weather(loc)
                grounding_info += f"\n## Live Weather Data for '{loc}':\n{json.dumps(weather_res)}\n"

            # Universal live web grounding for any informational question (sports, news, tech, products, facts)
            is_action = any(k in lower_msg for k in ["remind", "reminder", "task", "set a timer", "delete memory", "clear memory"])
            if not is_action and len(user_message.strip()) > 3:
                search_res = tool_executor._tool_search_web(user_message, limit=5)
                snippets = search_res.get("results", [])
                if snippets:
                    formatted_snippets = []
                    for s in snippets:
                        if isinstance(s, dict):
                            formatted_snippets.append(f"- {s.get('title', '')}: {s.get('snippet', '')}")
                        else:
                            formatted_snippets.append(str(s))
                    grounding_info += f"\n## Live Data for '{user_message}':\n" + "\n".join(formatted_snippets) + "\n"

            active_tools = TOOL_DEFINITIONS
            if grounding_info:
                messages[0]["content"] += f"\n{grounding_info}\nUse the live data above to answer the user truthfully and concisely."
                # Live data is already grounded; pass tools=None to guarantee instant final text synthesis
                active_tools = None

            # Call Groq with tools
            response = self.groq.chat(
                messages=messages,
                tools=active_tools,
            )

            # Handle tool calls (single round on Alexa to guarantee sub-3s response)
            rounds = 0
            max_rounds = 1 if self.is_alexa else self.MAX_TOOL_ROUNDS
            while response.get("tool_calls") and rounds < max_rounds:
                rounds += 1
                assistant_msg = {"role": "assistant", "content": response["content"] or ""}
                if response["tool_calls"]:
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": tc["function"],
                        }
                        for tc in response["tool_calls"]
                    ]
                messages.append(assistant_msg)

                for tc in response["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    fn_args = tc["function"]["arguments"]

                    is_valid, error, parsed_args = validate_tool_call(fn_name, fn_args)
                    if is_valid:
                        result = tool_executor.execute(fn_name, parsed_args)
                    else:
                        result = json.dumps({"error": error})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
                    logger.info(f"Tool '{fn_name}' executed: {result[:200]}")

                # Call Groq again to synthesize the answer
                # Pass tools=None on Alexa or final round so model produces final text immediately
                next_tools = None if self.is_alexa else (TOOL_DEFINITIONS if rounds < 2 else None)
                response = self.groq.chat(messages=messages, tools=next_tools)

            answer = (response.get("content") or "").strip()

            # Fallback if model returned empty content after tool calls
            if not answer:
                resp_forced = self.groq.chat(messages=messages, tools=None)
                answer = (resp_forced.get("content") or "").strip() or "I found the information, but couldn't format a complete response. Please ask again."

            if self.is_alexa and len(answer) > 6000:
                answer = answer[:5900] + "... Would you like me to continue?"

            self._save_message(db, "assistant", answer)
            return answer

        except RuntimeError as e:
            logger.error(f"Agent error: {e}")
            return str(e)
        except Exception as e:
            logger.error(f"Unexpected error in agent: {e}", exc_info=True)
            return "I encountered an unexpected error. Please try again."
        finally:
            db.close()

    def get_history(self) -> list[dict]:
        """Return conversation history for the current session."""
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            history = self._load_conversation_history(db)
            return history
        finally:
            db.close()
