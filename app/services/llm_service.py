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
