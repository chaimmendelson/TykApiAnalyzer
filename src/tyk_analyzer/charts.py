"""Plotly figures built from category counts."""

from collections.abc import Collection

import plotly.graph_objects as go

BASE = "#4f7cac"
SELECTED = "#2a8f86"  # same teal as .streamlit/config.toml primaryColor
BAR_HEIGHT = 28
DIMMED_OPACITY = 0.35
# Charts are for reading and clicking only: no pan, zoom, drag handles or toolbar.
STATIC_CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showAxisDragHandles": False}
PIE_COLOURS = (  # muted blues, greens and neutrals: nothing red or orange
    "#4f7cac", "#7fa3c7", "#5f9ea0", "#9bb7a0", "#c9b27c",
    "#a58fb3", "#8d9db6", "#b8a89a", "#6b8e9f", "#c4a1a1",
)


def with_selected(rows: list[tuple[str, int]], selected: Collection[str]) -> list[tuple[str, int]]:
    """Keep selected categories visible (with 0) even when other filters remove all their APIs."""
    present = {label for label, _ in rows}
    return rows + [(label, 0) for label in sorted(selected) if label not in present]


def breakdown_figure(
    title: str,
    rows: list[tuple[str, int]],
    selected: Collection[str] = (),
    height: int | None = None,
) -> go.Figure:
    """Horizontal bar chart, largest on top. Click a bar to select its category."""
    rows = with_selected(rows, selected)
    labels = [label for label, _ in rows]
    values = [n for _, n in rows]
    # With a selection, unselected bars are dimmed so the selected ones stand out (FR-006g). The
    # dimming is in the colour's alpha: a per-bar marker.opacity array stops Plotly from reporting clicks.
    colors = [
        _rgba(SELECTED if label in selected else BASE, 1.0 if label in selected or not selected else DIMMED_OPACITY)
        for label in labels
    ]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=colors),
            text=values,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x} APIs<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", automargin=True, fixedrange=True)
    fig.update_xaxes(showgrid=False, visible=False, fixedrange=True)
    fig.update_layout(
        title=dict(text=title, x=0),
        height=height or max(160, BAR_HEIGHT * len(rows) + 90),
        margin=dict(l=0, r=40, t=50, b=10),
        showlegend=False,
        clickmode="event+select",
        dragmode=False,
    )
    return fig


def _rgba(hex_colour: str, opacity: float) -> str:
    r, g, b = (int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {opacity})"


def pie_figure(
    title: str,
    rows: list[tuple[str, int]],
    selected: Collection[str] = (),
    height: int | None = None,
) -> go.Figure:
    """Pie chart: slices show the name; counts are in the hover and in the chips under the pie."""
    rows = [(label, n) for label, n in with_selected(rows, selected) if n > 0 or label in selected]
    labels = [label for label, _ in rows]
    values = [n for _, n in rows]
    colours = [_rgba(PIE_COLOURS[i % len(PIE_COLOURS)], 1.0 if label in selected or not selected else DIMMED_OPACITY)
               for i, label in enumerate(labels)]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            customdata=labels,
            text=labels,
            textinfo="text",
            textposition="auto",
            marker=dict(colors=colours),
            sort=False,
            pull=[0.12 if label in selected else 0 for label in labels],
            hovertemplate="%{customdata}: %{value:,} APIs (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=title, x=0),
        height=height or max(260, BAR_HEIGHT * min(len(rows), 10) + 120),
        margin=dict(l=0, r=0, t=50, b=10),
        showlegend=False,
        uniformtext=dict(minsize=9, mode="hide"),
        clickmode="event",
    )
    return fig
