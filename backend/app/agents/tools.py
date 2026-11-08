"""Tool definitions and execution for JARVIS agent.

All tools are explicitly allow-listed. No arbitrary code execution.
"""

import inspect
import json
import logging
import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote_plus, unquote
import xml.etree.ElementTree as ET
import httpx

logger = logging.getLogger(__name__)

# ── Tool Registry (allowlist) ──────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save a personal fact or preference the user explicitly asked to remember.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Short label for the memory, e.g. 'favorite_color'",
                    },
                    "value": {
                        "type": "string",
                        "description": "The value to remember.",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["preference", "fact", "routine"],
                        "description": "Category of the memory.",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memories",
            "description": "Retrieve stored memories/preferences for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Create a new reminder with an alarm time or delay from now. Use when the user says 'remind me...'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "What to be reminded about.",
                    },
                    "seconds_from_now": {
                        "type": "integer",
                        "description": "Number of seconds from now to trigger the reminder (e.g. 30).",
                    },
                    "minutes_from_now": {
                        "type": "integer",
                        "description": "Number of minutes from now to trigger the reminder (e.g. 5).",
                    },
                    "due_at": {
                        "type": "string",
                        "description": "Exact ISO 8601 datetime when the reminder is due. Optional.",
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "List the user's active reminders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_done": {
                        "type": "boolean",
                        "description": "Whether to include completed reminders.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_reminder",
            "description": "Mark a reminder as done.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {
                        "type": "integer",
                        "description": "ID of the reminder to complete.",
                    },
                },
                "required": ["reminder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_reminder",
            "description": "Delete a reminder. Use with caution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {
                        "type": "integer",
                        "description": "ID of the reminder to delete.",
                    },
                },
                "required": ["reminder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Add a task to the user's task list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional details.",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "1=high, 2=medium, 3=low.",
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List the user's tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "done", "all"],
                        "description": "Filter by status.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update a task's status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "done"],
                    },
                },
                "required": ["task_id", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": "Delete a stored memory by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "integer",
                        "description": "ID of the memory to delete.",
                    },
                },
                "required": ["memory_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_memories",
            "description": "Delete ALL stored memories for the user. Requires confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true to proceed.",
                    },
                },
                "required": ["confirm"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the live internet for recent news, real-time facts, current events, or information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query keywords.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather conditions and forecast for any city or location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. 'Mumbai', 'London', 'New York'.",
                    },
                },
                "required": ["location"],
            },
        },
    },
]

# Allowlist of executable tools
ALLOWED_TOOLS = {t["function"]["name"] for t in TOOL_DEFINITIONS}

TOOL_ALIASES = {
    "search_and_browse": "search_web",
    "web_search": "search_web",
    "google_search": "search_web",
    "browse": "search_web",
    "search": "search_web",
}


def validate_tool_call(name: str, arguments: str) -> tuple[bool, str, dict]:
    """Validate a tool call against the allowlist and parse arguments.
    
    Returns (is_valid, error_message, parsed_args).
    """
    canonical_name = TOOL_ALIASES.get(name, name)
    if canonical_name not in ALLOWED_TOOLS:
        return False, f"Tool '{name}' is not allowed.", {}

    try:
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON arguments: {e}", {}

    return True, "", args


