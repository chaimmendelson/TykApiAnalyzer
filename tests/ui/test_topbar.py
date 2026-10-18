"""Browser checks for the sticky top bar. Opt-in: set UI_URL to a running dashboard.

    UI_URL=http://localhost:8501 pytest tests/ui

Needs `playwright` and a browser; set UI_BROWSER_CHANNEL=chrome to use an installed Chrome.
"""

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")

URL = os.environ.get("UI_URL")
pytestmark = pytest.mark.skipif(not URL, reason="UI_URL not set")

THEMES = {"dark": "rgb(14, 17, 23)", "light": "rgb(255, 255, 255)"}
BAR = ".st-key-topbar"


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
        channel = os.environ.get("UI_BROWSER_CHANNEL")
        b = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
        yield b
        b.close()


@pytest.fixture(params=sorted(THEMES))
def page(request, browser):
    pg = browser.new_page(viewport={"width": 1500, "height": 900}, color_scheme=request.param)
    pg.goto(URL)
    pg.wait_for_selector(BAR, timeout=30000)
    pg.wait_for_selector("[data-testid=stPlotlyChart]", timeout=30000)
    pg.theme = request.param
    yield pg
    pg.close()


def _wrapper_top(pg) -> float:
    return pg.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().top")


def test_bar_controls_are_in_one_row(page):
    tops = page.evaluate(
        f"[...document.querySelectorAll('{BAR} [data-testid=stColumn]')].slice(0, 4)"
        ".map(c => Math.round(c.getBoundingClientRect().top))"
    )
    assert len(tops) == 4 and len(set(tops)) == 1, tops


def test_bar_background_matches_the_theme(page):
    bg = page.evaluate(
        f"getComputedStyle(document.querySelector('{BAR}').parentElement).backgroundColor"
    )
    assert bg == THEMES[page.theme]


def test_bar_stays_pinned_and_compact(page):
    before = _wrapper_top(page)
    height = page.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().height")
    assert height < 80
    page.mouse.move(700, 600)
    page.mouse.wheel(0, 1500)
    page.wait_for_timeout(800)
    assert 0 <= _wrapper_top(page) <= before + 1


def test_bar_does_not_cover_the_first_chart(page):
    bar = page.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().bottom")
    chart = page.evaluate("document.querySelector('[data-testid=stPlotlyChart]').getBoundingClientRect().top")
    assert chart >= bar


def test_choosing_an_organization_adds_a_chip_inside_the_bar(page):
    page.click(f"{BAR} [data-testid=stMultiSelect] input")
    page.click("[role=option] >> nth=0")
    page.keyboard.press("Escape")
    page.wait_for_selector(f"{BAR} button:has-text('✕')", timeout=15000)
    height = page.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().height")
    assert height < 130
    page.click(f"{BAR} button:has-text('Clear all')")
    page.wait_for_selector(f"{BAR} button:has-text('✕')", state="detached", timeout=15000)
