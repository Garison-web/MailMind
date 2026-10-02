"""Local, read-only Gmail OAuth and inbox retrieval helpers."""
import base64
import hashlib
import os
import secrets
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
PROJECT_ROOT = Path(__file__).parents[2]
SECRETS_DIR = PROJECT_ROOT / "secrets"
TOKEN_PATH = SECRETS_DIR / "gmail_token.json"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8000/auth/gmail/callback"


def redirect_uri() -> str:
    base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return f"{base_url}/auth/gmail/callback"


def credential_file() -> Path | None:
    """Allow the Windows download extension as well as the intended filename."""
    matches = list(SECRETS_DIR.glob("gmail_client_secret*.json"))
    return matches[0] if matches else None


def is_configured() -> bool:
    return credential_file() is not None


def get_flow(state: str | None = None) -> Flow:
    path = credential_file()
    if not path:
        raise FileNotFoundError("Gmail OAuth client credentials were not found in secrets/.")
    return Flow.from_client_secrets_file(str(path), scopes=SCOPES, state=state, redirect_uri=redirect_uri())


def authorization_url() -> tuple[str, str, str]:
    flow = get_flow()
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account consent",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return auth_url, state, code_verifier


def save_authorization(code: str, state: str, code_verifier: str | None = None) -> None:
    flow = get_flow(state)
    flow.fetch_token(code=code, code_verifier=code_verifier)
    TOKEN_PATH.write_text(flow.credentials.to_json(), encoding="utf-8")


def is_connected() -> bool:
    return TOKEN_PATH.exists()


def _service():
    if not TOKEN_PATH.exists():
        raise PermissionError("Connect Gmail before fetching inbox messages.")
    credentials = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")
    if not credentials.valid:
        raise PermissionError("Your Gmail connection expired. Please connect Gmail again.")
    return build("gmail", "v1", credentials=credentials)


def _text_part(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        raw = payload["body"]["data"]
        return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        text = _text_part(part)
        if text:
            return text
    return ""


def recent_messages(limit: int = 5) -> list[dict]:
    service = _service()
    listing = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=limit).execute()
    emails = []
    for item in listing.get("messages", []):
        message = service.users().messages().get(userId="me", id=item["id"], format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
        body = _text_part(message.get("payload", {})) or message.get("snippet", "")
        emails.append({
            "id": message["id"], "subject": headers.get("subject", "(No subject)"),
            "sender": headers.get("from", "Unknown sender"),
            "date": headers.get("date", ""), "body": body[:10000],
        })
    return emails
