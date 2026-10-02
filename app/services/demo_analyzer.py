import re
from app.models import AnalysisResult


def _unique(items):
    return list(dict.fromkeys(item.strip(" ,.") for item in items if item.strip(" ,.")))


def analyze_demo(email: dict) -> AnalysisResult:
    text = email["combined"]
    lower = text.lower()
    urgent_words = ["today", "tomorrow", "asap", "urgent", "immediately", "by 6", "deadline", "confirm"]
    high_words = ["interview", "offer", "payment", "invoice", "exam", "meeting", "security", "password", "action required"]
    critical_words = ["breach", "compromised", "fraud", "suspended", "service interruption", "legal action", "data loss"]
    is_urgent = any(word in lower for word in urgent_words)
    is_high = any(word in lower for word in high_words)
    is_critical = any(word in lower for word in critical_words)
    priority = "Critical" if is_critical and is_urgent else "High" if is_high and is_urgent else "Medium" if is_high or is_urgent else "Low"
    urgency = "Urgent" if is_urgent else "Normal"

    if any(x in lower for x in ["interview", "internship", "recruit"]):
        intent, category = "Interview confirmation", "Recruitment"
    elif any(x in lower for x in ["invoice", "payment", "refund", "bill"]):
        intent, category = "Payment request", "Finance"
    elif any(x in lower for x in ["meeting", "calendar", "schedule"]):
        intent, category = "Meeting coordination", "Work"
    elif any(x in lower for x in ["password", "security", "verify account"]):
        intent, category = "Security notification", "Security"
    elif any(x in lower for x in ["assignment", "exam", "class", "professor"]):
        intent, category = "Academic update", "Education"
    else:
        intent, category = "General correspondence", "General"

    deadline_match = re.search(r"(?:by|before|due)\s+([^.!\n]+)", text, re.I)
    deadline = deadline_match.group(0).strip(" .") if deadline_match else None
    dates = _unique(re.findall(r"\b(?:today|tomorrow|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b(?:\s*(?:at)?\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)?", text))
    people = _unique(re.findall(r"(?:Dear|Hi|Hello|Regards,?|Thanks,?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text))
    orgs = _unique(re.findall(r"\b(?:at|from|with)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})", text))
    actions = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n", email["body"]):
        if re.search(r"\b(?:please|confirm|reply|submit|review|attend|complete|send)\b", sentence, re.I): actions.append(sentence.strip())
    actions = _unique(actions)[:3]
    response = bool(actions or "reply" in lower or "confirm" in lower)
    reason_bits = []
    if is_critical: reason_bits.append("it signals a potentially severe consequence")
    elif is_high: reason_bits.append(f"it concerns {intent.lower()}")
    if deadline: reason_bits.append(f"it has a clear deadline ({deadline})")
    elif is_urgent: reason_bits.append("it contains time-sensitive language")
    if response: reason_bits.append("it asks you to take action")
    reason = "This is marked " + priority.lower() + " priority because " + ", and ".join(reason_bits or ["it appears informational"]) + "."
    summary = f"{intent}: " + (actions[0] if actions else email["body"].split(".")[0].strip() + ".")
    greeting = people[0] if people else "there"
    reply = f"Hi {greeting},\n\nThank you for the update. I have received your message and will {('complete the requested action' if response else 'keep this in mind')}.\n\nBest regards,\n[Your Name]"
    return AnalysisResult(intent=intent, category=category, priority=priority, urgency=urgency,
        response_required=response, deadline=deadline, people=people, organizations=orgs,
        dates_times=dates, action_items=actions, summary=summary, priority_reason=reason,
        reply_draft=reply, confidence=94 if priority == "Critical" else 91 if priority != "Low" else 82, source="Demo Intelligence")
