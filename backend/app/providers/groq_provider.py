"""Groq API provider — handles all communication with the Groq cloud API."""

import time
import logging
import re
import json
from typing import Optional
from groq import Groq, APIError, RateLimitError, APIConnectionError, BadRequestError
from backend.app.config import get_settings

logger = logging.getLogger(__name__)


class GroqProvider:
    """Wrapper around the Groq SDK with rate-limit awareness."""

    def __init__(self):
        self.settings = get_settings()
        if not self.settings.groq_api_key:
            logger.warning("GROQ_API_KEY is not set. AI features will not work.")
            self._client = None
        else:
            self._client = Groq(api_key=self.settings.groq_api_key)
        self._request_times: list[float] = []

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def _check_rate_limit(self):
        """Simple sliding-window rate limiter."""
        now = time.time()
        minute_ago = now - 60
        self._request_times = [t for t in self._request_times if t > minute_ago]
        if len(self._request_times) >= self.settings.rate_limit_rpm:
            wait = 60 - (now - self._request_times[0])
            logger.warning(f"Rate limit approached, waiting {wait:.1f}s")
            time.sleep(max(wait, 1))
        self._request_times.append(now)

    @staticmethod
    def _parse_failed_tool_call(failed_gen: str) -> tuple[Optional[str], dict]:
        """Extract tool name and arguments from a malformed XML or JSON generation."""
        TOOL_ALIASES = {
            "search_and_browse": "search_web",
            "web_search": "search_web",
            "google_search": "search_web",
            "browse": "search_web",
            "search": "search_web",
        }

        # 1. XML-style: <tool_call><function=name><parameter=key>value</parameter>...
        fn_match = re.search(r'<function=([a-zA-Z0-9_]+)>', failed_gen)
        if fn_match:
            fn_name = fn_match.group(1).strip()
            fn_name = TOOL_ALIASES.get(fn_name, fn_name)
            param_matches = re.findall(
                r'<\s*parameter=([a-zA-Z0-9_]+)\s*>\s*(.*?)\s*</parameter>',
                failed_gen,
                re.DOTALL,
            )
            args = {}
            for k, v in param_matches:
                v_clean = v.strip()
                try:
                    if "." in v_clean:
                        v_num = float(v_clean)
                        if v_num.is_integer():
                            v_clean = int(v_num)
                    else:
                        v_clean = int(v_clean)
                except ValueError:
                    pass
                args[k.strip()] = v_clean
            return fn_name, args

        # 2. JSON-style: {"name": "...", "arguments": {...}}
        json_match = re.search(
            r'\{\s*"name"\s*:\s*"([a-zA-Z0-9_]+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}',
            failed_gen,
            re.DOTALL,
        )
        if json_match:
            fn_name = json_match.group(1).strip()
            fn_name = TOOL_ALIASES.get(fn_name, fn_name)
            try:
                args = json.loads(json_match.group(2))
                return fn_name, args
            except Exception:
                pass

        return None, {}

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[list[dict]] = None,
    ) -> dict:
        """
        Send a chat completion request to Groq.
        Returns a dict with keys: content, role, tool_calls, usage, model.
        """
        if not self.is_available:
            raise RuntimeError(
                "Groq API key not configured. Set GROQ_API_KEY in your .env file."
            )

        self._check_rate_limit()

        model = model or self.settings.groq_model
        max_tokens = max_tokens or self.settings.groq_max_tokens
        temperature = temperature if temperature is not None else self.settings.groq_temperature

        kwargs = dict(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            result = {
                "content": choice.message.content or "",
                "role": choice.message.role,
                "tool_calls": None,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else {},
                "model": response.model,
            }
            if choice.message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ]
            return result

        except BadRequestError as e:
            # Handle Groq tool_use_failed where model generated a malformed tool call or XML whitespace typo
            err_dict = getattr(e, "body", {}) or {}
            if isinstance(err_dict, dict) and err_dict.get("error", {}).get("code") == "tool_use_failed":
                failed_gen = err_dict.get("error", {}).get("failed_generation", "")

                # 1. Try to recover tool call from failed_generation (e.g. XML with whitespace typo like < parameter=title>)
                recovered_fn, recovered_args = self._parse_failed_tool_call(failed_gen)
                if recovered_fn:
                    logger.info(f"Recovered tool call '{recovered_fn}' from failed_generation.")
                    return {
                        "content": "",
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": f"recovered_{int(time.time())}",
                                "function": {
                                    "name": recovered_fn,
                                    "arguments": json.dumps(recovered_args),
                                },
                            }
                        ],
                        "usage": {},
                        "model": model,
                    }

                # 2. Try to recover clean text before tool call
                clean_text = re.split(r"(<tool_call>|\{\"name\":)", failed_gen)[0].strip()
                if clean_text:
                    logger.info("Recovered text response from tool_use_failed generation.")
                    return {
                        "content": clean_text,
                        "role": "assistant",
                        "tool_calls": None,
                        "usage": {},
                        "model": model,
                    }

                # 3. If tools failed completely and unrecoverable, retry without tools
                if tools:
                    logger.info("Tool use failed and unrecoverable; retrying request without tools.")
                    return self.chat(
                        messages=messages,
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        tools=None,
                    )

            logger.error(f"Groq Bad Request: {e}")
            raise RuntimeError(f"Groq API error: {e}") from e
        except RateLimitError as e:
            logger.error(f"Groq rate limit hit: {e}")
            raise RuntimeError(
                "I've hit the Groq API rate limit. Please wait a minute and try again."
            ) from e
        except APIConnectionError as e:
            logger.error(f"Groq connection error: {e}")
            raise RuntimeError(
                "Cannot connect to Groq API. Check your internet connection."
            ) from e
        except APIError as e:
            logger.error(f"Groq API error: {e}")
            raise RuntimeError(f"Groq API error: {e}") from e

    def list_models(self) -> list[dict]:
        """List available models on the account."""
        if not self.is_available:
            return []
        try:
            models = self._client.models.list()
            return [
                {"id": m.id, "owned_by": m.owned_by}
                for m in models.data
            ]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def check_model(self, model_id: Optional[str] = None) -> dict:
        """Verify a model is accessible. Returns status dict."""
        model_id = model_id or self.settings.groq_model
        models = self.list_models()
        available_ids = [m["id"] for m in models]
        found = model_id in available_ids
        return {
            "model": model_id,
            "available": found,
            "total_models": len(available_ids),
            "suggestion": available_ids[:10] if not found else [],
        }
