"""Streamlit entry point. All logic lives in the other modules; this only wires the UI."""

import logging

import pandas as pd
import streamlit as st

from tyk_analyzer.charts import STATIC_CHART_CONFIG, breakdown_figure, pie_figure, with_selected
from tyk_analyzer.config import ConfigError, Settings, load_dotenv, load_settings, redact
from tyk_analyzer.filters import (
    DIMENSIONS,
    TITLES,
    apply_selection,
    counts_with_selection,
    dropdown_options,
    selection_summary,
    toggle,
)
from tyk_analyzer.model import ApiRecord, Snapshot
from tyk_analyzer.snapshot import build_snapshot
from tyk_analyzer.source import MongoApiSource, SourceError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

PIE_DIMS = ("api_type", "auth")
DROPDOWN_DIMS = ("org", "api_type", "auth", "mw_global", "mw_endpoint")
BAR_DIMS = ("mw_global", "mw_endpoint")
PIE_HEIGHT = 340
TABLE_HEIGHT = 580
DROPDOWN_LIST_HEIGHT = 300
BAR_ROW_HEIGHT = 520
CHART_DIMS = PIE_DIMS + BAR_DIMS
MIDDLEWARE_DIMS = ("mw_global", "mw_endpoint")


@st.cache_resource
def _source(settings: Settings) -> MongoApiSource:
    # Caches the connection pool only. Data is never cached (constitution VI).
    return MongoApiSource(settings)


def _load(settings: Settings | None, config_error: str | None) -> None:
    """Replace the snapshot. On any failure, drop it so stale data is never shown."""
    st.session_state.snapshot = None
    st.session_state.error = None
    # New widget keys drop every selection; bumping (not resetting) keeps old keys from returning.
    previous = st.session_state.get("epochs")
    st.session_state.epochs = {d: (previous[d] + 1 if previous else 0) for d in DIMENSIONS}
    if settings is None:
        st.session_state.error = config_error
        return
    try:
        with st.spinner("Loading API definitions…"):
            st.session_state.snapshot = build_snapshot(_source(settings))
    except SourceError as exc:
        st.session_state.error = str(exc)
    except Exception as exc:
        logging.getLogger(__name__).exception("unexpected failure while loading")
        st.session_state.error = redact(f"Unexpected error: {type(exc).__name__}", settings.secrets)


def _chart_key(dim: str) -> str:
    return f"chart_{dim}_{st.session_state.epochs[dim]}"


def _widget_key(dim: str, name: str) -> str:
    return f"{name}_{dim}_{st.session_state.epochs[dim]}"


def _bar_chart_key(dim: str) -> str:
    # The click counter is part of the key: each click remounts the chart so Plotly's own
    # one-bar selection is forgotten and our toggled selection is the only source of truth.
    clicks = st.session_state.setdefault("bar_clicks", {}).get(dim, 0)
    return f"chart_{dim}_{st.session_state.epochs[dim]}_{clicks}"


def _sel_key(dim: str) -> str:
    """The one stored selection per dimension; dropdown, chips and bar clicks all read and write it."""
    return _widget_key(dim, "sel")


def _selected(dim: str) -> list[str]:
    return list(st.session_state.get(_sel_key(dim)) or [])


def _sync_widget(dim: str, name: str) -> str:
    """Point a widget's own state at the stored selection before it is drawn; returns its key."""
    key = _widget_key(dim, name)
    st.session_state[key] = _selected(dim)
    return key


def _store_from_widget(dim: str, name: str) -> None:
    """on_change: a widget changed, so its value becomes the stored selection."""
    st.session_state[_sel_key(dim)] = list(st.session_state.get(_widget_key(dim, name)) or [])


def _on_bar_click(dim: str) -> None:
    """Toggle the clicked bar(s) in the dimension's selection (FR-006f)."""
    state = st.session_state.get(_bar_chart_key(dim))
    try:
        points = state["selection"]["points"]
    except (TypeError, KeyError):
        return
    key = _sel_key(dim)
    chosen = _selected(dim)
    for point in points:
        label = point.get("y")
        if label is not None:
            chosen = toggle(chosen, str(label))
    st.session_state[key] = chosen
    st.session_state["bar_clicks"][dim] = st.session_state["bar_clicks"].get(dim, 0) + 1


def _current_selection(snapshot: Snapshot) -> dict[str, set[str]]:
    selection = {d: set(_selected(d)) for d in DIMENSIONS}
    return {d: v for d, v in selection.items() if v}


def _clear(dims) -> None:
    for d in dims:
        st.session_state.epochs[d] += 1


