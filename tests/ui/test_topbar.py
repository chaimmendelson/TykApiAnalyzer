"""Browser checks for the sticky top bar. Opt-in: set UI_URL to a running dashboard.

    UI_URL=http://localhost:8501 pytest tests/ui

Needs `playwright` and a browser; set UI_BROWSER_CHANNEL=chrome to use an installed Chrome.
"""

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")
expect = playwright.expect

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


def _clear_all(page):
    return page.locator(f"{BAR} button", has_text="Clear all").first


def _wait_selected(page, selected=True):
    """Clear all is enabled exactly while something is selected (there is no chip line any more)."""
    if selected:
        expect(_clear_all(page)).to_be_enabled(timeout=15000)
    else:
        expect(_clear_all(page)).to_be_disabled(timeout=15000)
    page.wait_for_timeout(800)


def _tab(page, name):
    page.get_by_role("tab", name=name).click()
    page.wait_for_timeout(700)


def _showing(page):
    """The 'Showing N of M' count lives in the APIs tab; read it there and come back to Overview."""
    _tab(page, "APIs")
    text = page.locator("[data-testid=stApp]").inner_text()
    _tab(page, "Overview")
    return int(text.split("Showing ")[1].split(" of")[0].replace(",", ""))


def _option_labels(page, index):
    """Open dropdown `index`, read its option labels, close it."""
    page.locator(f"{BAR} [data-testid=stMultiSelect]").nth(index).locator("input").click()
    page.wait_for_timeout(500)
    labels = [t for t in page.locator("[role=option]").all_inner_texts() if t != "Select all"]
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    return labels


def _count_of(labels, name):
    return next(int(l.rsplit("(", 1)[1].rstrip(")").replace(",", "")) for l in labels if l.startswith(name + " ("))


def _boxes(page, selector):
    return page.evaluate(
        f"[...document.querySelectorAll('{selector}')].map(c => {{ const r = c.getBoundingClientRect();"
        " return [Math.round(r.left), Math.round(r.top), Math.round(r.width)]; })"
    )


def test_five_dropdowns_share_one_row_of_equal_width(page):
    boxes = _boxes(page, f"{BAR} [data-testid=stMultiSelect]")
    assert len(boxes) == 5, boxes
    assert len({top for _, top, _ in boxes}) == 1, boxes  # one row
    widths = [w for _, _, w in boxes]
    assert max(widths) - min(widths) <= 2, widths  # equal widths
    labels = page.locator(f"{BAR} [data-testid=stMultiSelect] input").evaluate_all("els => els.map(e => e.placeholder)")
    assert labels == ["All organizations", "All API types", "All authentication", "All global middleware", "All per-endpoint middleware"], labels


def test_title_refresh_and_clear_share_the_first_row(page):
    tops = page.evaluate(
        f"[...document.querySelectorAll('{BAR} [data-testid=stColumn]')].slice(0, 3)"
        ".map(c => Math.round(c.getBoundingClientRect().top))"
    )
    assert len(tops) == 3 and len(set(tops)) == 1, tops


def test_bar_background_matches_the_theme(page):
    bg = page.evaluate(
        f"getComputedStyle(document.querySelector('{BAR}').parentElement).backgroundColor"
    )
    assert bg == THEMES[page.theme]


def test_bar_stays_pinned_and_compact(page):
    before = _wrapper_top(page)
    height = page.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().height")
    assert height < 130  # two compact rows
    page.mouse.move(700, 600)
    page.mouse.wheel(0, 1500)
    page.wait_for_timeout(800)
    assert 0 <= _wrapper_top(page) <= before + 1


def test_bar_does_not_cover_the_first_chart(page):
    bar = page.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().bottom")
    chart = page.evaluate("document.querySelector('[data-testid=stPlotlyChart]').getBoundingClientRect().top")
    assert chart >= bar


def test_choosing_an_organization_shows_in_its_dropdown_and_clear_all_resets(page):
    page.locator(f"{BAR} [data-testid=stMultiSelect]").first.locator("input").click()
    page.locator("[role=option]").nth(1).click()  # nth(0) is "Select all"
    page.keyboard.press("Escape")
    _wait_selected(page)
    assert _dropdown_tags(page, 0)
    height = page.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().height")
    assert height < 130  # still two rows: no chip line
    _clear_all(page).click()
    _wait_selected(page, False)
    assert not _dropdown_tags(page, 0)


