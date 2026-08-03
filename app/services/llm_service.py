import json
import httpx
from app.config import get_settings

FIELDS = {"title", "one_line_summary", "direct_answer", "saju_summary", "tarot_summary", "card_readings", "spread_flow",
          "saju_tarot_agreement", "conflict_tension", "fusion_interpretation",
          "dominant_patterns", "card_combinations", "saju_overlay", "scenario_paths",
          "positive_factors", "risk_factors", "recommended_actions", "timing", "final_message", "disclaimer"}

async def generate(system: str, user: str) -> dict | None:
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    payload = {"model": settings.llm_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
               "response_format": {"type": "json_object"}, "max_completion_tokens": settings.llm_max_completion_tokens}
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        response = await client.post(f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                                     headers={"Authorization": f"Bearer {settings.llm_api_key}"}, json=payload)
        response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
    if not FIELDS.issubset(parsed):
        raise ValueError("LLM 구조화 응답에 필수 필드가 없습니다.")
    return parsed

async def check_connection() -> dict:
    settings = get_settings()
    if not settings.llm_api_key:
        return {"configured": False, "reachable": False, "model": settings.llm_model, "message": ".env에 LLM_API_KEY가 없습니다."}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.llm_base_url.rstrip('/')}/models",
                                        headers={"Authorization": f"Bearer {settings.llm_api_key}"})
        return {"configured": True, "reachable": response.is_success, "model": settings.llm_model,
                "http_status": response.status_code, "message": "LLM 인증 정상" if response.is_success else "LLM 인증 또는 API 설정 오류"}
    except httpx.HTTPError:
        return {"configured": True, "reachable": False, "model": settings.llm_model, "message": "LLM 서버에 연결할 수 없습니다."}

async def generate_agent_reply(history: list[dict], cards: list[dict], saju: dict | None, message: str) -> str | None:
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    system = """당신은 Magic Tarot의 차분한 한국어 상담 에이전트입니다. 기존 카드가 있으면 카드의 자리와 방향을 근거로 답하고, 사주가 연결되어 있으면 장기 성향과 현재 타로를 구분해 참고하세요. 카드나 사주로 타인의 숨은 사실, 확정된 미래, 질병, 법적 결과, 투자 수익을 단정하지 마세요. 사용자가 원하는 답을 얻기 위한 반복 뽑기를 부추기지 말고 기존 카드를 먼저 활용하세요. 친절하지만 과장 없이 4~8문장으로 답하세요."""
    context = {"recent_history": history[-10:], "cards": cards, "saju": saju, "new_message": message}
    payload = {"model": settings.llm_model, "messages": [{"role":"system","content":system},{"role":"user","content":json.dumps(context, ensure_ascii=False)}], "max_completion_tokens":900}
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        response = await client.post(f"{settings.llm_base_url.rstrip('/')}/chat/completions", headers={"Authorization":f"Bearer {settings.llm_api_key}"}, json=payload)
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()

async def _agent_json(system: str, context: dict, max_tokens: int = 1200) -> dict:
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY가 없어 Agent 채팅을 시작할 수 없습니다.")
    model = settings.agent_llm_model
    payload = {"model":model, "messages":[{"role":"system","content":system},{"role":"user","content":json.dumps(context, ensure_ascii=False)}],
               "response_format":{"type":"json_object"}, "max_completion_tokens":max_tokens}
    if model.startswith("gpt-5"):
        payload["reasoning_effort"] = "low"
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        response = await client.post(f"{settings.llm_base_url.rstrip('/')}/chat/completions", headers={"Authorization":f"Bearer {settings.llm_api_key}"}, json=payload)
        response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])

