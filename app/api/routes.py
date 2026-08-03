from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from app.config import BASE_DIR
from app.schemas.models import (DrawRequest, ReadingRequest, SajuRequest, AgentSessionCreate,
                                AgentMessageRequest, AgentDrawConfirm, AgentCardsRequest, AgentSajuRequest)
from app.repositories.tarot_repository import get_cards, get_card
from app.repositories.result_repository import get_result
from app.services.tarot_draw_service import draw_cards, SPREADS, SPREAD_DETAILS, CATEGORY_SPREADS
from app.services.saju_service import calculate_saju
from app.services.reading_service import create_reading
from app.services.llm_service import check_connection
from app.services.pdf_service import render_result_pdf
from app.repositories.agent_session_repository import get_session, delete_session
from app.services.agent_service import (create_agent_session, handle_user_message, confirm_draw,
                                        submit_agent_cards, connect_saju, reset_topic)
from urllib.parse import quote
from starlette.concurrency import run_in_threadpool

router = APIRouter()
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")

@router.get("/", response_class=HTMLResponse)
def index(request: Request): return templates.TemplateResponse(request, "index.html")

@router.get("/consult", response_class=HTMLResponse)
def consult(request: Request): return templates.TemplateResponse(request, "consult.html")

@router.get("/agent", response_class=HTMLResponse)
def agent_page(request: Request): return templates.TemplateResponse(request, "agent.html")

@router.get("/results/{result_id}", response_class=HTMLResponse)
def result_page(request: Request, result_id: str):
    try: result = get_result(result_id)
    except KeyError: raise HTTPException(404, "결과를 찾을 수 없거나 보관 기간이 지났습니다.")
    return templates.TemplateResponse(request, "result.html", {"result": result})

@router.get("/health")
def health(): return {"status": "ok"}

@router.get("/api/cards")
def cards(): return {"cards": get_cards()}

@router.get("/api/cards/{card_id}")
def card(card_id: str):
    try: return get_card(card_id)
    except KeyError as error: raise HTTPException(404, str(error))

@router.get("/api/spreads")
def spreads():
    return {"spreads": [{"id": key, "positions": SPREADS[key], "count": len(SPREADS[key]), **value} for key, value in SPREAD_DETAILS.items()],
            "category_defaults": CATEGORY_SPREADS}

@router.get("/api/llm/status")
async def llm_status():
    return await check_connection()

@router.post("/api/tarot/draw")
def tarot_draw(body: DrawRequest):
    try: return {"spread_type": body.spread_type, "cards": draw_cards(body.count, body.spread_type, body.seed)}
    except ValueError as error: raise HTTPException(422, str(error))

@router.post("/api/saju/calculate")
def saju(body: SajuRequest): return calculate_saju(body.profile, body.target_year, body.target_month)

@router.post("/api/reading/generate")
async def reading(body: ReadingRequest):
    try:
        result = await create_reading(body)
        return {"result_id": result["result_id"], "created_at": result["created_at"], "reading": result["reading"]}
    except (KeyError, FileNotFoundError, ValueError) as error: raise HTTPException(422, str(error))

@router.get("/api/results/{result_id}")
def result_api(result_id: str):
    try: return get_result(result_id)
    except KeyError: raise HTTPException(404, "결과를 찾을 수 없거나 보관 기간이 지났습니다.")

@router.get("/api/results/{result_id}/pdf")
async def result_pdf(request: Request, result_id: str):
    try: result = get_result(result_id)
    except KeyError: raise HTTPException(404, "결과를 찾을 수 없습니다.")
    try:
        result_url = str(request.url_for("result_page", result_id=result_id)) + "?pdf_render=1"
        content = await run_in_threadpool(render_result_pdf, result_url)
    except Exception as error:
        raise HTTPException(503, "PDF 생성에 실패했습니다. 서버에 Chromium 또는 Edge가 설치되어 있는지 확인해 주세요.") from error
    profile = result.get("input", {}).get("profile") or {}
    nickname = profile.get("nickname") or "user"
    safe_name = "".join(char for char in nickname if char.isalnum() or char in "-_ ")[:30].strip() or "user"
    filename = quote(f"magic-tarot_{safe_name}_{result_id[:8]}.pdf")
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{filename}", "Cache-Control": "no-store"
    })

