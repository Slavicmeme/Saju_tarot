import random
from app.repositories.tarot_repository import get_cards

SPREADS = {
    "one_card": ["핵심 메시지"],
    "situation_obstacle_advice": ["현재 상황", "방해 요소", "실천 조언"],
    "situation_action_outcome": ["현재 상황", "권장 행동", "예상 결과"],
    "past_present_future": ["과거의 영향", "현재의 핵심", "이어질 흐름"],
    "self_other_relationship": ["나의 입장", "상대의 입장", "관계의 흐름"],
    "five_card": ["현재 상황", "내면 상태", "외부 환경", "조언", "예상 흐름"],
    "celtic_cross": ["현재의 핵심", "가로막는 과제", "문제의 뿌리", "지나온 영향", "의식하는 목표", "가까운 전개", "나의 태도", "주변 환경", "희망과 두려움", "현재 흐름의 결론"],
    "relationship_seven": ["나의 현재 마음", "상대의 현재 마음", "관계의 현재 상태", "내가 바라는 것", "상대에게 필요한 것", "관계의 핵심 과제", "현재 흐름이 이어질 방향"],
    "career_five": ["현재 직업 상황", "통제하기 어려운 외부 변수", "활용할 강점과 자원", "가장 현실적인 행동", "현재대로 갈 때의 전개"],
    "money_five": ["현재 재정·사업 상태", "외부 변수와 제약", "확장 가능한 기회", "위험을 줄일 행동", "현재대로 갈 때의 전개"],
    "study_five": ["현재 학습 상태", "집중을 막는 요인", "활용할 강점과 자원", "효과적인 학습 전략", "현재대로 갈 때의 전개"],
    "decision_five": ["선택 A의 장점", "선택 A의 비용", "선택 B의 장점", "선택 B의 비용", "두 선택을 아우르는 조언"],
}

SPREAD_DETAILS = {
    "situation_obstacle_advice": {"name":"상황 · 장애물 · 조언", "best_for":"종합, 막힌 문제, 원인 파악"},
    "situation_action_outcome": {"name":"상황 · 행동 · 결과", "best_for":"선택, 이직, 의사결정"},
    "past_present_future": {"name":"과거 · 현재 · 미래", "best_for":"전체 흐름과 변화 과정"},
    "self_other_relationship": {"name":"나 · 상대 · 관계", "best_for":"연애, 재회, 인간관계"},
    "celtic_cross": {"name":"켈틱 크로스 10장", "best_for":"종합운과 복잡한 전체 흐름"},
    "relationship_seven": {"name":"관계 심층 배열 7장", "best_for":"연애, 재회, 인간관계"},
    "career_five": {"name":"커리어 배열 5장", "best_for":"직장, 이직, 진로"},
    "money_five": {"name":"재물·사업 배열 5장", "best_for":"사업, 재물, 현실 조건"},
    "study_five": {"name":"학업 배열 5장", "best_for":"학습, 시험, 성장 전략"},
    "decision_five": {"name":"선택 비교 배열 5장", "best_for":"두 선택지와 의사결정"},
}

CATEGORY_SPREADS = {
    "general": "celtic_cross", "love": "relationship_seven", "career": "career_five",
    "business": "money_five", "study": "study_five", "decision": "decision_five",
}

def draw_cards(count: int, spread_type: str, seed: int | None = None) -> list[dict]:
    positions = SPREADS.get(spread_type)
    if not positions or len(positions) != count:
        raise ValueError("지원하지 않거나 카드 수가 맞지 않는 스프레드입니다.")
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    selected = rng.sample(get_cards(), count)
    return [{"position": positions[index], "card_id": card["id"], "name_ko": card["name_ko"],
             "name_en": card["name_en"], "orientation": rng.choice(["upright", "reversed"]),
             "image_url": card["image_url"]} for index, card in enumerate(selected)]
