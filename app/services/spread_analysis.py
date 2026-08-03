from collections import Counter

SUIT_LABELS = {"wands":"완드(행동·열정)", "cups":"컵(감정·관계)", "swords":"소드(생각·갈등)", "pentacles":"펜타클(일·돈·현실)"}
SUIT_ELEMENTS = {"wands":"fire", "cups":"water", "swords":"metal", "pentacles":"earth"}
ELEMENT_LABELS = {"wood":"성장과 시작", "fire":"표현과 추진", "earth":"안정과 유지", "metal":"판단과 정리", "water":"관찰과 유연함"}

def analyze_spread(cards: list[dict], saju: dict | None = None) -> dict:
    suits = Counter(card["arcana"] for card in cards if card["arcana"] != "major")
    orientations = Counter(card["orientation"] for card in cards)
    major_cards = [card["name_ko"] for card in cards if card["arcana"] == "major"]
    dominant_suit = suits.most_common(1)[0][0] if suits else None
    card_element = SUIT_ELEMENTS.get(dominant_suit)
    if not saju:
        resonance = "타로만 보기에서는 사주와의 결합 없이 카드의 자리와 조합만 해석합니다."
    else:
        saju_elements = saju["five_elements"]
        strong_element = max(saju_elements, key=saju_elements.get)
        weak_element = min(saju_elements, key=saju_elements.get)
    if saju and card_element == strong_element:
        resonance = f"카드에서도 {ELEMENT_LABELS[card_element]} 주제가 반복되어 타고난 강점이 현재 상황에서 강하게 작동합니다. 과해지지 않도록 속도를 조절해야 합니다."
    elif saju and card_element == weak_element:
        resonance = f"카드는 지금 {ELEMENT_LABELS[card_element]}을 요구합니다. 평소 자연스럽지 않을 수 있지만 이번 질문에서는 의식적으로 보완할 핵심 행동입니다."
    elif saju and card_element:
        resonance = f"카드의 중심 주제인 {ELEMENT_LABELS[card_element]}이 사주의 장기 성향에 새로운 현실 변수를 더합니다."
    elif saju:
        resonance = "큰 전환을 뜻하는 메이저 카드가 중심이어서 일시적 기분보다 삶의 방향과 태도를 함께 살펴야 합니다."
    return {
        "card_count": len(cards), "major_count": len(major_cards), "major_cards": major_cards,
        "suit_counts": {SUIT_LABELS[key]: value for key, value in suits.items()},
        "dominant_suit": SUIT_LABELS.get(dominant_suit, "메이저 아르카나"),
        "upright_count": orientations["upright"], "reversed_count": orientations["reversed"],
        "saju_resonance": resonance,
        "reading_instruction": "개별 뜻을 나열하지 말고 서로 마주 보는 자리, 원인→행동→결과, 반복 슈트, 메이저 카드와 역방향의 집중 구간을 우선 분석한다.",
    }