_STICKY_CSS = """
<style>
/* Streamlit wraps keyed containers in a layout wrapper, and sticky only works on that wrapper. */
[data-testid="stLayoutWrapper"]:has(> .st-key-topbar) {
    position: sticky; top: 3.75rem; z-index: 999;
    background: %(bg)s;
    border-bottom: 1px solid rgba(128, 128, 128, 0.35);
    padding: 0.35rem 0;
}
.st-key-topbar [data-testid="stCaptionContainer"] { margin: 0; line-height: 1.1; }
.st-key-topbar p { margin: 0; }
/* st.pills scrolls sideways by default; let the name · count chips wrap so every category is reachable. */
[data-testid="stButtonGroup"] > div { flex-wrap: wrap; overflow: visible; height: auto; }
.block-container { padding-top: 4rem; }
/* The detail panel stays in view under the sticky top bar while the table scrolls (FR-006k). The row
   stretches so the panel's wrapper has room to stick; narrow screens stack it below the table. */
[data-testid="stHorizontalBlock"]:has(.st-key-detail) { align-items: stretch; }
[data-testid="stColumn"]:has(.st-key-detail) > [data-testid="stVerticalBlock"] { height: 100%%; }
[data-testid="stLayoutWrapper"]:has(> .st-key-detail) {
    position: sticky; top: 11rem; z-index: 5;
    max-height: calc(100vh - 12rem); overflow-y: auto;
    background: %(bg)s;
}
@media (max-width: 900px) {
    [data-testid="stLayoutWrapper"]:has(> .st-key-detail) { position: static; max-height: none; }
}
</style>
"""

_THEME_BACKGROUNDS = {"dark": "#0e1117", "light": "#ffffff"}


def _sticky_css() -> str:
    """Opaque bar background that matches the active Streamlit theme (no white box in dark mode)."""
    try:
        theme = st.context.theme.type
    except (AttributeError, KeyError):
        theme = None
    return _STICKY_CSS % {"bg": _THEME_BACKGROUNDS.get(theme, "Canvas")}


def _topbar(
    settings: Settings | None,
    config_error: str | None,
    snapshot: Snapshot | None,
    selection: dict[str, set[str]],
) -> None:
    """Sticky bar: row 1 title, refresh, clear all; row 2 one dropdown per dimension (FR-006i)."""
    ready = bool(snapshot and snapshot.records and not st.session_state.error)
    with st.container(key="topbar"):
        title, refresh, clear = st.columns([8, 1.3, 1.3], vertical_alignment="center")
        with title:
            st.markdown("**Tyk Configuration Analytics**")
            if snapshot:
                st.caption(f"Data loaded at {snapshot.loaded_at:%Y-%m-%d %H:%M:%S} UTC")
        if ready:
            clear.button(
                "Clear all",
                disabled=not selection,
                on_click=_clear,
                args=(list(DIMENSIONS),),
                key="clear_all_bar",
                width="stretch",
            )
        if refresh.button("Refresh", icon=":material/refresh:", width="stretch"):
            _load(settings, config_error)
            st.rerun()
        if ready:
            for col, dim in zip(st.columns(len(DROPDOWN_DIMS)), DROPDOWN_DIMS, strict=True):
                with col:
                    _dropdown(snapshot.records, selection, dim)


_NOUNS = {
    "org": "organizations",
    "api_type": "API types",
    "auth": "authentication",
    "mw_global": "global middleware",
    "mw_endpoint": "per-endpoint middleware",
}


def _toggle_category(dim: str, label: str) -> None:
    """on_change of a checkbox: add or remove that category in the stored selection (FR-006n)."""
    st.session_state[_sel_key(dim)] = toggle(_selected(dim), label)


def _clear_dropdown(dim: str) -> None:
    """Clear button: untick everything in this dropdown only (no filter for the dimension)."""
    st.session_state[_sel_key(dim)] = []


def _dropdown(records: list[ApiRecord], selection: dict[str, set[str]], dim: str) -> None:
    """Popup with a Clear button and a checkbox per category, counts following the other filters."""
    options = dropdown_options(records, selection, dim)
    chosen = set(_selected(dim))
    with st.popover(selection_summary(_NOUNS[dim], chosen), width="stretch", key=f"popover_{dim}"):
        st.button(
            "Clear",
            key=f"clear_{dim}_{st.session_state.epochs[dim]}",
            on_click=_clear_dropdown,
            args=(dim,),
            disabled=not chosen,
            width="stretch",
        )
        with st.container(height=min(DROPDOWN_LIST_HEIGHT, 40 * len(options) + 8), border=False):
            for index, (label, count) in enumerate(options):
                key = f"cb_{dim}_{st.session_state.epochs[dim]}_{index}"
                st.session_state[key] = label in chosen
                st.checkbox(
                    f"{label} ({count:,})",
                    key=key,
                    on_change=_toggle_category,
                    args=(dim, label),
                )


def _summary(snapshot: Snapshot, shown: list[ApiRecord]) -> None:
    """One small line of text; scrolls with the page."""
    total = len(snapshot.records)
    cov = snapshot.coverage
    st.caption(
        f"**{len(shown):,}** of {total:,} APIs · **{cov.unclassified_count:,}** unclassified"
    )
    if cov.unclassified_count:
        with st.popover(f"{cov.unclassified_count:,} of {cov.total:,} APIs have unclassified settings"):
            names = {
                "api_type": "API type not understood",
                "auth": "Authentication value not understood",
                "auth_oas_mismatch": "OpenAPI authentication disagrees with the flags",
                "org_unmatched": "Organization not found",
            }
            for reason, n in sorted(cov.by_reason.items(), key=lambda kv: -kv[1]):
                st.write(f"**{n:,}** · {names.get(reason, reason)}")


