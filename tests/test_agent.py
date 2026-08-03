import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_agent_llm(monkeypatch):
    import app.services.agent_service as service
    async def turn(history, cards, saju, message, category, memory_summary=""):
        users = [item for item in history if item["role"] == "user"]
        new_category = "career" if "직장" in message or "이직" in message else "love"
        changed = bool(category and new_category != category and new_category == "career")
        if "사주" in message and not saju:
            return {"reply":"사주를 한 번 연결해 이후 대화에서 참고할게요.","category":new_category,"topic_changed":changed,"action":"request_saju","draw_count":1,"positions":[]}
        action = "answer" if "대화" in message else ("offer_draw" if len(users) >= 2 or changed else "answer")
        return {"reply":"이야기를 이해했어요. 현재 감정과 현실 조건을 함께 살펴볼게요.","category":new_category,"topic_changed":changed,
                "action":action,"draw_count":2,"positions":["현재 드러난 핵심", "다음 행동의 기준"] if action == "offer_draw" else [],"memory_summary":"재회 문제를 상담 중"}
    async def followup(history, cards, saju, reading, memory_summary=""):
        return {"summary":"두 카드는 현재 상황과 다음 행동을 구분해서 보여줍니다. 결과를 확정하기보다 현실 반응을 확인하는 것이 중요합니다.",
                "reply":"이 해석에서 가장 마음에 걸리는 부분은 무엇인가요? 기존 카드를 토대로 계속 이야기해 볼게요.",
                "offer_more":True,"draw_count":2,"positions":["추가로 확인할 변수","현실적인 대응"],"memory_summary":"재회 문제와 카드 결과를 상담 중"}
    monkeypatch.setattr(service, "generate_agent_turn", turn)
    monkeypatch.setattr(service, "generate_agent_followup", followup)

def _profile():
    return {"nickname":"상담자","birth_date":"1995-06-10","birth_time":"14:30","time_unknown":False,
            "calendar_type":"solar","gender":"female","birth_place":"서울"}

def _select(card_pool, positions, used=None):
    used = used or set()
    cards = [card for card in card_pool if card["id"] not in used][:len(positions)]
    return [{"position":position,"card_id":card["id"],"orientation":"upright"} for position,card in zip(positions,cards)]

def test_agent_llm_conversation_draw_followup_saju_and_pdf(monkeypatch):
    import app.api.routes as routes
    monkeypatch.setattr(routes, "render_result_pdf", lambda _url: b"%PDF-1.4\nagent")
    session = client.post("/api/agent/sessions", json={"ai_consent":True}).json()
    session_id = session["session_id"]
    first = client.post(f"/api/agent/sessions/{session_id}/messages", json={"message":"헤어진 사람과 재회하고 싶어요."}).json()
    assert first["messages"][-1]["role"] == "assistant"
    assert first["messages"][-1]["kind"] == "text"
    second = client.post(f"/api/agent/sessions/{session_id}/messages", json={"message":"상대의 마음과 앞으로 제가 할 행동이 궁금해요."}).json()
    assert second["messages"][-1]["kind"] == "offer_draw"
    assert second["pending_draw"]["count"] == 2

    first_proposal = second["pending_draw"]["proposal_id"]
    confirmed = client.post(f"/api/agent/sessions/{session_id}/draw/confirm", json={"kind":"main","proposal_id":first_proposal}).json()
    positions = confirmed["pending_draw"]["positions"]
    pool = client.get("/api/cards").json()["cards"]
    reading = client.post(f"/api/agent/sessions/{session_id}/draw/cards", json={"cards":_select(pool, positions)})
    assert reading.status_code == 200
    state = reading.json()
    assert state["messages"][-1]["kind"] == "card_reading"
    assert "가장 마음에 걸리는" in state["messages"][-1]["text"]
    assert state["messages"][-1]["offer_more"] is True
    assert state["pending_draw"]["count"] == 2
    assert client.post(f"/api/agent/sessions/{session_id}/draw/confirm", json={"kind":"main","proposal_id":first_proposal}).status_code == 422

    supplement = client.post(f"/api/agent/sessions/{session_id}/draw/confirm", json={"kind":"main","proposal_id":state["pending_draw"]["proposal_id"]}).json()
    extra = _select(pool, supplement["pending_draw"]["positions"], {card["card_id"] for card in state["cards"]})
    added = client.post(f"/api/agent/sessions/{session_id}/draw/cards", json={"cards":extra})
    assert added.status_code == 200
    assert len(added.json()["cards"]) == 4

    answered = client.post(f"/api/agent/sessions/{session_id}/messages", json={"message":"그럼 제가 지금 할 일은 뭘까요?"}).json()
    assert answered["messages"][-1]["role"] == "assistant"
    saju = client.post(f"/api/agent/sessions/{session_id}/saju", json={"profile":_profile(),"target_year":2026,"target_month":8})
    assert saju.status_code == 200
    assert client.post(f"/api/agent/sessions/{session_id}/saju", json={"profile":_profile(),"target_year":2026,"target_month":8}).status_code == 422
    reset = client.post(f"/api/agent/sessions/{session_id}/new-topic").json()
    assert reset["cards"] == [] and reset["saju"] is not None
    assert client.get(f"/api/agent/sessions/{session_id}/pdf").status_code == 200

def test_agent_requires_llm_consent():
    assert client.post("/api/agent/sessions", json={"ai_consent":False}).status_code == 422

def test_agent_chat_can_be_deleted_immediately():
    session_id = client.post("/api/agent/sessions", json={"ai_consent":True}).json()["session_id"]
    assert client.get(f"/api/agent/sessions/{session_id}").status_code == 200
    assert client.delete(f"/api/agent/sessions/{session_id}").status_code == 204
    assert client.get(f"/api/agent/sessions/{session_id}").status_code == 404

def test_agent_detects_llm_category_change():
    session_id = client.post("/api/agent/sessions", json={"ai_consent":True}).json()["session_id"]
    client.post(f"/api/agent/sessions/{session_id}/messages", json={"message":"연애 문제로 마음이 힘들어요."})
    love = client.post(f"/api/agent/sessions/{session_id}/messages", json={"message":"관계가 어떻게 될지 궁금해요."}).json()
    assert love["category"] == "love"
    changed = client.post(f"/api/agent/sessions/{session_id}/messages", json={"message":"이번에는 이직과 직장운을 보고 싶어요."}).json()
    assert changed["category"] == "career"
    assert changed["cards"] == []
    assert changed["messages"][-1]["kind"] == "offer_draw"

def test_new_message_skips_pending_card_proposal():
    session_id = client.post("/api/agent/sessions", json={"ai_consent":True}).json()["session_id"]
    client.post(f"/api/agent/sessions/{session_id}/messages", json={"message":"재회가 고민이에요."})
    offered = client.post(f"/api/agent/sessions/{session_id}/messages", json={"message":"헤어진 상대의 마음이 궁금해요."}).json()
    old_proposal = offered["pending_draw"]["proposal_id"]
    skipped = client.post(f"/api/agent/sessions/{session_id}/messages", json={"message":"일단 카드는 말고 대화로 더 얘기할게요."}).json()
    assert skipped["pending_draw"] is None
    assert skipped["messages"][-1]["kind"] == "text"
    stale = client.post(f"/api/agent/sessions/{session_id}/draw/confirm", json={"kind":"main","proposal_id":old_proposal})
    assert stale.status_code == 422

def test_agent_page_and_floating_entry_exist():
    assert client.get("/agent").status_code == 200
    home = client.get("/").text
    assert 'class="agent-float no-print"' in home and 'href="/agent"' in home
