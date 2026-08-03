import json
from functools import lru_cache
from app.config import BASE_DIR

@lru_cache
def get_cards() -> list[dict]:
    return json.loads((BASE_DIR / "data" / "tarot_cards.json").read_text(encoding="utf-8-sig"))

def get_card(card_id: str) -> dict:
    card = next((card for card in get_cards() if card["id"] == card_id), None)
    if not card:
        raise KeyError(f"등록되지 않은 카드입니다: {card_id}")
    return card
