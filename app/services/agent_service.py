from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.repositories.agent_session_repository import save_session
from app.repositories.tarot_repository import get_card
from app.schemas.models import Profile, SelectedCard
from app.services.llm_service import generate_agent_turn, generate_agent_followup
from app.services.saju_service import calculate_saju
from app.services.tarot_draw_service import CATEGORY_SPREADS, SPREADS, SPREAD_DETAILS
from app.services.tarot_meanings import meaning_for

KST = timezone(timedelta(hours=9))
CATEGORY_LABELS = {"general":"종합운", "love":"연애·관계", "career":"직장·이직", "business":"사업·재물", "study":"학업", "decision":"선택·의사결정"}
CATEGORY_WORDS = {
    "general": ("종합운", "전체운", "전반적인 흐름"),
    "love": ("연애", "재회", "헤어", "남자친구", "여자친구", "상대", "관계", "연락", "마음"),
    "career": ("직장", "이직", "취업", "회사", "상사", "진로", "승진"),
    "business": ("사업", "재물", "돈", "매출", "투자", "창업"),
    "study": ("학업", "시험", "공부", "합격", "학교"),
    "decision": ("선택", "결정", "고민", "할까", "말까", "A", "B"),
}
HIGH_STAKES = ("진단", "약", "수술", "소송", "법률", "주식", "코인", "수익", "대출")
SUPPLEMENT_WORDS = ("언제", "시기", "연락", "속마음", "추가", "좀 더", "구체적", "어떻게")

def _message(role: str, text: str, kind: str = "text", **extra) -> dict:
    return {"id":str(uuid4()), "role":role, "text":text, "kind":kind, "created_at":datetime.now(KST).isoformat(), **extra}

def create_agent_session(ai_consent: bool) -> dict:
    now = datetime.now(KST)
    session = {"session_id":str(uuid4()), "created_at":now.isoformat(), "updated_at":now.isoformat(), "expires_at":(now+timedelta(hours=24)).isoformat(), "ai_consent":ai_consent,
               "category":None, "topic":None, "memory_summary":"", "topic_message_start":0, "messages":[_message("assistant", "안녕. 요즘 어떤 일이 마음에 걸려요? 편하게 말해 봐요.")], "cards":[], "saju":None, "profile":None, "pending_draw":None, "active_spread":None, "draw_count":0}
    save_session(session)
    return session

def classify_category(text: str) -> str:
    scores = {category:sum(word.lower() in text.lower() for word in words) for category, words in CATEGORY_WORDS.items()}
    return max(scores, key=scores.get) if max(scores.values(), default=0) else "general"

async def handle_user_message(session: dict, text: str) -> dict:
    if not session.get("ai_consent"):
        raise RuntimeError("이전 규칙 기반 세션입니다. 새 LLM Agent 세션을 시작해 주세요.")
    user_entry = _message("user", text)
    session["messages"].append(user_entry)
    if session.get("pending_draw"):
        session["pending_draw"] = None
        save_session(session)
    try:
        current_history = session["messages"][session.get("topic_message_start", 0):]
        decision = await generate_agent_turn(current_history, session["cards"], session.get("saju"), text, session.get("category"), session.get("memory_summary", ""))
    except Exception as error:
        session["messages"] = [item for item in session["messages"] if item["id"] != user_entry["id"]]
        save_session(session)
        raise RuntimeError("LLM이 답변하지 못했습니다. API 설정과 연결 상태를 확인한 뒤 다시 보내 주세요.") from error
    valid_categories = set(CATEGORY_LABELS)
    category = decision.get("category") if decision.get("category") in valid_categories else (session.get("category") or "general")
    topic_changed = bool(decision.get("topic_changed") and session.get("category") and category != session["category"])
    if topic_changed:
        session.update({"cards":[], "pending_draw":None, "active_spread":None, "draw_count":0})
        session["topic_message_start"] = len(session["messages"]) - 1
    session["category"] = category
    session["memory_summary"] = str(decision.get("memory_summary") or session.get("memory_summary", ""))[:500]
    session["topic"] = text[:120] if topic_changed or not session.get("topic") else session["topic"]
    action = decision.get("action", "answer")
    kind, extra = ("topic_changed" if topic_changed else "text"), {}
    if action == "request_saju" and not session.get("saju"):
        kind = "request_saju"
    elif action == "offer_draw":
        count = 1 if decision.get("draw_count") == 1 else 2
        positions = [str(item)[:40] for item in decision.get("positions", []) if str(item).strip()][:count]
        while len(positions) < count:
            positions.append("지금 확인할 핵심" if not positions else "다음 행동의 조언")
        spread_type = "one_card" if count == 1 else "supplement_two"
        session["pending_draw"] = {"proposal_id":str(uuid4()), "kind":"llm", "spread_type":spread_type, "count":count, "positions":positions}
        kind, extra = "offer_draw", {"draw":session["pending_draw"]}
    session["messages"].append(_message("assistant", str(decision.get("reply") or "조금 더 이야기해 주세요."), kind, **extra))
    save_session(session)
    return session

