import logging
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.config import BASE_DIR, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("saju_tarot")
app = FastAPI(title=get_settings().app_name, version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
app.include_router(router)

@app.middleware("http")
async def request_log(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    logger.info("method=%s path=%s status=%s duration_ms=%d", request.method, request.url.path, response.status_code,
                (time.perf_counter() - started) * 1000)
    return response

