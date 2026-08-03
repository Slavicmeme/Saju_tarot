import json
from app.config import BASE_DIR
from app.services.knowledge_loader import load_fusion_rules

def build_prompt(request, saju: dict, card_contexts: list[dict], pattern_analysis: dict) -> tuple[str, str]:
    system = (BASE_DIR / "prompts" / "system.md").read_text(encoding="utf-8")
    schema = (BASE_DIR / "prompts" / "output_schema.md").read_text(encoding="utf-8")
    safe_input = {"question": request.question, "category": request.category, "current_situation": request.current_situation,
                  "target_year": request.target_year, "target_month": request.target_month}
    user = f"""다음 자료를 근거로 융합 상담 결과를 작성하세요.
<USER_INPUT>\n{json.dumps(safe_input, ensure_ascii=False)}\n</USER_INPUT>
[사주 계산 결과]\n{json.dumps(saju, ensure_ascii=False)}
[선택한 스프레드]\n{request.spread_type}
[타로 카드와 자리]\n{json.dumps(card_contexts, ensure_ascii=False)}
[배열 전체의 객관적 패턴]\n{json.dumps(pattern_analysis, ensure_ascii=False)}
[융합 규칙]\n{load_fusion_rules()}
[출력 형식]\n{schema}
상담 카테고리 밖의 건강·질병·신체 증상은 언급하지 마세요. 카드별 해석은 자리의 역할을 중심으로 각 3문장 이상 쓰되 사전 뜻을 반복하지 마세요. 서로 직접 연결되는 카드 조합을 최소 3개 분석하고, 반복 슈트·메이저 비중·역방향 집중·사주와의 공명 또는 긴장을 설명하세요. 현재 패턴을 유지할 때와 행동을 조정할 때의 두 시나리오를 구분하세요. 전체 흐름과 융합 해석은 각 7문장 이상 작성하세요. 반드시 JSON 객체 하나만 반환하세요."""
    return system, user