async def generate_agent_turn(history: list[dict], cards: list[dict], saju: dict | None, message: str, category: str | None, memory_summary: str = "") -> dict:
    system = """당신은 Magic Tarot의 다정한 한국어 대화 상대입니다. 특정 상담 대본을 따르지 말고, 지금까지의 대화 흐름에 맞춰 친구처럼 자연스럽게 반응하세요.

핵심 방식:
- 사용자의 고민을 조사하듯 캐묻지 않습니다.
- 판단에 더 필요한 내용이 생기면 사용자에게 설명을 요구하는 질문 대신, 그 내용을 확인할 카드 1~2장을 제안합니다.
- 카드의 position은 방금 궁금해진 내용을 그대로 구체적인 역할로 만듭니다.
- 사용자가 카드 제안을 누르지 않고 새 메시지를 보내면 그 제안은 건너뛴 것으로 보고 자연스럽게 새 대화를 이어갑니다.
- 이미 공개된 카드로 충분히 답할 수 있으면 새 카드를 제안하지 않고 그 카드와 대화를 바탕으로 답합니다.
- 정해진 전체 배열이나 남은 카드 수는 없습니다. 매 순간 1~2장만 판단합니다.

대화 방식:
- 보통 1~3개의 짧은 문장으로 답합니다.
- 사용자의 말을 구체적으로 받아주고, 방금 말한 내용에 먼저 반응합니다.
- 대화에 꼭 필요하지 않은 후속 질문으로 매번 끝내지 않습니다.
- 선택지, 서비스 사용법, 주의사항, 사주 입력을 반복해서 안내하지 않습니다.
- 카드 제안 시에도 절차를 길게 설명하지 말고 자연스럽게 "이 부분은 카드로 한번 볼게요" 정도로 말합니다. 확인 버튼은 화면이 붙입니다.
- 사용자가 요청하지 않은 사주는 먼저 꺼내지 않습니다. 사용자가 사주를 원하고 아직 연결되지 않았을 때만 request_saju를 선택합니다.
- 기존 카드 의미를 기계적으로 반복하지 말고 현재 메시지에 필요한 부분만 연결합니다.
- 주제가 명확히 달라졌다면 topic_changed를 true로 하되 전환 안내를 장황하게 하지 않습니다.
- 타인의 숨은 사실이나 미래를 확정하지 않고, 의료·법률·투자 같은 고위험 내용만 필요한 한계를 짧게 알립니다.

가벼운 인사에는 자연스럽게 인사할 수 있지만, 상담 내용을 더 알아내기 위한 질문은 카드 제안으로 대신하세요.

반드시 JSON 객체로 답하세요: {"reply":"자연스럽고 짧은 실제 답변", "category":"general|love|career|business|study|decision", "topic_changed":false, "action":"answer|offer_draw|request_saju", "draw_count":1 또는 2, "positions":["지금 카드로 확인할 구체적인 내용"], "memory_summary":"이후 대화에서 기억할 사용자 상황·감정·목표를 250자 이내로 갱신"}. offer_draw가 아니면 positions는 빈 배열입니다."""
    return await _agent_json(system, {"conversation_memory":memory_summary, "recent_history":history[-12:], "existing_cards":cards, "saju":saju, "current_category":category, "new_message":message}, 650)

async def generate_agent_followup(history: list[dict], cards: list[dict], saju: dict | None, reading: dict, memory_summary: str = "") -> dict:
    system = """당신은 고민을 함께 풀어가는 자연스러운 한국어 대화 상대입니다. 방금 공개된 카드를 현재 대화에 붙여 짧게 풀어주세요.
- 카드의 정·역방향과 실제 입력 의미를 정확히 사용합니다.
- 카드 사전 문구나 모호한 교훈을 반복하지 않습니다.
- summary는 지금 카드가 보여준 핵심을 1~2문장으로 씁니다.
- reply는 결과를 현재 대화에 연결하는 1~2문장입니다. 상담을 끝내거나 의례적인 질문을 붙이지 않습니다.
- 결과를 읽다가 새로 확인해야 할 내용이 생겼다면 사용자에게 그 내용을 질문하지 말고, 그 역할의 카드 1~2장을 offer_more로 제안합니다.
- 기존 카드만으로 충분하면 offer_more는 false입니다.
- 미리 정한 전체 배열이나 남은 카드 자리는 없습니다.
- 사주·주의사항·사용법은 필요한 경우가 아니면 말하지 않습니다.
반드시 JSON 객체로 답하세요: {"summary":"현재 고민에 붙인 짧은 카드 요약", "reply":"대화를 자연스럽게 이어가는 짧은 해석", "offer_more":false, "draw_count":1 또는 2, "positions":["새로 카드로 확인할 구체적인 내용"], "memory_summary":"이후 대화에서 기억할 사용자 상황·감정·목표를 250자 이내로 갱신"}."""
    return await _agent_json(system, {"conversation_memory":memory_summary, "recent_history":history[-12:], "all_cards":cards, "saju":saju, "latest_reading":reading}, 900)
