# Magic Tarot — 사주 × 타로 AI MVP

요구사항 명세를 바탕으로 만든 FastAPI + Jinja2 + Vanilla JavaScript MVP입니다. 78장 카드와 156개 정·역방향 TXT를 카드 ID로 정확히 읽으며, Vector DB나 Embedding은 사용하지 않습니다.

## 주요 기능

- 생년월일, 출생 시간, 상담 분야와 질문 입력 및 서버 검증
- 퍼블릭 도메인 Rider–Waite–Smith 실제 카드 아트 78장
- 상담 분야에 따라 5·7·10장을 직접 선택하거나 중복 없이 자동 뽑기
- 카드별 정방향/역방향과 스프레드 자리 지원
- `lunar_python` 절기 기준 사주팔자·오행·십성 + 카드 TXT + Fusion Rule 프롬프트 조립
- 종합운 켈틱 크로스 10장, 관계 7장, 커리어·재물·학업·선택 5장 심층 스프레드
- 카드 조합, 반복 슈트, 메이저 비중, 역방향 집중, 두 가지 조건부 시나리오 분석
- OpenAI 호환 Chat Completions API 연결 및 키가 없거나 실패할 때 규칙 기반 fallback
- UUID JSON 결과 임시 저장, 카드형 결과 UI, 서버 HTML-to-PDF 다운로드
- 반응형/키보드 버튼/대체 텍스트/Print CSS

## 설치 및 실행

Conda 사용 시:

```bash
conda env create -f env.yml
conda activate magic-tarot
python run.py
```

일반 가상환경 사용 시:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다. API 문서는 `/docs`, 상태 확인은 `/health`입니다.

PDF는 Playwright가 서버의 결과 HTML을 Chromium 기반 PDF로 렌더링합니다. Windows에서는 설치된 Edge 또는 Chrome을 자동으로 사용합니다. 해당 브라우저가 없는 환경에서는 한 번만 `python -m playwright install chromium`을 실행하거나 `PDF_BROWSER_PATH`에 Chromium 계열 브라우저 실행 경로를 설정하세요.

## 환경변수

`.env.example`을 `.env`로 복사합니다. `LLM_API_KEY`를 비워두면 API 호출 없이 MVP fallback 해석을 사용합니다. 키가 있으면 `LLM_BASE_URL`, `LLM_MODEL`의 OpenAI 호환 Chat Completions API를 호출합니다. 키와 전체 질문/생년월일은 로그에 남기지 않습니다.

## 데이터 및 검증

카드 원문은 `knowledge/tarot/{card_id}/{orientation}.txt`에 있습니다. SVG와 지식 파일을 다시 만드는 개발용 스크립트는 `scripts/seed_tarot_data.py` 및 Windows용 `scripts/seed_tarot_data.ps1`입니다.

```bash
python scripts/validate_tarot_files.py
pytest -q
```

결과는 `data/results/{uuid}.json`에 저장되며 기본 조회 유효기간은 24시간입니다. 자동 물리 삭제 작업은 MVP 범위 밖이므로 운영 전 스케줄러를 추가해야 합니다.

## 중요한 한계

현재 사주 모듈은 `lunar_python`으로 양력·음력 변환과 절기 기준 사주팔자·오행·십성을 계산합니다. 출생 시간 미상은 정오를 사용하며 출생 지역에 따른 진태양시, 전문 용신 판정과 역술가 감수는 포함하지 않습니다. 타로 결과도 확정된 예언이 아니라 질문과 스프레드에 따른 자기성찰 자료입니다.

의료·법률·투자 등 중요한 판단은 본 결과만으로 결정하지 마세요.
