import re


def clean_email(subject: str, body: str) -> dict:
    """Normalize email content before sending it to an analyzer."""
    subject = re.sub(r"\s+", " ", subject).strip()
    body = re.sub(r"\r\n?", "\n", body)
    body = re.sub(r"[ \t]+", " ", body).strip()
    return {"subject": subject, "body": body, "combined": f"Subject: {subject}\n\n{body}"}
