import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.config import BASE_DIR

SESSION_DIR = BASE_DIR / "data" / "agent_sessions"
KST = timezone(timedelta(hours=9))
TTL = timedelta(hours=24)

def cleanup_expired_sessions() -> None:
    if not SESSION_DIR.is_dir():
        return
    now = datetime.now(KST)
    for path in SESSION_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if now - datetime.fromisoformat(data["created_at"]) > TTL:
                path.unlink(missing_ok=True)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue

def save_session(session: dict) -> None:
    cleanup_expired_sessions()
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = datetime.now(KST).isoformat()
    (SESSION_DIR / f"{session['session_id']}.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def get_session(session_id: str) -> dict:
    if not session_id.replace("-", "").isalnum():
        raise KeyError(session_id)
    path = SESSION_DIR / f"{session_id}.json"
    if not path.is_file():
        raise KeyError(session_id)
    session = json.loads(path.read_text(encoding="utf-8"))
    created = datetime.fromisoformat(session["created_at"])
    if datetime.now(KST) - created > TTL:
        path.unlink(missing_ok=True)
        raise KeyError(session_id)
    return session

def delete_session(session_id: str) -> None:
    if not session_id.replace("-", "").isalnum():
        raise KeyError(session_id)
    path = SESSION_DIR / f"{session_id}.json"
    if not path.is_file():
        raise KeyError(session_id)
    path.unlink()
