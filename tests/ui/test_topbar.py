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


def test_pie_slices_show_names_and_the_chips_show_counts(page):
    first = page.locator("[data-testid=stPlotlyChart]").first
    first.locator("g.slice text").first.wait_for(timeout=15000)
    slice_text = [t.strip() for t in first.locator("g.slice text").all_text_contents() if t.strip()]
    assert slice_text and not any(t.replace(",", "").isdigit() for t in slice_text), slice_text
    pills = page.locator("[data-testid=stButtonGroup] button").all_inner_texts()
    assert pills and all("·" in t for t in pills), pills


def test_clicking_a_chip_under_a_pie_filters_by_its_name(page):
    page.locator("[data-testid=stButtonGroup] button").first.click()
    chip = page.locator(f"{BAR} button:has-text('✕')").first
    chip.wait_for(timeout=15000)
    text = chip.inner_text()
    assert text.startswith("API type: ") and "·" not in text, text
    page.click(f"{BAR} button:has-text('Clear all')")
    page.wait_for_selector(f"{BAR} button:has-text('✕')", state="detached", timeout=15000)


def _chip(page, text):
    return page.locator("[data-testid=stButtonGroup] button", has_text=text).first


def test_chips_toggle_and_highlight_selected_categories(page):
    chips = page.locator("[data-testid=stButtonGroup] button")
    chips.first.wait_for(timeout=15000)
    slices = "[data-testid=stPlotlyChart] g.slice path"
    page.locator(slices).first.wait_for(timeout=15000)
    fills = lambda: page.evaluate(
        f"[...document.querySelectorAll('{slices}')].slice(0, 7).map(p => getComputedStyle(p).fillOpacity)"
    )
    assert not any(f == "0.35" for f in fills())  # nothing selected, nothing dimmed
    _chip(page, "TCP").click()
    page.locator(f"{BAR} button:has-text('✕')").first.wait_for(timeout=15000)
    page.wait_for_timeout(1500)
    assert sum(f == "0.35" for f in fills()) >= 1  # the unselected slices are dimmed
    _chip(page, "TCP").click()  # clicking again removes it (FR-006f)
    page.wait_for_selector(f"{BAR} button:has-text('✕')", state="detached", timeout=15000)
    page.wait_for_timeout(1500)
    assert not any(f == "0.35" for f in fills())


def test_selecting_dims_the_unselected_bars(page):
    _bars(page, "global").locator(".bars .point path").first.wait_for(timeout=15000)
    _click_bar(page, 2, 0)
    page.wait_for_timeout(2500)
    opacities = page.evaluate(
        "[...document.querySelectorAll('[data-testid=stPlotlyChart] .bars .point path')]"
        ".map(p => getComputedStyle(p).fillOpacity)"
    )
    assert "1" in opacities and any(float(o) < 1 for o in opacities), opacities


def _bars(page, n):
    chart = page.locator("[data-testid=stPlotlyChart]").nth(2 if n == "global" else 3)
    chart.evaluate("e => e.scrollIntoView({block: 'center'})")  # keep it clear of the sticky bar
    page.wait_for_timeout(600)
    return chart


def _click_bar(page, chart_index, bar_index):
    """A real mouse click at the bar's centre (as a user would), not a synthetic element click."""
    bar = page.locator("[data-testid=stPlotlyChart]").nth(chart_index).locator(".bars .point path").nth(bar_index)
    box = bar.bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def _bar_chips(page):
    return page.locator(f"{BAR} button:has-text('\u2715')")


def test_bar_charts_cannot_be_moved_and_have_no_toolbar(page):
    chart = _bars(page, "endpoint")
    chart.locator(".bars .point path").first.wait_for(timeout=15000)
    page.wait_for_timeout(800)
    assert chart.locator(".modebar-btn").count() == 0

    def geometry():
        # Relative to the chart, so scrolling the page itself does not count as movement.
        return chart.evaluate(
            "host => { const c = host.getBoundingClientRect();"
            " return [...host.querySelectorAll('.bars .point path')].slice(0, 3).map(e => {"
            " const r = e.getBoundingClientRect(); return [Math.round(r.x - c.x), Math.round(r.y - c.y), Math.round(r.width)]; }); }"
        )

    before = geometry()
    box = chart.locator(".nsewdrag").first.bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 150, cy + 60, steps=8)
    page.mouse.up()
    page.mouse.wheel(0, -300)
    page.wait_for_timeout(1500)
    assert geometry() == before


def test_clicking_bars_toggles_and_combines_the_selection(page):
    chart = _bars(page, "endpoint")
    points = chart.locator(".bars .point path")
    points.first.wait_for(timeout=15000)
    _click_bar(page, 3, 0)
    _bar_chips(page).first.wait_for(timeout=15000)
    assert _bar_chips(page).first.inner_text().startswith("Per-endpoint middleware: ")
    page.wait_for_timeout(1500)
    _click_bar(page, 3, 1)
    page.wait_for_timeout(2500)
    chip = page.locator(f"{BAR} button:has-text('Per-endpoint middleware')").first
    assert "," in chip.inner_text()  # two bars selected, no modifier key needed
    _click_bar(page, 3, 1)
    page.wait_for_timeout(2500)
    assert "," not in page.locator(f"{BAR} button:has-text('Per-endpoint middleware')").first.inner_text()
    _click_bar(page, 3, 0)
    page.wait_for_selector(f"{BAR} button:has-text('Per-endpoint middleware')", state="detached", timeout=15000)


def test_every_chip_is_fully_visible_without_sideways_scrolling(page):
    clipped = page.evaluate(
        "[...document.querySelectorAll('[data-testid=stButtonGroup] > div')]"
        ".filter(d => d.scrollWidth > d.clientWidth + 1).length"
    )
    assert clipped == 0
