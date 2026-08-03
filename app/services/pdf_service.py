import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BROWSER_CANDIDATES = [
    Path(os.getenv("PDF_BROWSER_PATH", "")),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]

def find_browser() -> str | None:
    return next((str(path) for path in BROWSER_CANDIDATES if str(path) and path.is_file()), None)

def render_result_pdf(result_url: str) -> bytes:
    executable = find_browser()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable) if executable else playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
            page.goto(result_url, wait_until="networkidle", timeout=30_000)
            page.emulate_media(media="print")
            return page.pdf(
                format="A4", print_background=True, prefer_css_page_size=True,
                margin={"top": "14mm", "right": "13mm", "bottom": "14mm", "left": "13mm"},
                display_header_footer=True,
                header_template="<span></span>",
                footer_template='<div style="width:100%;font-size:8px;color:#777;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
            )
        finally:
            browser.close()
