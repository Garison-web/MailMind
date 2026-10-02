# MailMind

**MailMind** is an explainable AI email triage and response assistant built for a live classroom demo. Paste an email, analyze it, and get structured intent, priority, urgency, extracted information, a transparent explanation, and a reply draft.

## Features

- Polished responsive dashboard with a sample-email picker and editable drafts
- Intent, category, priority, urgency and response-required classification
- People, organizations, dates, times, action items, and deadline extraction
- Plain-language explanation of the priority decision
- Concise email summary and editable reply draft
- Optional Gemini structured-output analysis; deterministic local fallback for offline demos
- API docs at `/docs`

## Architecture

```text
Browser UI → FastAPI API → preprocessing → LLM / demo analyzer → validated JSON → UI
```

## Run it

1. Copy `.env.example` to `.env`, then add `GEMINI_API_KEY` and a long random `SESSION_SECRET`.
2. Create and activate a virtual environment.
3. Install packages: `pip install -r requirements.txt`
4. Start: `uvicorn app.main:app --reload`
5. Open `http://127.0.0.1:8000`.

Without a key, the app automatically uses **Demo Intelligence**, which is intentional: it makes the presentation stable without internet access. With a Gemini key, it sends the prompt and cleaned email to Gemini, requests a Pydantic-backed JSON schema, validates the result, and only then displays it. If the provider is unavailable, the local analyzer keeps the demo working.

## Presentation flow (90 seconds)

1. Select **Interview confirmation** from the sample menu.
2. Click **Analyze email** and point out the high-priority and deadline badges.
3. Show extracted details, then the “Why this matters” explanation.
4. Edit or copy the generated response.
5. Mention the architecture: preprocessing prepares clean text; the LLM returns a strict JSON contract; the UI renders it clearly.

## Project layout

- `app/main.py` — API and static site host
- `app/services/` — preprocessing, demo intelligence, optional LLM client
- `app/prompts/triage_prompt.txt` — versioned LLM instructions
- `app/static/` — responsive frontend
- `sample_data/emails.json` — demo fixtures

## API

`POST /api/analyze`

```json
{ "subject": "Interview Confirmation", "body": "Please confirm by 6 PM today." }
```

`GET /api/samples` returns presentation samples. API errors are returned as clear JSON messages, and the browser retains the user’s draft.

## Configuration and security

- `GEMINI_API_KEY` is read only from `.env`; it is never embedded in the frontend or committed.
- `SESSION_SECRET` secures local Gmail OAuth session state. Replace the development value before sharing or deploying.
- Gmail OAuth credentials and tokens belong in `secrets/`, which is ignored by Git. Do not commit client-secret or token files; rotate any credential that was accidentally shared.
