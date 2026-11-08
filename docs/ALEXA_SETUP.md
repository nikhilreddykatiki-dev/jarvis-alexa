# Alexa Skill Setup Guide for JARVIS

Turn your Amazon Echo Dot 5 into JARVIS using the Alexa Developer Console.

---

## 1. Create Alexa Skill
1. Go to [Amazon Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
2. Click **Create Skill**.
3. **Skill Name**: `Jarvis`
4. **Primary Locale**: English (India) or English (US) matching your Echo Dot language.
5. **Model**: Custom.
6. **Hosting**: Provision your own.

---

## 2. Configure Invocation Name
1. In the left navigation, click **Invocations** > **Skill Invocation Name**.
2. Set invocation to: `jarvis`.
3. You will say: *"Alexa, open Jarvis"*.

---

## 3. Configure Interaction Model (Intents & Slots)
1. In **Interaction Model** > **Intents**:
   - Keep built-ins:
     - `AMAZON.CancelIntent`
     - `AMAZON.HelpIntent`
     - `AMAZON.StopIntent`
     - `AMAZON.FallbackIntent`
2. Add Custom Intent:
   - Intent Name: `AskJarvisIntent`
   - Add a slot: `query` of type `AMAZON.SearchQuery`.
   - Add sample utterances:
     - `{query}`
     - `ask jarvis {query}`
     - `tell me {query}`
     - `what is {query}`
3. Click **Save Model** and **Build Model**.

---

## 4. Connect Endpoint
1. In the left navigation, click **Endpoint**.
2. Select **HTTPS**.
3. Default Region: Enter your public HTTPS URL (e.g., using Cloudflare Tunnel or ngrok during local testing, or AWS Lambda URL in production):
   `https://<your-subdomain>/api/alexa`
4. SSL Certificate Type:
   - If using ngrok/Cloudflare or public free cloud: Select *"My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority"*.
5. Click **Save Endpoints**.

---

## 5. Test with Simulator & Echo Dot 5
1. Go to the **Test** tab.
2. Change dropdown from "Off" to **Development**.
3. Type or speak: *"open jarvis"*.
4. Verify response: *"Hello, I am Jarvis. How can I help you today?"*.
5. Once test succeeds in simulator, speak directly to your Echo Dot 5 (ensure it is registered to the same Amazon Developer Account):
   - *"Alexa, open Jarvis"*
