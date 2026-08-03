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
