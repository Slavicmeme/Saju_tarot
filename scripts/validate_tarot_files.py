import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
cards=json.loads((ROOT/"data"/"tarot_cards.json").read_text(encoding="utf-8-sig"))
assert len(cards)==78 and len({c["id"] for c in cards})==78
for card in cards:
    for orientation in ("upright","reversed"):
        path=ROOT/"knowledge"/"tarot"/card["id"]/f"{orientation}.txt"
        assert path.is_file() and f"[ORIENTATION]\n{orientation}" in path.read_text(encoding="utf-8")
print("OK: 78 cards, 156 UTF-8 knowledge files")