class ToolExecutor:
    """Executes validated tool calls against the database."""

    def __init__(self, db_session, user_id: str = "default"):
        self.db = db_session
        self.user_id = user_id

    def execute(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool and return the result as a string."""
        canonical_name = TOOL_ALIASES.get(tool_name, tool_name)
        is_valid, error, args = validate_tool_call(canonical_name, arguments)
        if not is_valid:
            return json.dumps({"error": error})

        handler = getattr(self, f"_tool_{canonical_name}", None)
        if handler is None:
            return json.dumps({"error": f"No handler for tool '{canonical_name}'"})

        try:
            sig = inspect.signature(handler)
            has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            if not has_var_keyword:
                filtered_args = {k: v for k, v in args.items() if k in sig.parameters}
            else:
                filtered_args = args
            result = handler(**filtered_args)
            return json.dumps(result, default=str)
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {e}")
            return json.dumps({"error": str(e)})

    # ── Tool Handlers ──

    def _tool_get_current_time(self) -> dict:
        now = datetime.now()
        return {
            "datetime": now.isoformat(),
            "formatted": now.strftime("%A, %B %d, %Y at %I:%M %p"),
        }

    def _tool_save_memory(self, key: str, value: str, category: str = "general") -> dict:
        from backend.app.models import Memory

        existing = (
            self.db.query(Memory)
            .filter(Memory.user_id == self.user_id, Memory.key == key)
            .first()
        )
        if existing:
            existing.value = value
            existing.category = category
            self.db.commit()
            return {"status": "updated", "key": key, "value": value}

        memory = Memory(
            user_id=self.user_id, key=key, value=value, category=category
        )
        self.db.add(memory)
        self.db.commit()
        return {"status": "saved", "key": key, "value": value}

    def _tool_recall_memories(self, category: Optional[str] = None) -> dict:
        from backend.app.models import Memory

        query = self.db.query(Memory).filter(Memory.user_id == self.user_id)
        if category:
            query = query.filter(Memory.category == category)
        memories = query.order_by(Memory.created_at.desc()).limit(50).all()
        return {
            "memories": [
                {
                    "id": m.id,
                    "key": m.key,
                    "value": m.value,
                    "category": m.category,
                    "created_at": str(m.created_at),
                }
                for m in memories
            ]
        }

    def _tool_delete_memory(self, memory_id: int) -> dict:
        from backend.app.models import Memory

        memory = (
            self.db.query(Memory)
            .filter(Memory.id == memory_id, Memory.user_id == self.user_id)
            .first()
        )
        if not memory:
            return {"error": "Memory not found."}
        self.db.delete(memory)
        self.db.commit()
        return {"status": "deleted", "id": memory_id}

    def _tool_clear_memories(self, confirm: bool = False) -> dict:
        from backend.app.models import Memory

        if not confirm:
            return {"error": "Confirmation required. Set confirm=true."}
        count = (
            self.db.query(Memory)
            .filter(Memory.user_id == self.user_id)
            .delete()
        )
        self.db.commit()
        return {"status": "cleared", "deleted_count": count}

    def _tool_create_reminder(
        self,
        title: str,
        due_at: Optional[str] = None,
        seconds_from_now: Optional[int] = None,
        minutes_from_now: Optional[int] = None,
        **kwargs: Any,
    ) -> dict:
        from datetime import timedelta
        from backend.app.models import Reminder

        calc_due = None
        if seconds_from_now is not None:
            calc_due = datetime.now() + timedelta(seconds=int(seconds_from_now))
        elif minutes_from_now is not None:
            calc_due = datetime.now() + timedelta(minutes=int(minutes_from_now))
        elif due_at:
            try:
                calc_due = datetime.fromisoformat(due_at)
            except Exception:
                calc_due = None

        reminder = Reminder(
            user_id=self.user_id,
            title=title,
            due_at=calc_due,
        )
        self.db.add(reminder)
        self.db.commit()
        return {"status": "created", "id": reminder.id, "title": title, "due_at": str(calc_due) if calc_due else None}

    def _tool_list_reminders(self, include_done: bool = False) -> dict:
        from backend.app.models import Reminder

        query = self.db.query(Reminder).filter(Reminder.user_id == self.user_id)
        if not include_done:
            query = query.filter(Reminder.is_done == False)  # noqa: E712
        reminders = query.order_by(Reminder.created_at.desc()).all()
        return {
            "reminders": [
                {
                    "id": r.id,
                    "title": r.title,
                    "due_at": str(r.due_at) if r.due_at else None,
                    "is_done": r.is_done,
                    "created_at": str(r.created_at),
                }
                for r in reminders
            ]
        }

    def _tool_complete_reminder(self, reminder_id: int) -> dict:
        from backend.app.models import Reminder

        reminder = (
            self.db.query(Reminder)
            .filter(Reminder.id == reminder_id, Reminder.user_id == self.user_id)
            .first()
        )
        if not reminder:
            return {"error": "Reminder not found."}
        reminder.is_done = True
        self.db.commit()
        return {"status": "completed", "id": reminder_id, "title": reminder.title}

    def _tool_delete_reminder(self, reminder_id: int) -> dict:
        from backend.app.models import Reminder

        reminder = (
            self.db.query(Reminder)
            .filter(Reminder.id == reminder_id, Reminder.user_id == self.user_id)
            .first()
        )
        if not reminder:
            return {"error": "Reminder not found."}
        self.db.delete(reminder)
        self.db.commit()
        return {"status": "deleted", "id": reminder_id}

    def _tool_create_task(
        self, title: str, description: str = "", priority: int = 2
    ) -> dict:
        from backend.app.models import Task

        task = Task(
            user_id=self.user_id,
            title=title,
            description=description,
            priority=max(1, min(3, priority)),
        )
        self.db.add(task)
        self.db.commit()
        return {"status": "created", "id": task.id, "title": title}

    def _tool_list_tasks(self, status: str = "pending") -> dict:
        from backend.app.models import Task

        query = self.db.query(Task).filter(Task.user_id == self.user_id)
        if status != "all":
            query = query.filter(Task.status == status)
        tasks = query.order_by(Task.priority, Task.created_at.desc()).all()
        return {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "priority": t.priority,
                    "status": t.status,
                    "created_at": str(t.created_at),
                }
                for t in tasks
            ]
        }

    def _tool_update_task(self, task_id: int, status: str = "done") -> dict:
        from backend.app.models import Task

        task = (
            self.db.query(Task)
            .filter(Task.id == task_id, Task.user_id == self.user_id)
            .first()
        )
        if not task:
            return {"error": "Task not found."}
        task.status = status
        self.db.commit()
        return {"status": "updated", "id": task_id, "new_status": status}

    def _tool_get_weather(self, location: str, **kwargs: Any) -> dict:
        """Fetch current weather for a location from wttr.in (100% free, no API key needed)."""
        clean_loc = quote_plus(location.strip())
        url = f"https://wttr.in/{clean_loc}?format=j1"
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers={"User-Agent": "Jarvis-Assistant/1.0"})
                if resp.status_code != 200:
                    return {"error": f"Weather service responded with status {resp.status_code}"}
                data = resp.json()
                current = data.get("current_condition", [{}])[0]
                area = data.get("nearest_area", [{}])[0]
                city = area.get("areaName", [{}])[0].get("value", location)
                country = area.get("country", [{}])[0].get("value", "")

                return {
                    "location": f"{city}, {country}".strip(", "),
                    "temperature_c": current.get("temp_C"),
                    "feels_like_c": current.get("FeelsLikeC"),
                    "condition": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
                    "humidity": current.get("humidity") + "%" if current.get("humidity") else "Unknown",
                    "wind_kmph": current.get("windspeedKmph"),
                }
        except Exception as e:
            logger.error(f"Weather lookup error: {e}")
            return {"error": f"Could not retrieve weather: {str(e)}"}

    def _tool_search_web(self, query: str, limit: int = 5, **kwargs: Any) -> dict:
        """Search the internet for real-time live data, standings, and facts without API keys."""
        lower_q = query.lower()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        # ── 1. Universal Sports Standings (NBA, NFL, MLB, NHL, Soccer Leagues) ──
        SPORTS_MAP = {
            "nba": ("basketball", "nba"),
            "wnba": ("basketball", "wnba"),
            "nfl": ("football", "nfl"),
            "mlb": ("baseball", "mlb"),
            "nhl": ("hockey", "nhl"),
            "premier league": ("soccer", "eng.1"),
            "epl": ("soccer", "eng.1"),
            "la liga": ("soccer", "esp.1"),
            "laliga": ("soccer", "esp.1"),
            "serie a": ("soccer", "ita.1"),
            "bundesliga": ("soccer", "ger.1"),
            "ligue 1": ("soccer", "fra.1"),
            "champions league": ("soccer", "uefa.champions"),
        }

        TEAM_ALIASES = {
            # NBA
            "gsw": ("basketball", "nba", "Golden State Warriors"),
            "warriors": ("basketball", "nba", "Golden State Warriors"),
            "lakers": ("basketball", "nba", "Los Angeles Lakers"),
            "celtics": ("basketball", "nba", "Boston Celtics"),
            "bulls": ("basketball", "nba", "Chicago Bulls"),
            "knicks": ("basketball", "nba", "New York Knicks"),
            "heat": ("basketball", "nba", "Miami Heat"),
            "bucks": ("basketball", "nba", "Milwaukee Bucks"),
            "nuggets": ("basketball", "nba", "Denver Nuggets"),
            "suns": ("basketball", "nba", "Phoenix Suns"),
            "clippers": ("basketball", "nba", "LA Clippers"),
            "mavericks": ("basketball", "nba", "Dallas Mavericks"),
            "mavs": ("basketball", "nba", "Dallas Mavericks"),
            "76ers": ("basketball", "nba", "Philadelphia 76ers"),
            # NFL
            "chiefs": ("football", "nfl", "Kansas City Chiefs"),
            "eagles": ("football", "nfl", "Philadelphia Eagles"),
            "cowboys": ("football", "nfl", "Dallas Cowboys"),
            "49ers": ("football", "nfl", "San Francisco 49ers"),
            # Soccer
            "real madrid": ("soccer", "esp.1", "Real Madrid"),
            "barcelona": ("soccer", "esp.1", "Barcelona"),
            "barca": ("soccer", "esp.1", "Barcelona"),
            "atletico": ("soccer", "esp.1", "Atlético Madrid"),
            "man utd": ("soccer", "eng.1", "Manchester United"),
            "manchester united": ("soccer", "eng.1", "Manchester United"),
            "man city": ("soccer", "eng.1", "Manchester City"),
            "arsenal": ("soccer", "eng.1", "Arsenal"),
            "liverpool": ("soccer", "eng.1", "Liverpool"),
            "chelsea": ("soccer", "eng.1", "Chelsea"),
            "spurs": ("soccer", "eng.1", "Tottenham Hotspur"),
            "tottenham": ("soccer", "eng.1", "Tottenham Hotspur"),
            "bayern": ("soccer", "ger.1", "Bayern Munich"),
            "dortmund": ("soccer", "ger.1", "Borussia Dortmund"),
            "juventus": ("soccer", "ita.1", "Juventus"),
            "inter milan": ("soccer", "ita.1", "Internazionale"),
            "psg": ("soccer", "fra.1", "Paris Saint-Germain"),
        }

        # ── 1. Standings Interceptor (ESPN API) ──
        # ONLY trigger if the query explicitly asks for standings / table / rank / seed / position
        standings_keywords = [
            "table", "standing", "standings", "position", "positions",
            "rank", "ranks", "ranking", "rankings", "seed", "seeds",
            "seeded", "points table", "playoff picture"
        ]
        is_standings_query = any(k in lower_q for k in standings_keywords) or (
            any(w in lower_q for w in ["where is", "where are"]) and any(lg in lower_q for lg in SPORTS_MAP)
        )

        sport_league = None
        target_team = None

        if is_standings_query:
            for alias, val in TEAM_ALIASES.items():
                if alias in lower_q:
                    sport_league = (val[0], val[1])
                    target_team = val[2]
                    break

            if not sport_league:
                for lk, val in SPORTS_MAP.items():
                    if lk in lower_q:
                        sport_league = val
                        break

        if sport_league:
            try:
                sport, lg = sport_league
                with httpx.Client(timeout=5.0) as client:
                    espn_url = f"https://site.api.espn.com/apis/v2/sports/{sport}/{lg}/standings"
                    resp = client.get(espn_url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        entries = []
                        def extract_entries(node):
                            if isinstance(node, dict):
                                if "standings" in node and "entries" in node["standings"]:
                                    entries.extend(node["standings"]["entries"])
                                for v in node.values():
                                    extract_entries(v)
                            elif isinstance(node, list):
                                for item in node:
                                    extract_entries(item)

                        extract_entries(data.get("children", []))
                        table_data = []
                        for e in entries:
                            t_name = e.get("team", {}).get("displayName", "")
                            st = {s.get("name"): s.get("displayValue") for s in e.get("stats", [])}
                            table_data.append({
                                "rank": st.get("playoffSeed") or st.get("rank"),
                                "team": t_name,
                                "played": st.get("gamesPlayed"),
                                "wins": st.get("wins"),
                                "losses": st.get("losses"),
                                "streak": st.get("streak", ""),
                                "record": st.get("overall", f"{st.get('wins', 0)}-{st.get('losses', 0)}"),
                                "points": st.get("points"),
                            })
                        if target_team:
                            matched = [t for t in table_data if target_team.lower() in t["team"].lower()]
                            if matched:
                                return {
                                    "query": query,
                                    "source": f"ESPN {lg.upper()} Live Feed",
                                    "results": matched,
                                    "top_teams": table_data[:5]
                                }
                        if table_data:
                            return {
                                "query": query,
                                "source": f"ESPN {lg.upper()} Live Feed",
                                "results": table_data,
                            }
            except Exception as e:
                logger.warning(f"ESPN Standings lookup error: {e}")

        # ── 2. Real-Time News (Google News RSS Feed) for breaking & recent queries ──
        news_triggers = ["retire", "death", "died", "trade", "signed", "injury", "breaking", "news", "today", "yesterday", "latest", "announced"]
        if any(w in lower_q for w in news_triggers):
            try:
                with httpx.Client(timeout=6.0) as client:
                    news_url = f"https://news.google.com/rss/search?q={quote_plus(query)}"
                    n_resp = client.get(news_url, headers=headers, follow_redirects=True)
                    if n_resp.status_code == 200:
                        root = ET.fromstring(n_resp.text)
                        items = root.findall('.//item')
                        if items:
                            news_results = []
                            for it in items[:5]:
                                title = it.find('title').text if it.find('title') is not None else ""
                                pdate = it.find('pubDate').text if it.find('pubDate') is not None else ""
                                if title:
                                    news_results.append({
                                        "title": title,
                                        "published": pdate,
                                        "snippet": f"Published: {pdate}. Headline: {title}"
                                    })
                            if news_results:
                                return {
                                    "query": query,
                                    "source": "Google News Live RSS",
                                    "results": news_results,
                                }
            except Exception as e:
                logger.warning(f"Google News RSS error: {e}")

        # ── 3. General Web Search via DuckDuckGo with deep article extraction ──
        try:
            with httpx.Client(timeout=8.0) as client:
                ddg_api = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
                resp = client.get(ddg_api, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    abstract = data.get("AbstractText", "")
                    if abstract:
                        return {"query": query, "summary": abstract, "source": data.get("Heading", "DuckDuckGo")}

                html_url = "https://html.duckduckgo.com/html/"
                resp = client.post(html_url, headers=headers, data={"q": query})
                if resp.status_code == 200:
                    titles = re.findall(r'<h2 class="result__title">\s*<a[^>]*class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                    snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                    clean_results = []
                    max_results = max(1, min(10, int(limit)))
                    for t, s in zip(titles[:max_results], snippets[:max_results]):
                        clean_t = re.sub(r"<[^>]+>", "", t).strip()
                        clean_s = re.sub(r"<[^>]+>", "", s).strip()
                        if clean_t or clean_s:
                            clean_results.append({"title": clean_t, "snippet": clean_s})

                    # Deep read: Fetch actual text from top article URL
                    raw_urls = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', resp.text)
                    if not raw_urls:
                        raw_urls = re.findall(r'<a[^>]+class="result__snippet"[^>]+href="([^"]+)"', resp.text)
                    if raw_urls:
                        m = re.search(r'uddg=([^&]+)', raw_urls[0])
                        actual_url = unquote(m.group(1)) if m else raw_urls[0]
                        if not actual_url.startswith("http"):
                            actual_url = "https:" + actual_url
                        try:
                            page_resp = client.get(actual_url, follow_redirects=True, timeout=4.0, headers=headers)
                            clean_page = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', page_resp.text, flags=re.DOTALL)
                            clean_page = re.sub(r'<[^>]+>', ' ', clean_page)
                            deep_text = re.sub(r'\s+', ' ', clean_page).strip()[:1000]
                            if deep_text:
                                clean_results.insert(0, {"title": "Top Article Body", "snippet": deep_text})
                        except Exception:
                            pass

                # Fallback: DuckDuckGo Lite if HTML gave no results
                if not clean_results:
                    try:
                        lite_url = "https://lite.duckduckgo.com/lite/"
                        l_resp = client.post(lite_url, headers=headers, data={"q": query})
                        if l_resp.status_code == 200:
                            l_snippets = re.findall(r'<td class="result-snippet">\s*(.*?)\s*</td>', l_resp.text, re.DOTALL)
                            l_titles = re.findall(r'<a[^>]+class="result-link"[^>]*>(.*?)</a>', l_resp.text, re.DOTALL)
                            for t, s in zip(l_titles[:limit], l_snippets[:limit]):
                                clean_t = re.sub(r"<[^>]+>", "", t).strip()
                                clean_s = re.sub(r"<[^>]+>", "", s).strip()
                                if clean_t or clean_s:
                                    clean_results.append({"title": clean_t, "snippet": clean_s})
                    except Exception as e:
                        logger.warning(f"DuckDuckGo Lite search error: {e}")

                # Fallback: Wikipedia API for encyclopedic entities
                if not clean_results:
                    try:
                        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(query)}&format=json"
                        w_resp = client.get(wiki_url, headers=headers)
                        if w_resp.status_code == 200:
                            w_items = w_resp.json().get("query", {}).get("search", [])
                            for item in w_items[:limit]:
                                clean_t = item.get("title", "")
                                clean_s = re.sub(r"<[^>]+>", "", item.get("snippet", "")).strip()
                                if clean_t or clean_s:
                                    clean_results.append({"title": f"Wikipedia: {clean_t}", "snippet": clean_s})
                    except Exception as e:
                        logger.warning(f"Wikipedia API search error: {e}")

                if clean_results:
                    return {"query": query, "results": clean_results}

            return {"query": query, "message": "No specific search results found."}
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"error": f"Search failed: {str(e)}"}
