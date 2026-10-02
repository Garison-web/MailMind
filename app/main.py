import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from app.models import EmailInput, AnalysisResult
from app.services.preprocess import clean_email
from app.services.demo_analyzer import analyze_demo
from app.services.llm import analyze_with_llm
from app.services import gmail

load_dotenv()
ROOT = Path(__file__).parent
app = FastAPI(title="MailMind API", version="1.0.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "mailmind-development-only-change-this"),
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


def remember_gmail_state(request: Request, state: str) -> None:
    request.session["gmail_oauth_states"] = [state]


def consume_gmail_state(request: Request, state: str) -> bool:
    states = request.session.get("gmail_oauth_states", [])
    if not isinstance(states, list):
        states = []
    if not states or states[-1] != state:
        return False
    request.session["gmail_oauth_states"] = []
    return True

@app.get("/")
def home(): return FileResponse(ROOT / "static" / "index.html")

@app.get("/api/samples")
def samples():
    return json.loads((ROOT.parent / "sample_data" / "emails.json").read_text(encoding="utf-8"))

@app.get("/api/gmail/status")
def gmail_status():
    return {"configured": gmail.is_configured(), "connected": gmail.is_connected()}

@app.get("/auth/gmail/connect")
def gmail_connect(request: Request):
    try:
        url, state, code_verifier = gmail.authorization_url()
        request.session["gmail_oauth_state"] = state
        request.session["gmail_oauth_code_verifier"] = code_verifier
        return RedirectResponse(url)
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.get("/auth/gmail/callback")
def gmail_callback(request: Request, code: str, state: str | None = None):
    if state and state != request.session.get("gmail_oauth_state"):
        raise HTTPException(400, "Gmail sign-in state did not match. Please try again.")
    code_verifier = request.session.get("gmail_oauth_code_verifier")
    try:
        gmail.save_authorization(code, state or "", code_verifier)
        request.session.pop("gmail_oauth_state", None)
        request.session.pop("gmail_oauth_code_verifier", None)
        return RedirectResponse("/?gmail=connected")
    except Exception as exc:
        raise HTTPException(400, "Gmail connection could not be completed. Please try again.") from exc

@app.get("/api/gmail/emails")
def gmail_emails(limit: int = 5):
    try:
        return gmail.recent_messages(max(1, min(limit, 10)))
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "MailMind could not read your inbox. Please reconnect Gmail.") from exc

@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(payload: EmailInput):
    try:
        email = clean_email(payload.subject, payload.body)
        if len(email["body"]) < 8: raise HTTPException(422, "Please enter a fuller email message.")
        return analyze_with_llm(email) or analyze_demo(email)
    except HTTPException: raise
    except Exception as exc: raise HTTPException(500, "MailMind could not analyze this email. Please try again.") from exc
