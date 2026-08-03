from datetime import date
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def profile():
    return {"nickname":"테스터","birth_date":"1995-06-10","birth_time":"14:30","time_unknown":False,
            "calendar_type":"solar","gender":"female","birth_place":"서울"}

def test_health_and_cards():
    assert client.get("/health").json() == {"status":"ok"}
    assert len(client.get("/api/cards").json()["cards"]) == 78

def test_saju_has_plain_language_summary():
    response = client.post("/api/saju/calculate", json={"profile": profile(), "target_year": 2026, "target_month": 8})
    assert response.status_code == 200
    data = response.json()
    assert set(data["plain_language"]) == {"personality", "natural_strength", "balance_tip"}
    assert "기운" not in data["summary"]
    assert data["technical_summary"]
    assert data["calculation_basis"]["region_correction"].startswith("미적용")
    assert data["professional_useful_element_calculated"] is False

def test_saju_matches_lunar_python_official_example():
    known = profile()
    known.update({"birth_date":"1986-05-29", "birth_time":"00:00", "calendar_type":"solar"})
    response = client.post("/api/saju/calculate", json={"profile":known, "target_year":2026, "target_month":8})
    assert response.status_code == 200
    data = response.json()
    assert data["lunar_birth"] == "1986-04-21"
    assert data["four_pillars"]["year"] == "병인"
    assert data["four_pillars"]["month"] == "계사"
    assert data["four_pillars"]["day"] == "계유"

def test_no_ai_consent_skips_llm(tmp_path, monkeypatch):
    import app.services.reading_service as reading_service
    async def should_not_run(*_args):
        raise AssertionError("LLM must not be called without consent")
    monkeypatch.setattr(reading_service, "generate", should_not_run)
    drawn = client.post("/api/tarot/draw", json={"count":3,"spread_type":"situation_action_outcome","seed":4}).json()["cards"]
    response = client.post("/api/reading/generate", json={"profile":profile(),"question":"질문","category":"career",
        "target_year":2026,"target_month":8,"spread_type":"situation_action_outcome","ai_consent":False,
        "cards":[{"position":c["position"],"card_id":c["card_id"],"orientation":c["orientation"]} for c in drawn]})
    assert response.status_code == 200
    stored = client.get(f"/api/results/{response.json()['result_id']}").json()
    assert stored["llm_diagnostic"]["code"] == "consent_not_given"

def test_tarot_only_does_not_require_profile():
    drawn = client.post("/api/tarot/draw", json={"count":3,"spread_type":"situation_action_outcome","seed":8}).json()["cards"]
    response = client.post("/api/reading/generate", json={"reading_mode":"tarot","profile":None,"question":"관계의 흐름은?","current_situation":"최근 관계가 소원해졌습니다.","category":"love",
        "target_year":2026,"target_month":8,"spread_type":"situation_action_outcome","ai_consent":False,
        "cards":[{"position":c["position"],"card_id":c["card_id"],"orientation":c["orientation"]} for c in drawn]})
    assert response.status_code == 200
    stored = client.get(f"/api/results/{response.json()['result_id']}").json()
    assert stored["input"]["reading_mode"] == "tarot"
    assert stored["saju_result"] is None
    page = client.get(f"/results/{response.json()['result_id']}").text
    assert "사주 계산 근거와 한계 보기" not in page

def test_saju_only_does_not_require_cards():
    response = client.post("/api/reading/generate", json={"reading_mode":"saju","profile":profile(),"question":"","category":"general",
        "target_year":2026,"target_month":8,"spread_type":"saju_only","ai_consent":False,"cards":[]})
    assert response.status_code == 200
    stored = client.get(f"/api/results/{response.json()['result_id']}").json()
    assert stored["input"]["reading_mode"] == "saju"
    assert stored["cards"] == []
    page = client.get(f"/results/{response.json()['result_id']}").text
    assert "선택한 카드" not in page
    assert "사주 계산 근거와 한계 보기" in page

def test_tarot_and_saju_pdf_downloads_handle_optional_profile(monkeypatch):
    import app.api.routes as routes
    monkeypatch.setattr(routes, "render_result_pdf", lambda _url: b"%PDF-1.4\nmock")

    drawn = client.post("/api/tarot/draw", json={"count":3,"spread_type":"situation_action_outcome","seed":12}).json()["cards"]
    tarot = client.post("/api/reading/generate", json={"reading_mode":"tarot","profile":None,"question":"","current_situation":"새로운 선택을 고민하고 있습니다.","category":"decision",
        "target_year":2026,"target_month":8,"spread_type":"situation_action_outcome","ai_consent":False,
        "cards":[{"position":c["position"],"card_id":c["card_id"],"orientation":c["orientation"]} for c in drawn]}).json()
    tarot_pdf = client.get(f"/api/results/{tarot['result_id']}/pdf")
    assert tarot_pdf.status_code == 200
    assert tarot_pdf.headers["content-type"] == "application/pdf"
    assert "magic-tarot_user_" in tarot_pdf.headers["content-disposition"]

    saju = client.post("/api/reading/generate", json={"reading_mode":"saju","profile":profile(),"question":"","category":"general",
        "target_year":2026,"target_month":8,"spread_type":"saju_only","ai_consent":False,"cards":[]}).json()
    saju_pdf = client.get(f"/api/results/{saju['result_id']}/pdf")
    assert saju_pdf.status_code == 200
    assert saju_pdf.headers["content-type"] == "application/pdf"
    assert "%ED%85%8C%EC%8A%A4%ED%84%B0" in saju_pdf.headers["content-disposition"]

def test_reading_flow_and_result(tmp_path, monkeypatch):
    import app.repositories.result_repository as result_repository
    monkeypatch.setattr(result_repository, "RESULT_DIR", tmp_path)
    drawn = client.post("/api/tarot/draw", json={"count":3,"spread_type":"situation_action_outcome","seed":2}).json()["cards"]
    response = client.post("/api/reading/generate", json={"profile":profile(),"question":"이직을 준비할까요?","category":"career",
        "target_year":2026,"target_month":8,"current_situation":"성장을 고민합니다.","spread_type":"situation_action_outcome","ai_consent":True,
        "cards":[{"position":c["position"],"card_id":c["card_id"],"orientation":c["orientation"]} for c in drawn]})
    assert response.status_code == 200
    result_id = response.json()["result_id"]
    stored = client.get(f"/api/results/{result_id}")
    assert stored.status_code == 200
    reading = stored.json()["reading"]
    assert len(reading["card_readings"]) == 3
    assert reading["dominant_patterns"]
    assert reading["card_combinations"]
    assert reading["saju_overlay"]
    assert set(reading["scenario_paths"]) == {"current_path", "adjusted_path"}
    assert stored.json()["llm_diagnostic"]["code"] == "not_configured"
    assert client.get(f"/results/{result_id}").status_code == 200

def test_future_birth_and_duplicate_cards_fail():
    bad = profile(); bad["birth_date"] = str(date.today().replace(year=date.today().year + 1))
    assert client.post("/api/saju/calculate", json={"profile":bad,"target_year":2026,"target_month":8}).status_code == 422
    card={"position":"x","card_id":"00_the_fool","orientation":"upright"}
    assert client.post("/api/reading/generate",json={"profile":profile(),"question":"질문","category":"general","target_year":2026,"target_month":8,
        "spread_type":"situation_obstacle_advice","ai_consent":True,"cards":[card,card,card]}).status_code == 422
