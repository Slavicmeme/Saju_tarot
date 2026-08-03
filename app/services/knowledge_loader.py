from app.config import BASE_DIR
from app.repositories.tarot_repository import get_card

VALID_ORIENTATIONS = {"upright", "reversed"}

def load_card_knowledge(card_id: str, orientation: str, max_chars: int = 5000) -> str:
    get_card(card_id)
    if orientation not in VALID_ORIENTATIONS:
        raise ValueError("방향은 upright 또는 reversed여야 합니다.")
    path = BASE_DIR / "knowledge" / "tarot" / card_id / f"{orientation}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"카드 지식 파일이 없습니다: {card_id}/{orientation}")
    return path.read_text(encoding="utf-8")[:max_chars]

def load_fusion_rules() -> str:
    directory = BASE_DIR / "knowledge" / "fusion"
    return "\n\n".join(path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.txt")))