@router.post("/api/agent/sessions")
def agent_session_create(body: AgentSessionCreate):
    return create_agent_session(body.ai_consent)

@router.get("/api/agent/sessions/{session_id}")
def agent_session_get(session_id: str):
    try: return get_session(session_id)
    except KeyError: raise HTTPException(404, "상담 세션을 찾을 수 없거나 24시간이 지났습니다.")

@router.delete("/api/agent/sessions/{session_id}", status_code=204)
def agent_session_delete(session_id: str):
    try: delete_session(session_id)
    except KeyError: raise HTTPException(404, "삭제할 상담 세션을 찾을 수 없습니다.")
    return Response(status_code=204)

@router.post("/api/agent/sessions/{session_id}/messages")
async def agent_message(session_id: str, body: AgentMessageRequest):
    try: return await handle_user_message(get_session(session_id), body.message.strip())
    except KeyError: raise HTTPException(404, "상담 세션을 찾을 수 없거나 24시간이 지났습니다.")
    except RuntimeError as error: raise HTTPException(503, str(error))

@router.post("/api/agent/sessions/{session_id}/draw/confirm")
def agent_draw_confirm(session_id: str, body: AgentDrawConfirm):
    try: return confirm_draw(get_session(session_id), body.kind, body.count, body.proposal_id)
    except KeyError: raise HTTPException(404, "상담 세션을 찾을 수 없습니다.")
    except ValueError as error: raise HTTPException(422, str(error))

@router.post("/api/agent/sessions/{session_id}/draw/cards")
async def agent_draw_cards(session_id: str, body: AgentCardsRequest):
    try: return await submit_agent_cards(get_session(session_id), body.cards)
    except KeyError: raise HTTPException(404, "상담 세션을 찾을 수 없습니다.")
    except ValueError as error: raise HTTPException(422, str(error))
    except RuntimeError as error: raise HTTPException(503, str(error))

@router.post("/api/agent/sessions/{session_id}/saju")
def agent_saju(session_id: str, body: AgentSajuRequest):
    try: return connect_saju(get_session(session_id), body.profile, body.target_year, body.target_month)
    except KeyError: raise HTTPException(404, "상담 세션을 찾을 수 없습니다.")
    except ValueError as error: raise HTTPException(422, str(error))

@router.post("/api/agent/sessions/{session_id}/new-topic")
def agent_new_topic(session_id: str):
    try: return reset_topic(get_session(session_id))
    except KeyError: raise HTTPException(404, "상담 세션을 찾을 수 없습니다.")

@router.get("/agent/{session_id}/print", response_class=HTMLResponse)
def agent_print(request: Request, session_id: str):
    try: session = get_session(session_id)
    except KeyError: raise HTTPException(404, "상담 세션을 찾을 수 없습니다.")
    return templates.TemplateResponse(request, "agent_print.html", {"session":session})

@router.get("/api/agent/sessions/{session_id}/pdf")
async def agent_pdf(request: Request, session_id: str):
    try: session = get_session(session_id)
    except KeyError: raise HTTPException(404, "상담 세션을 찾을 수 없습니다.")
    try:
        url = str(request.url_for("agent_print", session_id=session_id))
        content = await run_in_threadpool(render_result_pdf, url)
    except Exception as error:
        raise HTTPException(503, "상담 PDF 생성에 실패했습니다.") from error
    filename = quote(f"magic-tarot-agent_{session_id[:8]}.pdf")
    return Response(content, media_type="application/pdf", headers={"Content-Disposition":f"attachment; filename*=UTF-8''{filename}", "Cache-Control":"no-store"})
