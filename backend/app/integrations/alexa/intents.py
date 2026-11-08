"""Alexa Skill Intent and Response Helpers."""

from typing import Optional, Any


def build_response(
    speech_text: str,
    reprompt_text: Optional[str] = None,
    should_end_session: bool = False,
    card_title: Optional[str] = None,
    session_attributes: Optional[dict] = None,
    use_ssml: bool = False,
) -> dict:
    """Construct an Alexa skill response object compliant with ASK specification."""
    output_speech: dict[str, Any] = {}
    if use_ssml:
        if not speech_text.startswith("<speak>"):
            speech_text = f"<speak>{speech_text}</speak>"
        output_speech = {"type": "SSML", "ssml": speech_text}
    else:
        output_speech = {"type": "PlainText", "text": speech_text}

    response: dict[str, Any] = {
        "outputSpeech": output_speech,
        "shouldEndSession": should_end_session,
    }

    if card_title:
        response["card"] = {
            "type": "Simple",
            "title": card_title,
            "content": speech_text,
        }

    if reprompt_text:
        reprompt_speech: dict[str, Any] = (
            {"type": "SSML", "ssml": f"<speak>{reprompt_text}</speak>"}
            if use_ssml and not reprompt_text.startswith("<speak>")
            else {"type": "PlainText", "text": reprompt_text}
        )
        response["reprompt"] = {"outputSpeech": reprompt_speech}

    return {
        "version": "1.0",
        "sessionAttributes": session_attributes or {},
        "response": response,
    }
