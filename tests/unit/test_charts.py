import plotly.graph_objects as go

from tyk_analyzer.charts import pie_figure

ROWS = [("a", 9), ("b", 7), ("c", 5), ("d", 3), ("e", 1)]


def test_pie_has_one_slice_per_row_and_pulls_selected():
    fig = pie_figure("T", ROWS[:3], {"b"})
    (trace,) = fig.data
    assert isinstance(trace, go.Pie)
    assert list(trace.customdata) == ["a", "b", "c"] and list(trace.values) == [9, 7, 5]
    assert list(trace.labels) == ["a", "b", "c"]
    assert list(trace.text) == ["a", "b", "c"] and trace.textinfo == "text"  # slices: name only
    assert list(trace.pull) == [0, 0.12, 0]


def test_pie_keeps_a_selected_category_with_zero_count():
    (trace,) = pie_figure("T", ROWS[:2], {"z"}).data
    assert "z" in list(trace.customdata)




def test_fixed_height_is_honoured_for_pies_and_bars():
    from tyk_analyzer.charts import breakdown_figure

    assert pie_figure("T", ROWS, height=340).layout.height == 340
    assert breakdown_figure("T", ROWS, height=520).layout.height == 520
    assert breakdown_figure("T", ROWS).layout.height != 520


def test_pie_has_no_plotly_legend_because_the_chips_carry_the_counts():
    assert pie_figure("T", ROWS).layout.showlegend is False
