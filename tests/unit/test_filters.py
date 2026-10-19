from tyk_analyzer.filters import apply_selection, counts, counts_with_selection
from tyk_analyzer.snapshot import build_snapshot


def names(records):
    return sorted(r.name for r in records)


def test_empty_selection_returns_everything(source):
    recs = build_snapshot(source).records
    assert apply_selection(recs, {}) == recs
    assert apply_selection(recs, {"api_type": set(), "auth": set()}) == recs


def test_single_category(source):
    recs = build_snapshot(source).records
    assert names(apply_selection(recs, {"api_type": {"Federation"}})) == ["federation"]


def test_values_within_a_dimension_are_or(source):
    recs = build_snapshot(source).records
    got = apply_selection(recs, {"api_type": {"MCP", "Federation"}})
    assert names(got) == ["federation", "mcp"]


def test_dimensions_are_and(source):
    recs = build_snapshot(source).records
    got = apply_selection(recs, {"auth": {"JWT"}, "api_type": {"REST (classic)"}})
    assert names(got) == ["multi-auth"]  # udg also has JWT but is not REST (classic)


def test_authentication_selection_matches_any_of_an_apis_methods(source):
    recs = build_snapshot(source).records
    assert "multi-auth" in names(apply_selection(recs, {"auth": {"OAuth 2.0"}}))


def test_count_equals_rows_listed_when_selected(source):
    recs = build_snapshot(source).records
    other = {"org": {"perimeter"}}
    for dim in ("api_type", "auth", "org", "mw_global", "mw_endpoint"):
        for label, n in counts_with_selection(recs, other, dim):
            listed = apply_selection(recs, {**other, dim: {label}})
            assert len(listed) == n, (dim, label)


def test_own_dimension_selection_is_ignored_for_its_own_chart(source):
    recs = build_snapshot(source).records
    sel = {"api_type": {"MCP"}}
    assert counts_with_selection(recs, sel, "api_type") == counts(recs, "api_type")
    # other charts reflect the selection
    assert counts_with_selection(recs, sel, "auth") == [("API key", 1)]


def test_combination_matching_nothing_is_empty(source):
    recs = build_snapshot(source).records
    assert apply_selection(recs, {"api_type": {"MCP"}, "auth": {"Basic"}}) == []


def test_selection_does_not_mutate_inputs(source):
    recs = build_snapshot(source).records
    sel = {"api_type": {"MCP"}}
    apply_selection(recs, sel)
    assert sel == {"api_type": {"MCP"}} and len(recs) == 21


def test_middleware_selection_matches_exactly_the_counted_apis():
    from tests.conftest import InMemorySource, load_fixture

    recs = build_snapshot(InMemorySource(load_fixture("middleware.json"), [])).records
    for dim in ("mw_global", "mw_endpoint"):
        for label, n in counts(recs, dim):
            assert len(apply_selection(recs, {dim: {label}})) == n, (dim, label)
    got = apply_selection(recs, {"mw_global": {"CORS"}, "mw_endpoint": {"Circuit breaker"}})
    assert names(got) == ["several"]
    listed = {r.name for dim in ("mw_global", "mw_endpoint") for label, _ in counts(recs, dim)
              for r in apply_selection(recs, {dim: {label}})}
    assert "nothing-enabled" not in listed


def test_toggle_adds_then_removes_a_category():
    from tyk_analyzer.filters import toggle

    assert toggle([], "Cache") == ["Cache"]
    assert toggle(["Cache"], "CORS") == ["Cache", "CORS"]
    assert toggle(["Cache", "CORS"], "Cache") == ["CORS"]
    assert toggle(toggle([], "Cache"), "Cache") == []


def test_dropdown_options_list_every_category_in_a_fixed_order(source):
    from tyk_analyzer.filters import dropdown_options

    recs = build_snapshot(source).records
    base = dropdown_options(recs, {}, "api_type")
    assert [n for n, _ in base] == [n for n, _ in counts(recs, "api_type")]
    filtered = dropdown_options(recs, {"auth": {"JWT"}}, "api_type")
    assert [n for n, _ in filtered] == [n for n, _ in base]  # order never changes with the selection
    assert any(c == 0 for _, c in filtered)  # categories with no match stay listed with 0


def test_dropdown_counts_follow_the_other_dimensions_and_ignore_the_own_one(source):
    from tyk_analyzer.filters import dropdown_options

    recs = build_snapshot(source).records
    selection = {"auth": {"JWT"}, "api_type": {"MCP"}}
    for dim in ("api_type", "auth", "org", "mw_global", "mw_endpoint"):
        others = {d: v for d, v in selection.items() if d != dim}
        for label, n in dropdown_options(recs, selection, dim):
            assert n == len(apply_selection(recs, {**others, dim: {label}})), (dim, label)


def test_a_selected_category_with_no_matches_stays_listed_with_zero(source):
    from tyk_analyzer.filters import dropdown_options

    recs = build_snapshot(source).records
    got = dict(dropdown_options(recs, {"auth": {"JWT"}, "api_type": {"MCP"}}, "api_type"))
    assert got["MCP"] == 0 and "MCP" in got
