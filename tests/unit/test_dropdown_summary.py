from tyk_analyzer.filters import selection_summary


def test_nothing_selected_reads_all():
    assert selection_summary("API types", []) == "All API types"
    assert selection_summary("organizations", set()) == "All organizations"


def test_one_selected_shows_its_name():
    assert selection_summary("API types", ["TCP"]) == "TCP"


def test_several_selected_show_a_count():
    assert selection_summary("API types", ["TCP", "MCP"]) == "2 selected"
    assert selection_summary("authentication", ["JWT", "Basic", "API key"]) == "3 selected"


def test_a_long_name_is_shortened():
    got = selection_summary("organizations", ["a-very-long-organization-name-that-would-not-fit"])
    assert len(got) <= 24 and got.endswith("…")