def confirm_draw(session: dict, kind: str, count: int | None, proposal_id: str | None = None) -> dict:
    if not session.get("pending_draw"):
        raise ValueError("LLM이 제안한 카드가 없습니다.")
    if not proposal_id or proposal_id != session["pending_draw"].get("proposal_id"):
        raise ValueError("이미 사용했거나 만료된 카드 제안입니다.")
    return session

async def submit_agent_cards(session: dict, selected: list[SelectedCard]) -> dict:
    pending = session.get("pending_draw")
    if not pending or len(selected) != pending["count"] or len({c.card_id for c in selected}) != len(selected):
        raise ValueError("요청한 배열과 카드 수가 일치하지 않습니다.")
    if any(c.card_id in {old["card_id"] for old in session["cards"]} for c in selected):
        raise ValueError("이 상담에서 이미 사용한 카드는 다시 선택할 수 없습니다.")
    current_messages = session["messages"][session.get("topic_message_start", 0):]
    history = "\n".join(item["text"] for item in current_messages if item["role"] == "user")[-1500:]
    added = []
    for card in selected:
        meta = get_card(card.card_id)
        added.append({"position":card.position, "card_id":card.card_id, "name_ko":meta["name_ko"], "name_en":meta["name_en"], "orientation":card.orientation,
                      "image_url":meta["image_url"], "keywords":meta["keywords"][card.orientation],
                      "meaning":meaning_for(card.card_id, card.orientation, session.get("category") or "general")})
    all_cards = session["cards"] + added
    try:
        current_history = session["messages"][session.get("topic_message_start", 0):]
        followup = await generate_agent_followup(current_history, all_cards, session.get("saju"), {"new_cards":added, "current_situation":history}, session.get("memory_summary", ""))
    except Exception as error:
        raise RuntimeError("카드 결과를 받았지만 LLM 후속 해석에 실패했습니다. 잠시 후 다시 시도해 주세요.") from error
    session["cards"] = all_cards; session["draw_count"] += 1; session["pending_draw"] = None
    session["memory_summary"] = str(followup.get("memory_summary") or session.get("memory_summary", ""))[:500]
    offer_more = bool(followup.get("offer_more"))
    if offer_more:
        count = 1 if followup.get("draw_count") == 1 else 2
        positions = [str(item)[:40] for item in followup.get("positions", []) if str(item).strip()][:count]
        while len(positions) < count:
            positions.append("추가로 확인할 핵심")
        session["pending_draw"] = {"proposal_id":str(uuid4()), "kind":"llm_followup", "spread_type":"one_card" if count == 1 else "supplement_two", "count":count, "positions":positions}
    text = f"{followup.get('summary') or '선택한 카드의 흐름을 확인했어요.'}\n\n{followup.get('reply') or '이 결과에서 가장 마음에 걸리는 부분을 말해 주세요.'}"
    session["messages"].append(_message("assistant", text, "card_reading", cards=added, offer_more=offer_more, draw=session.get("pending_draw")))
    save_session(session)
    return session

def connect_saju(session: dict, profile: Profile, target_year: int, target_month: int) -> dict:
    if session.get("saju"):
        raise ValueError("이 세션에는 이미 사주가 연결되어 있습니다.")
    session["profile"] = profile.model_dump(mode="json")
    session["saju"] = calculate_saju(profile, target_year, target_month)
    session["messages"].append(_message("assistant", f"사주를 한 번 계산해 이 상담에 연결했습니다. {session['saju']['summary']} 앞으로 추가 타로를 볼 때 이 장기 성향을 함께 참고할게요.", "saju_connected"))
    save_session(session)
    return session

def reset_topic(session: dict) -> dict:
    session.update({"category":None, "topic":None, "memory_summary":"", "cards":[], "pending_draw":None, "active_spread":None, "draw_count":0})
    session["topic_message_start"] = len(session["messages"])
    session["messages"].append(_message("assistant", "새 주제로 전환했습니다. 연결된 사주는 그대로 참고하고, 이전 타로 카드는 새 질문에 사용하지 않을게요. 새 이야기를 들려주세요.", "new_topic"))
    save_session(session)
    return session
