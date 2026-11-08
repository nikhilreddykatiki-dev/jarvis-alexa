"""Tests for JARVIS Agent components."""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.agents.tools import validate_tool_call, ALLOWED_TOOLS, TOOL_DEFINITIONS
from backend.app.agents.prompts import JARVIS_SYSTEM_PROMPT


class TestToolValidation:
    def test_valid_tool(self):
        is_valid, error, args = validate_tool_call(
            "get_current_time", json.dumps({})
        )
        assert is_valid
        assert error == ""

    def test_invalid_tool_name(self):
        is_valid, error, args = validate_tool_call(
            "run_shell_command", json.dumps({"cmd": "rm -rf /"})
        )
        assert not is_valid
        assert "not allowed" in error

    def test_invalid_json(self):
        is_valid, error, args = validate_tool_call(
            "save_memory", "not valid json{{"
        )
        assert not is_valid
        assert "Invalid JSON" in error

    def test_all_tools_in_allowlist(self):
        for tool_def in TOOL_DEFINITIONS:
            assert tool_def["function"]["name"] in ALLOWED_TOOLS

    def test_live_data_tools_registered(self):
        assert "search_web" in ALLOWED_TOOLS
        assert "get_weather" in ALLOWED_TOOLS


class TestPrompts:
    def test_system_prompt_exists(self):
        assert len(JARVIS_SYSTEM_PROMPT) > 100

    def test_system_prompt_contains_personality(self):
        assert "JARVIS" in JARVIS_SYSTEM_PROMPT

    def test_system_prompt_has_safety_rules(self):
        assert "fabricate" in JARVIS_SYSTEM_PROMPT.lower() or "invent" in JARVIS_SYSTEM_PROMPT.lower()
