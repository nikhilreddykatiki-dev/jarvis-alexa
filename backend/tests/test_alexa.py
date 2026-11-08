"""Tests for Alexa ASK Request Verification and Intents."""

import json
import pytest
from backend.app.integrations.alexa.intents import build_response
from backend.app.integrations.alexa.handler import handle_alexa_request
from backend.app.integrations.alexa.security import validate_timestamp, validate_cert_url


def test_build_response_plain():
    resp = build_response(speech_text="Hello world", should_end_session=False)
    assert resp["version"] == "1.0"
    assert resp["response"]["outputSpeech"]["type"] == "PlainText"
    assert resp["response"]["outputSpeech"]["text"] == "Hello world"
    assert not resp["response"]["shouldEndSession"]


def test_build_response_ssml():
    resp = build_response(speech_text="Hello world", use_ssml=True)
    assert resp["response"]["outputSpeech"]["type"] == "SSML"
    assert "<speak>Hello world</speak>" in resp["response"]["outputSpeech"]["ssml"]


def test_validate_cert_url_valid():
    valid_url = "https://s3.amazonaws.com/echo.api/echo-api-cert.pem"
    assert validate_cert_url(valid_url)


def test_validate_cert_url_invalid():
    assert not validate_cert_url("http://s3.amazonaws.com/echo.api/cert.pem")  # non-https
    assert not validate_cert_url("https://malicious.com/echo.api/cert.pem")     # wrong host
    assert not validate_cert_url("https://s3.amazonaws.com/other/cert.pem")     # wrong path


def test_alexa_launch_request():
    payload = {
        "version": "1.0",
        "session": {"sessionId": "s_123", "user": {"userId": "u_123"}},
        "request": {"type": "LaunchRequest"},
    }
    resp = handle_alexa_request(payload)
    assert "Jarvis" in resp["response"]["outputSpeech"]["text"]
    assert not resp["response"]["shouldEndSession"]


def test_alexa_stop_intent():
    payload = {
        "version": "1.0",
        "session": {"sessionId": "s_123", "user": {"userId": "u_123"}},
        "request": {
            "type": "IntentRequest",
            "intent": {"name": "AMAZON.StopIntent"},
        },
    }
    resp = handle_alexa_request(payload)
    assert resp["response"]["shouldEndSession"]
    assert "Goodbye" in resp["response"]["outputSpeech"]["text"]
