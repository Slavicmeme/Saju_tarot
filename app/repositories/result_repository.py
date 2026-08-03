import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.config import BASE_DIR, get_settings

RESULT_DIR = BASE_DIR / "data" / "results"
KST = timezone(timedelta(hours=9))

def save_result(result_id: str, payload: dict) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / f"{result_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def get_result(result_id: str) -> dict:
    if not result_id.replace("-", "").isalnum():
        raise KeyError(result_id)
    path = RESULT_DIR / f"{result_id}.json"
    if not path.is_file():
        raise KeyError(result_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    created = datetime.fromisoformat(data["created_at"])
    if datetime.now(KST) - created > timedelta(hours=get_settings().result_ttl_hours):
        raise KeyError(result_id)
    return data