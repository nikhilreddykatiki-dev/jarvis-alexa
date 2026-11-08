"""Alexa Skill Request Handler."""

import logging
from typing import Any
from backend.app.agents.jarvis_agent import JarvisAgent
from backend.app.integrations.alexa.intents import build_response

logger = logging.getLogger(__name__)


def handle_alexa_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Process an incoming Alexa Skill request and return a valid ASK response."""
    request_type = payload.get("request", {}).get("type", "")
    session = payload.get("session", {})
    session_id = session.get("sessionId", "alexa_default_session")
    user_id = session.get("user", {}).get("userId", "alexa_user")
    session_attributes = session.get("attributes", {})

    logger.info(f"Received Alexa request type: {request_type} for session: {session_id}")

    if request_type == "LaunchRequest":
        from backend.app.reminders.manager import ReminderManager
        rem_mgr = ReminderManager(user_id=user_id)
        due = rem_mgr.get_due_reminders()
        if due:
            alerts = ", ".join([r['title'] for r in due])
            speech = f"Hello, I am Jarvis. Alert: you have an active reminder: {alerts}! How can I help you today?"
            for r in due:
                rem_mgr.complete(r["id"])
        else:
            speech = (
                "Hello, I am Jarvis. How can I help you today?"
            )
        reprompt = "You can ask me questions, create reminders, or manage your tasks. What would you like to do?"
        return build_response(
            speech_text=speech,
            reprompt_text=reprompt,
            should_end_session=False,
            card_title="Jarvis Online",
            session_attributes=session_attributes,
        )

    elif request_type == "IntentRequest":
        intent = payload["request"].get("intent", {})
        intent_name = intent.get("name", "")
        logger.info(f"Processing Intent: {intent_name}")

        if intent_name in ("AMAZON.StopIntent", "AMAZON.CancelIntent"):
            return build_response(
                speech_text="Goodbye! Have a great day.",
                should_end_session=True,
                card_title="Jarvis",
            )

        elif intent_name == "AMAZON.HelpIntent":
            help_text = (
                "I am your personal AI assistant powered by Groq. "
                "You can ask me any question, ask me to remember facts, or check your reminders. "
                "What would you like to do?"
            )
            return build_response(
                speech_text=help_text,
                reprompt_text="What can I assist you with?",
                should_end_session=False,
                card_title="Jarvis Help",
                session_attributes=session_attributes,
            )

        elif intent_name == "AMAZON.FallbackIntent":
            fallback_text = "I didn't quite catch that. You can ask me questions, say 'set a timer for 5 minutes', or ask in Tanglish like 'cheppu Chelsea ekkada undi'."
            return build_response(
                speech_text=fallback_text,
                reprompt_text="How can I assist you?",
                should_end_session=False,
                card_title="Jarvis",
                session_attributes=session_attributes,
            )

        # Custom Conversational Intent: AskJarvisIntent or similar
        # Alexa slots usually pass the utterance in a catch-all slot (e.g. 'query' or 'utterance')
        slots = intent.get("slots", {})
        user_query = ""
        for slot in slots.values():
            if slot.get("value"):
                user_query = slot["value"]
                break

        if not user_query:
            return build_response(
                speech_text="I didn't quite catch that. Could you please repeat what you said?",
                reprompt_text="I'm listening, please go ahead.",
                should_end_session=False,
                session_attributes=session_attributes,
            )

        # Extract Alexa System context (device info, api endpoint, and security token)
        system_context = payload.get("context", {}).get("System", {})
        alexa_context = {
            "apiEndpoint": system_context.get("apiEndpoint", "https://api.eu.amazonalexa.com"),
            "apiAccessToken": system_context.get("apiAccessToken", ""),
            "deviceId": system_context.get("device", {}).get("deviceId", ""),
        }

        # Call Jarvis Agent
        agent = JarvisAgent(
            user_id=user_id,
            session_id=session_id,
            is_alexa=True,
            alexa_context=alexa_context,
        )
        response_text = agent.chat(user_query)

        # Check if permission consent card is needed (e.g. for reminders or timers)
        permissions = None
        if alexa_context.get("permission_consent_required"):
            permissions = [
                "alexa::alerts:reminders:skill:readwrite",
                "alexa::alerts:timers:skill:readwrite",
            ]

        return build_response(
            speech_text=response_text,
            reprompt_text="Is there anything else I can do for you?",
            should_end_session=False,
            card_title="Jarvis",
            session_attributes=session_attributes,
            permissions=permissions,
        )

    elif request_type == "SessionEndedRequest":
        reason = payload.get("request", {}).get("reason", "Unknown")
        logger.info(f"Alexa session ended: {reason}")
        return build_response(speech_text="", should_end_session=True)

    else:
        logger.warning(f"Unhandled request type: {request_type}")
        return build_response(
            speech_text="I'm sorry, I didn't recognize that request.",
            should_end_session=True,
        )
