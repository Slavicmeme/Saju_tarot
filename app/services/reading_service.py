from uuid import uuid4
from datetime import datetime, timedelta, timezone
from app.repositories.tarot_repository import get_card
from app.repositories.result_repository import save_result
from app.services.knowledge_loader import load_card_knowledge
from app.services.saju_service import calculate_saju
from app.services.prompt_builder import build_prompt
from app.services.llm_service import generate
from app.services.tarot_meanings import meaning_for
from app.services.tarot_draw_service import SPREAD_DETAILS
from app.services.spread_analysis import analyze_spread
import logging
import json
import httpx

KST = timezone(timedelta(hours=9))
logger = logging.getLogger("saju_tarot.reading")

def classify_llm_error(error: Exception) -> dict:
    if isinstance(error, httpx.TimeoutException):
        return {"code": "timeout", "message": "AI가 제한 시간 안에 응답을 마치지 못해 보조 해석으로 전환했습니다."}
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return {"code": f"api_http_{status}", "message": f"AI API가 HTTP {status} 오류를 반환해 보조 해석으로 전환했습니다."}
    if isinstance(error, json.JSONDecodeError):
        return {"code": "invalid_json", "message": "AI 응답이 완전한 JSON 형식이 아니어서 보조 해석으로 전환했습니다."}
    if isinstance(error, ValueError):
        return {"code": "missing_fields", "message": "AI 응답에서 필수 해석 항목이 누락되어 보조 해석으로 전환했습니다."}
    return {"code": type(error).__name__.lower(), "message": "AI 해석 처리 중 오류가 발생해 보조 해석으로 전환했습니다."}

def fallback_reading(request, saju, cards):
    names = [f"{c['name_ko']}({'정방향' if c['orientation']=='upright' else '역방향'})" for c in cards]
    keywords = [keyword for c in cards for keyword in c["keywords"][:2]]
    card_readings = [{"position":c["position"], "card_name":c["name_ko"], "orientation":c["orientation"],
        "interpretation":f"{c['position']} 자리의 {c['name_ko']}은(는) {c['meaning']['core']}을 말합니다. {c['meaning']['category_lens']}의 관점에서 실제 행동과 대화를 확인하세요.",
        "evidence":c["meaning"]["orientation_note"]} for c in cards]
    pattern = analyze_spread(cards, saju)
    return {"title": f"{request.category or '종합'} 흐름 리딩", "one_line_summary": f"{len(cards)}장의 관계와 사주의 장기 흐름을 함께 읽어 핵심 패턴을 정리했습니다.",
        "direct_answer": "지금은 단정적인 결론보다 조건을 확인하며 단계적으로 움직이는 편이 좋습니다.", "saju_summary": saju["summary"],
        "tarot_summary": f"{SPREAD_DETAILS.get(request.spread_type,{}).get('name','심층')} 배열에서 {', '.join(names)}이 나왔습니다. 각 카드를 따로 단정하지 않고 원인, 내외부 변수, 행동, 조건부 결과의 관계로 읽습니다.",
        "card_readings":card_readings,
        "spread_flow":" → ".join(f"{card['position']}에서는 {card['meaning']['core']}" for card in cards) + "로 이어집니다. 마지막 자리는 확정된 미래가 아니라 앞선 조건과 행동이 유지될 때의 방향입니다.",
        "saju_tarot_agreement":"사주의 장기 성향과 카드의 현재 메시지가 만나는 지점은 준비 수준과 실행 속도를 조절하는 태도입니다.",
        "conflict_tension":"사주는 구조적 가능성을, 카드는 현재 선택에 따른 가변적 결과를 보여주므로 시간축을 구분해야 합니다.",
        "dominant_patterns":f"메이저 카드 {pattern['major_count']}장, 정방향 {pattern['upright_count']}장, 역방향 {pattern['reversed_count']}장입니다. 중심 영역은 {pattern['dominant_suit']}입니다.",
        "card_combinations":[{"cards":f"{cards[i]['name_ko']} → {cards[i+1]['name_ko']}", "interpretation":f"{cards[i]['position']}의 조건이 {cards[i+1]['position']}에 어떤 영향을 주는지 함께 확인해야 합니다."} for i in range(min(len(cards)-1, 4))],
        "saju_overlay":pattern["saju_resonance"],
        "scenario_paths":{"current_path":"현재 행동과 조건이 유지될 때 마지막 자리의 경향이 강화될 수 있습니다.", "adjusted_path":"조언과 보완 행동을 적용하면 역방향의 막힘을 완화하고 다른 선택지를 만들 수 있습니다."},
        "fusion_interpretation": f"사주의 구조적 경향과 타로의 단기 신호를 함께 보면, {', '.join(keywords[:4])}을 현실 조건과 대조하는 과정이 중요합니다.",
        "positive_factors": keywords[:3] or ["상황을 재점검할 기회"], "risk_factors": ["결과를 확정된 미래로 받아들이는 태도", "충분한 정보 없이 서두르는 결정"],
        "recommended_actions": ["이번 주에 확인 가능한 사실을 세 가지 적어보기", "중요 결정은 비용과 대안을 비교한 뒤 실행하기", "신뢰할 수 있는 사람의 의견을 함께 듣기"],
        "timing": f"{request.target_year}년 {request.target_month}월을 기준으로 단기 변화와 장기 계획을 구분해 살펴보세요.",
        "final_message": "운세는 방향을 비추는 질문입니다. 선택의 근거는 현실에서 하나씩 확인해 주세요.",
        "disclaimer": "본 결과는 오락 및 자기성찰을 위한 참고 자료이며, 의료·법률·재정 등 중요한 결정은 전문가와 상담하세요."}

async def create_reading(request):
    saju = calculate_saju(request.profile, request.target_year, request.target_month)
    cards = []
    for selected in request.cards:
        meta = get_card(selected.card_id)
        context = load_card_knowledge(selected.card_id, selected.orientation)
        cards.append({**selected.model_dump(), "name_ko": meta["name_ko"], "name_en": meta["name_en"], "arcana": meta["arcana"], "image_url": meta["image_url"],
                      "keywords": meta["keywords"][selected.orientation], "meaning": meaning_for(selected.card_id, selected.orientation, request.category), "context": context})
    pattern_analysis = analyze_spread(cards, saju)
    system, prompt = build_prompt(request, saju, cards, pattern_analysis)
    llm_diagnostic = None
    try:
        reading = await generate(system, prompt) or fallback_reading(request, saju, cards)
        mode = "llm" if get_llm_enabled() else "fallback"
        if mode == "fallback":
            llm_diagnostic = {"code": "not_configured", "message": "LLM API 키가 설정되지 않아 보조 해석을 사용했습니다."}
    except Exception as error:
        llm_diagnostic = classify_llm_error(error)
        logger.warning("LLM generation failed; using fallback error_type=%s diagnostic_code=%s", type(error).__name__, llm_diagnostic["code"])
        reading, mode = fallback_reading(request, saju, cards), "fallback_after_llm_error"
    result_id = str(uuid4())
    payload = {"result_id": result_id, "created_at": datetime.now(KST).isoformat(), "input": request.model_dump(mode="json"),
               "saju_result": saju, "cards": [{k: v for k, v in c.items() if k != "context"} for c in cards], "reading": reading,
               "mode": mode, "llm_diagnostic": llm_diagnostic}
    save_result(result_id, payload)
    return payload

def get_llm_enabled():
    from app.config import get_settings
    return bool(get_settings().llm_api_key)
