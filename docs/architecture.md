# Architecture

브라우저 입력 → FastAPI/Pydantic 검증 → 사주 구조화 계산 → 카드 ID 검증 및 정확한 TXT 로딩 → Fusion Prompt 조립 → LLM 또는 fallback → UUID JSON 저장 → Jinja2 결과/브라우저 인쇄 순서입니다.

`saju_service`, `knowledge_loader`, `prompt_builder`, `llm_service`, `reading_service`를 분리해 만세력 엔진과 LLM 공급자를 독립 교체할 수 있습니다. 사용자 문자열은 파일 경로 생성에 사용되지 않으며 카드 ID는 메타데이터에서 선검증합니다.
