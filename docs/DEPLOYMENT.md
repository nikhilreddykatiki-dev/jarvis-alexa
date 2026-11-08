# Zero-Cost Hosting & Deployment Options for JARVIS

Alexa requires an **HTTPS endpoint** with a valid SSL certificate. Here is an evaluation of completely free hosting options.

---

## Free Option Comparison

| Provider | Free Quota | Cold Starts | HTTPS / Custom Cert | Persistence | Best For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AWS Lambda** | 1M free requests/month (Always Free) | ~1-2s cold | Automatic with Function URL or API Gateway | Stateless (needs remote DB or S3 for memory) | Production AWS integration |
| **Cloudflare Tunnel (Local PC)** | Completely Free & Unlimited | **0 ms** (runs locally on PC) | Automatic free valid HTTPS domain | Full SQLite on PC | Best zero-cost development & testing |
| **Render** | 750 free instance hrs/month | Spindown after 15m inactivity (~40s delay) | Automatic free HTTPS | Ephemeral disk on free tier | Lightweight cloud testing |

---

## Recommended Free Development Setup: Cloudflare Tunnel (or ngrok)
Since your PC is already running the SQLite database and Python backend:
1. Run local JARVIS server:
   ```powershell
   uvicorn backend.app.main:app --port 8000
   ```
2. In a separate terminal, expose port 8000 using Cloudflare Tunnel (100% free, no account needed):
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
   (Or using free ngrok: `ngrok http 8000`)
3. Copy the resulting `https://*.trycloudflare.com` URL into Alexa Developer Console:
   `https://<your-subdomain>.trycloudflare.com/api/alexa`

---

## AWS Lambda Free Tier Deployment
To run serverless 24/7 on AWS without keeping your PC awake:
1. Use `mangum` adapter for ASGI/FastAPI:
   ```python
   from mangum import Mangum
   from backend.app.main import app
   handler = Mangum(app)
   ```
2. Free tier covers 1,000,000 requests/month and 3.2M seconds of compute time per month permanently under AWS Free Tier.