def test_pie_slices_show_names_and_the_chips_show_counts(page):
    first = page.locator("[data-testid=stPlotlyChart]").first
    first.locator("g.slice text").first.wait_for(timeout=15000)
    slice_text = [t.strip() for t in first.locator("g.slice text").all_text_contents() if t.strip()]
    assert slice_text and not any(t.replace(",", "").isdigit() for t in slice_text), slice_text
    pills = page.locator("[data-testid=stButtonGroup] button").all_inner_texts()
    assert pills and all("·" in t for t in pills), pills


def test_clicking_a_chip_under_a_pie_filters_by_its_name(page):
    total = _showing(page)
    page.locator("[data-testid=stButtonGroup] button").first.click()
    _wait_selected(page)
    assert _showing(page) < total
    assert _dropdown_tags(page, 1)  # API type dropdown shows the same choice
    _clear_all(page).click()
    _wait_selected(page, False)
    assert _showing(page) == total


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
    _wait_selected(page)
    assert sum(f == "0.35" for f in fills()) >= 1  # the unselected slices are dimmed
    _chip(page, "TCP").click()  # clicking again removes it (FR-006f)
    _wait_selected(page, False)
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
    chart.locator(".bars .point path").first.wait_for(timeout=15000)
    _click_bar(page, 3, 0)
    _wait_selected(page)
    assert len(_dropdown_tags(page, 4)) == 1
    _click_bar(page, 3, 1)
    page.wait_for_timeout(2000)
    assert len(_dropdown_tags(page, 4)) == 2  # two bars selected, no modifier key needed
    _click_bar(page, 3, 1)
    page.wait_for_timeout(2000)
    assert len(_dropdown_tags(page, 4)) == 1
    _click_bar(page, 3, 0)
    _wait_selected(page, False)


def _dropdown_tags(page, index):
    text = page.locator(f"{BAR} [data-testid=stMultiSelect]").nth(index).evaluate("e => e.innerText")
    return [t for t in text.splitlines() if "(" in t and ")" in t]  # tags read like "TCP (500)"


def test_choosing_in_a_dropdown_highlights_the_chart_and_filters(page):
    page.locator(f"{BAR} [data-testid=stMultiSelect]").nth(1).locator("input").click()
    page.locator("[role=option]", has_text="TCP").first.click()
    page.wait_for_timeout(500)  # let the selection register before closing the list
    page.keyboard.press("Escape")
    _wait_selected(page)
    assert any("TCP" in t for t in _dropdown_tags(page, 1))
    pressed = page.locator("[data-testid=stButtonGroup] button[aria-checked=true], [data-testid=stButtonGroup] button[aria-pressed=true]")
    assert pressed.count() >= 1 and "TCP" in pressed.first.inner_text()  # the chip under the pie agrees
    dimmed = page.evaluate(
        "[...document.querySelectorAll('[data-testid=stPlotlyChart] g.slice path')].slice(0, 7)"
        ".filter(p => getComputedStyle(p).fillOpacity === '0.35').length"
    )
    assert dimmed >= 1  # the pie dims the unselected slices


def test_clicking_a_bar_shows_in_its_dropdown_and_clear_all_empties_everything(page):
    chart = _bars(page, "global")
    chart.locator(".bars .point path").first.wait_for(timeout=15000)
    _click_bar(page, 2, 1)
    page.wait_for_timeout(2500)
    assert _dropdown_tags(page, 3), "global middleware dropdown should show the clicked bar"
    _clear_all(page).click()
    _wait_selected(page, False)
    assert all(not _dropdown_tags(page, i) for i in range(5))


def test_chip_selection_from_a_pie_appears_in_its_dropdown(page):
    page.locator("[data-testid=stButtonGroup] button", has_text="JWT").first.click()
    page.wait_for_timeout(2500)
    assert any("JWT" in t for t in _dropdown_tags(page, 2))


def test_every_chip_is_fully_visible_without_sideways_scrolling(page):
    clipped = page.evaluate(
        "[...document.querySelectorAll('[data-testid=stButtonGroup] > div')]"
        ".filter(d => d.scrollWidth > d.clientWidth + 1).length"
    )
    assert clipped == 0


def test_there_is_no_chip_line_and_the_bar_stays_two_rows(page):
    page.locator("[data-testid=stButtonGroup] button", has_text="TCP").first.click()
    _wait_selected(page)
    assert page.locator(f"{BAR} button:has-text('\u2715')").count() == 0
    height = page.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().height")
    assert height < 130, height


