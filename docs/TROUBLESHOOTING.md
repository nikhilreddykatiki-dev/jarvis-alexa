# JARVIS Troubleshooting Guide

### 1. `GROQ_API_KEY is not set`
- Ensure `.env` is located inside the `jarvis/` directory.
- Verify that `GROQ_API_KEY` contains no extra quotation marks or spaces.

### 2. `Model not found on Groq`
- Run `python -m scripts.terminal_chat` and type `/models` to view models currently active on your Groq tier.
- Update `GROQ_MODEL` in `.env` to a verified model (e.g., `llama-3.3-70b-versatile` or `meta-llama/llama-4-maverick-17b-128e-instruct`).

### 3. `Alexa endpoint error / 400 Bad Request`
- During development, set `ALEXA_VERIFY_REQUESTS=false` in `.env` if testing with simulated or local tools without Amazon's official certificate chain headers.
- When testing from Alexa Developer Console or physical Echo, set `ALEXA_VERIFY_REQUESTS=true`.

### 4. `Echo Dot says: "There was a problem with the requested skill's response"`
- Check backend terminal logs for any Python exceptions.
- Verify your webhook URL ends with `/api/alexa`.
- Verify your tunnel (e.g. Cloudflare / ngrok) is active and reachable.
