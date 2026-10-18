"""Plotly figures built from category counts."""

from collections.abc import Collection

import plotly.graph_objects as go

BASE = "#4f7cac"
SELECTED = "#e07a2f"
BAR_HEIGHT = 28


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
    colors = [SELECTED if label in selected else BASE for label in labels]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=values,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x} APIs<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig.update_xaxes(showgrid=False, visible=False)
    fig.update_layout(
        title=dict(text=title, x=0),
        height=height or max(160, BAR_HEIGHT * len(rows) + 90),
        margin=dict(l=0, r=40, t=50, b=10),
        showlegend=False,
        clickmode="event+select",
        dragmode=False,
    )
    return fig


def pie_figure(
    title: str,
    rows: list[tuple[str, int]],
    selected: Collection[str] = (),
    height: int | None = None,
) -> go.Figure:
    """Pie chart labelled with counts. Click a slice to select its category."""
    rows = [(label, n) for label, n in with_selected(rows, selected) if n > 0 or label in selected]
    labels = [label for label, _ in rows]
    values = [n for _, n in rows]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            customdata=labels,
            sort=False,
            pull=[0.12 if label in selected else 0 for label in labels],
            textinfo="value",
            hovertemplate="%{label}: %{value} APIs<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=title, x=0),
        height=height or max(260, BAR_HEIGHT * min(len(rows), 10) + 120),
        margin=dict(l=0, r=0, t=50, b=10),
        legend=dict(orientation="h", x=0, y=-0.05, yanchor="top"),
        clickmode="event+select",
    )
    return fig