def test_choosing_in_one_filter_adjusts_the_counts_in_the_others(page):
    before = {i: _option_labels(page, i) for i in range(5)}
    page.locator(f"{BAR} [data-testid=stMultiSelect]").nth(1).locator("input").click()
    page.locator("[role=option]", has_text="TCP").first.click()
    page.wait_for_timeout(500)
    page.keyboard.press("Escape")
    _wait_selected(page)
    after = {i: _option_labels(page, i) for i in range(5)}
    names = lambda labels: [l.rsplit(" (", 1)[0] for l in labels]
    for i in range(5):
        expected = [n for n in names(before[i]) if not (i == 1 and n == "TCP")]  # an open list hides the chosen one
        assert names(after[i]) == expected, i  # every category stays listed, in the same order
    tcp_tag = _dropdown_tags(page, 1)[0]
    assert tcp_tag == "TCP (500)", tcp_tag  # a dimension ignores its own selection
    assert _count_of(after[1], "REST (classic)") == _count_of(before[1], "REST (classic)")
    assert _count_of(after[2], "None (keyless)") < _count_of(before[2], "None (keyless)")  # auth follows API type
    assert _showing(page) == 500
    assert any(l.endswith("(0)") for i in (3, 4) for l in after[i])  # nothing matches: stays listed as (0)
    _clear_all(page).click()
    _wait_selected(page, False)
    assert {i: _option_labels(page, i) for i in range(5)} == before  # counts restored


DETAIL = ".st-key-detail"


def _table_box(page):
    _tab(page, "APIs")
    table = page.locator("[data-testid=stDataFrame]").first
    table.evaluate("e => e.scrollIntoView({block: 'start'})")
    page.mouse.wheel(0, -150)  # leave room for the sticky bar above the table
    page.wait_for_timeout(800)
    return table.bounding_box()


def _select_first_row(page):
    box = _table_box(page)
    page.mouse.click(box["x"] + 22, box["y"] + 36 + 17)  # the first row's checkbox, as a user would
    page.wait_for_timeout(2500)


def test_table_and_detail_panel_are_side_by_side_with_a_hint(page):
    table = _table_box(page)
    detail = page.locator(DETAIL).bounding_box()
    assert detail["x"] >= table["x"] + table["width"], (table, detail)  # panel is to the right
    assert table["width"] > detail["width"]  # about two thirds / one third
    assert "Select an API in the table" in page.locator(DETAIL).inner_text()


def test_selecting_a_row_fills_the_detail_panel(page):
    _select_first_row(page)
    text = page.locator(DETAIL).inner_text()
    assert "API type:" in text and "Organization:" in text
    assert "protocol" in text  # the classification evidence (TLS shows up here for TCP APIs)
    assert "Select an API in the table" not in text


def test_detail_panel_stays_in_view_and_clear_of_the_sticky_bar(page):
    _select_first_row(page)
    bar_bottom = page.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().bottom")
    page.mouse.move(700, 500)
    page.mouse.wheel(0, 260)  # scroll the page so the table's top passes under the bar
    page.wait_for_timeout(800)
    top = page.locator(DETAIL).bounding_box()["y"]
    assert top >= bar_bottom - 1, (top, bar_bottom)  # not hidden behind the bar
    assert top < 400, top  # and still on screen, because it sticks


def test_the_table_has_no_tls_column_and_no_inactive_state(page):
    _tab(page, "APIs")
    text = page.locator("[data-testid=stApp]").inner_text()
    assert "TLS" not in text.replace("Mutual TLS", "")


def test_two_tabs_with_overview_first(page):
    tabs = page.get_by_role("tab")
    assert tabs.all_inner_texts() == ["Overview", "APIs"]
    assert page.get_by_role("tab", name="Overview").get_attribute("aria-selected") == "true"
    assert page.locator("[data-testid=stPlotlyChart]").first.is_visible()  # charts are on Overview


def test_filters_stay_applied_when_switching_tabs(page):
    total = _showing(page)
    page.locator("[data-testid=stButtonGroup] button", has_text="TCP").first.click()
    _wait_selected(page)
    _tab(page, "APIs")
    assert _showing(page) == 500 < total  # the table follows the filter chosen on Overview
    assert _dropdown_tags(page, 1)  # the pinned bar still shows it on the APIs tab
    _tab(page, "Overview")
    assert _dropdown_tags(page, 1)


def test_table_and_detail_start_at_the_same_height(page):
    _table_box(page)
    table = page.locator("[data-testid=stDataFrame]").first.bounding_box()["y"]
    detail = page.locator(DETAIL).bounding_box()["y"]
    assert abs(table - detail) <= 2, (table, detail)


def test_the_pinned_bar_is_visible_on_both_tabs(page):
    for name in ("Overview", "APIs"):
        _tab(page, name)
        top = page.evaluate(f"document.querySelector('{BAR}').parentElement.getBoundingClientRect().top")
        assert 0 <= top < 200, (name, top)