def _chart(records: list[ApiRecord], selection: dict[str, set[str]], dim: str, height: int) -> None:
    rows = counts_with_selection(records, selection, dim)
    picked = selection.get(dim, set())
    if dim in PIE_DIMS:
        # Plotly pies cannot report clicks to Streamlit, so the name · count chips below the pie
        # are both the legend with the numbers and the filter control.
        st.plotly_chart(pie_figure(TITLES[dim], rows, picked, height=height), key=_chart_key(dim), on_select="ignore", width="stretch", config=STATIC_CHART_CONFIG)
        count_of = dict(with_selected(rows, picked))
        st.pills(
            TITLES[dim],
            list(count_of),
            selection_mode="multi",
            key=_sync_widget(dim, "pill"),
            on_change=_store_from_widget,
            args=(dim, "pill"),
            format_func=lambda name: f"{name} · {count_of[name]:,}",
            label_visibility="collapsed",
        )
    else:
        fig = breakdown_figure(TITLES[dim], rows, picked, height=height)
        st.plotly_chart(
            fig,
            key=_bar_chart_key(dim),
            on_select=lambda d=dim: _on_bar_click(d),
            selection_mode="points",
            width="stretch",
            config=STATIC_CHART_CONFIG,
        )
    if dim == "auth":
        st.caption("An API can use several methods, so counts may exceed the total.")
    if dim in MIDDLEWARE_DIMS:
        st.caption("An API can use several middleware, so counts may exceed the total.")


def _charts(snapshot: Snapshot, selection: dict[str, set[str]]) -> None:
    """Row of three equal pies, then row of two equal bar charts (FR-006d)."""
    for dims, height in ((PIE_DIMS, PIE_HEIGHT), (BAR_DIMS, BAR_ROW_HEIGHT)):
        for col, dim in zip(st.columns(len(dims)), dims, strict=True):
            with col:
                _chart(snapshot.records, selection, dim, height)


def _table(shown: list[ApiRecord]) -> None:
    """Matching APIs: the table on the left, the selected API's details on the right (FR-006k)."""
    if not shown:
        st.info("No matching APIs.")
        st.button("Clear all", on_click=_clear, args=(list(DIMENSIONS),), key="clear_nomatch")
        return
    total = len(st.session_state.snapshot.records)
    st.caption(f"Showing {len(shown):,} of {total:,}")  # above both columns so their tops line up
    left, right = st.columns([2, 1])
    with left:
        df = pd.DataFrame(
            {
                "Name": [r.name for r in shown],
                "API type": [r.api_type.value for r in shown],
                "Authentication": [", ".join(sorted(m.value for m in r.auth_methods)) for r in shown],
                "Organization": [r.org_label for r in shown],
            }
        )
        event = st.dataframe(
            df, hide_index=True, width="stretch", height=TABLE_HEIGHT,
            on_select="rerun", selection_mode="single-row", key="api_table",
        )
    rows = event.selection.rows if event and event.selection else []
    with right, st.container(key="detail", border=True):
        if rows:
            _detail(shown[rows[0]])
        else:
            st.info("Select an API in the table to see its details.")


def _detail(rec: ApiRecord) -> None:
    st.markdown(f"**{rec.name or '(unnamed)'}** · `{rec.api_id or rec.id}`")
    st.write(f"API type: **{rec.api_type.value}** · Organization: **{rec.org_label}**")
    if rec.unclassified:
        st.warning("Unclassified: " + ", ".join(rec.unclassified))
    st.caption("Values the classification is based on:")
    st.table(pd.DataFrame({"Field": list(rec.evidence), "Value": list(rec.evidence.values())}).set_index("Field"))


def main() -> None:
    st.set_page_config(page_title="Tyk Configuration Analytics", layout="wide")
    load_dotenv()
    try:
        settings, config_error = load_settings(), None
    except ConfigError as exc:
        settings, config_error = None, str(exc)

    st.markdown(_sticky_css(), unsafe_allow_html=True)
    if "snapshot" not in st.session_state:
        _load(settings, config_error)
    snapshot: Snapshot | None = st.session_state.get("snapshot")
    usable = bool(snapshot and snapshot.records) and not st.session_state.error
    selection = _current_selection(snapshot) if usable else {}
    _topbar(settings, config_error, snapshot, selection)

    if st.session_state.error:
        st.error(st.session_state.error)
        st.caption("Press Refresh to retry.")
        return
    if not snapshot.records:
        st.info("No Tyk API definitions found in the configured source.")
        return

    shown = apply_selection(snapshot.records, selection)
    _summary(snapshot, shown)
    overview, apis = st.tabs(["Overview", "APIs"])  # one set of filters above both (FR-006l)
    with overview:
        _charts(snapshot, selection)
    with apis:
        _table(shown)


main()
