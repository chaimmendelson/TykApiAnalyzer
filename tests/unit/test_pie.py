import pytest

from tyk_analyzer.pie import DIMMED_OPACITY, pie_data, slice_geometry, slice_path, toggle

ROWS = [("REST", 50), ("GraphQL", 30), ("TCP", 15), ("<b>x</b>", 5)]


def test_toggle_adds_then_removes():
    assert toggle([], "a") == ["a"]
    assert toggle(["a"], "b") == ["a", "b"]
    assert toggle(["a", "b"], "a") == ["b"]
    assert toggle(toggle([], "a"), "a") == []


def test_geometry_covers_360_degrees_in_order():
    spans = slice_geometry(ROWS)
    assert spans[0][0] == 0 and spans[-1][1] == pytest.approx(360)
    assert all(a[1] == pytest.approx(b[0]) for a, b in zip(spans, spans[1:], strict=False))
    assert spans[0] == (0, pytest.approx(180))


def test_single_category_is_one_full_slice():
    (start, end), = slice_geometry([("Active", 6518)])
    assert (start, end) == (0, pytest.approx(360))
    assert slice_path(start, end).count("a ") == 2  # drawn as a circle, not a degenerate arc


def test_empty_total_gives_empty_slices_without_dividing_by_zero():
    assert slice_geometry([("a", 0)]) == [(0.0, 0.0)]
    assert pie_data([("a", 0)])["slices"][0]["title"] == "a"


def test_nothing_selected_means_nothing_dimmed_or_pulled_out():
    slices = pie_data(ROWS)["slices"]
    assert not any(s["selected"] or s["dimmed"] or s["dx"] or s["dy"] for s in slices)


def test_selection_highlights_selected_and_dims_the_rest():
    data = pie_data(ROWS, {"GraphQL"})
    by = {s["label"]: s for s in data["slices"]}
    assert by["GraphQL"]["selected"] and not by["GraphQL"]["dimmed"] and (by["GraphQL"]["dx"] or by["GraphQL"]["dy"])
    assert all(s["dimmed"] and not s["selected"] for n, s in by.items() if n != "GraphQL")
    assert data["dimmed_opacity"] == DIMMED_OPACITY


def test_small_slices_get_no_inline_label_but_keep_a_hover_title():
    by = {s["label"]: s for s in pie_data(ROWS)["slices"]}
    assert by["REST"]["text"] and by["<b>x</b>"]["text"] is None
    assert by["<b>x</b>"]["title"] == "<b>x</b>: 5 APIs (5.0%)"  # data only; the JS uses textContent


def test_no_markup_is_ever_built_from_category_names():
    from tyk_analyzer import pie

    assert "innerHTML" not in pie._JS and "insertAdjacentHTML" not in pie._JS
    assert all("<" not in s["path"] for s in pie_data(ROWS)["slices"])
