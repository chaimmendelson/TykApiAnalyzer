"""Clickable pie chart drawn as inline SVG by a small Streamlit component (FR-006f, FR-006g).

Plotly pies cannot report slice clicks to Streamlit, so the pie is drawn here instead. Geometry
and selection logic are pure functions; the component's JavaScript only draws what it is given
and reports which slice was clicked. Category names are written with `textContent`, never as markup.
"""

import math
from collections.abc import Collection

PALETTE = (
    "#4f7cac", "#e07a2f", "#59a14f", "#b07aa1", "#edc948",
    "#76b7b2", "#ff9da7", "#9c755f", "#bab0ac", "#e15759",
)
CENTER = 150.0
RADIUS = 120.0
PULL = 14.0
MIN_LABEL_DEGREES = 20.0
DIMMED_OPACITY = 0.35


def toggle(selected: Collection[str], label: str) -> list[str]:
    """Add `label` when absent, remove it when present (FR-006f)."""
    current = list(selected)
    return [s for s in current if s != label] if label in current else current + [label]


def slice_geometry(rows: list[tuple[str, int]]) -> list[tuple[float, float]]:
    """(start, end) angle in degrees per row, clockwise from 12 o'clock, covering 360 in total."""
    total = sum(n for _, n in rows)
    if total <= 0:
        return [(0.0, 0.0) for _ in rows]
    out, start = [], 0.0
    for _, n in rows:
        end = start + 360.0 * n / total
        out.append((start, end))
        start = end
    return out


def _point(angle: float, radius: float) -> tuple[float, float]:
    rad = math.radians(angle - 90.0)
    return CENTER + radius * math.cos(rad), CENTER + radius * math.sin(rad)


def slice_path(start: float, end: float, radius: float = RADIUS) -> str:
    """SVG path for one slice; a full circle when the slice covers everything."""
    if end - start >= 359.999:
        return (
            f"M {CENTER - radius:.2f} {CENTER:.2f} "
            f"a {radius:.2f} {radius:.2f} 0 1 0 {2 * radius:.2f} 0 "
            f"a {radius:.2f} {radius:.2f} 0 1 0 {-2 * radius:.2f} 0 Z"
        )
    x0, y0 = _point(start, radius)
    x1, y1 = _point(end, radius)
    large = 1 if end - start > 180.0 else 0
    return f"M {CENTER:.2f} {CENTER:.2f} L {x0:.2f} {y0:.2f} A {radius:.2f} {radius:.2f} 0 {large} 1 {x1:.2f} {y1:.2f} Z"


def _text_colour(background: str) -> str:
    r, g, b = (int(background[i : i + 2], 16) for i in (1, 3, 5))
    return "#111111" if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "#ffffff"


def pie_data(rows: list[tuple[str, int]], selected: Collection[str] = (), height: int = 300) -> dict:
    """Everything the component needs to draw the pie, ready to serialise."""
    total = sum(n for _, n in rows)
    chosen = set(selected)
    slices = []
    for i, ((label, n), (start, end)) in enumerate(zip(rows, slice_geometry(rows), strict=True)):
        colour = PALETTE[i % len(PALETTE)]
        mid = (start + end) / 2.0
        is_selected = label in chosen
        dx, dy = (_point(mid, PULL)[0] - CENTER, _point(mid, PULL)[1] - CENTER) if is_selected and end - start < 359.999 else (0.0, 0.0)
        lx, ly = _point(mid, RADIUS * 0.62)
        slices.append(
            {
                "label": label,
                "path": slice_path(start, end),
                "colour": colour,
                "text_colour": _text_colour(colour),
                "selected": is_selected,
                "dimmed": bool(chosen) and not is_selected,
                "dx": round(dx, 2),
                "dy": round(dy, 2),
                "text": {"x": round(lx, 2), "y": round(ly, 2)} if end - start >= MIN_LABEL_DEGREES else None,
                "title": f"{label}: {n:,} APIs ({100.0 * n / total:.1f}%)" if total else label,
            }
        )
    return {"slices": slices, "height": height, "dimmed_opacity": DIMMED_OPACITY}


_CSS = """
.pie { width: 100%; display: flex; justify-content: center; }
.pie svg { max-width: 100%; }
.pie path { cursor: pointer; stroke: var(--st-background-color, rgba(128,128,128,0.4)); stroke-width: 1.5; transition: opacity 120ms, transform 120ms; }
.pie path:hover { filter: brightness(1.12); }
.pie text { pointer-events: none; font: 12px system-ui, sans-serif; text-anchor: middle; dominant-baseline: middle; }
"""

_JS = """
export default function (component) {
    const { data, setTriggerValue, parentElement } = component;
    const root = parentElement.querySelector('.pie');
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 300 300');
    svg.setAttribute('height', String(data.height));
    for (const s of data.slices) {
        const g = document.createElementNS(NS, 'g');
        g.setAttribute('transform', `translate(${s.dx} ${s.dy})`);
        g.setAttribute('opacity', s.dimmed ? String(data.dimmed_opacity) : '1');
        g.dataset.label = s.label;
        g.dataset.selected = String(s.selected);
        g.dataset.dimmed = String(s.dimmed);
        const path = document.createElementNS(NS, 'path');
        path.setAttribute('d', s.path);
        path.setAttribute('fill', s.colour);
        const title = document.createElementNS(NS, 'title');
        title.textContent = s.title;
        path.appendChild(title);
        path.addEventListener('click', () => setTriggerValue('clicked', s.label));
        g.appendChild(path);
        if (s.text) {
            const t = document.createElementNS(NS, 'text');
            t.setAttribute('x', s.text.x);
            t.setAttribute('y', s.text.y);
            t.setAttribute('fill', s.text_colour);
            t.textContent = s.label;
            g.appendChild(t);
        }
        svg.appendChild(g);
    }
    root.replaceChildren(svg);
}
"""


def render_pie(key: str, rows: list[tuple[str, int]], selected: Collection[str], height: int, on_click) -> None:
    """Mount the pie; `on_click` runs (before the rerun) when a slice is clicked."""
    import streamlit as st

    pie = st.components.v2.component("tyk_pie", html='<div class="pie"></div>', css=_CSS, js=_JS)
    pie(data=pie_data(rows, selected, height), key=key, on_clicked_change=on_click)
