"""Streamlit entry point. All logic lives in the other modules; this only wires the UI."""

import logging

import pandas as pd
import streamlit as st

from tyk_analyzer.charts import breakdown_figure, pie_figure
from tyk_analyzer.config import ConfigError, Settings, load_dotenv, load_settings, redact
from tyk_analyzer.filters import (
    DIMENSIONS,
    TITLES,
    apply_selection,
    counts,
    counts_with_selection,
)
from tyk_analyzer.model import ApiRecord, Snapshot
from tyk_analyzer.snapshot import build_snapshot
from tyk_analyzer.source import MongoApiSource, SourceError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

PIE_DIMS = ("api_type", "active", "auth")
BAR_DIMS = ("mw_global", "mw_endpoint")
PIE_HEIGHT = 340
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


def _point_label(point: dict) -> str | None:
    """Category of a clicked bar (y) or pie slice (customdata or label)."""
    for key in ("y", "customdata", "label"):
        value = point.get(key)
        if isinstance(value, list):
            value = value[0] if value else None
        if value is not None:
            return str(value)
    return None


def _chart_selection(dim: str) -> set[str]:
    state = st.session_state.get(_chart_key(dim))
    try:
        points = state["selection"]["points"]
    except (TypeError, KeyError):
        return set()
    picked = {_point_label(p) for p in points}
    picked.discard(None)
    return picked


def _current_selection(snapshot: Snapshot) -> dict[str, set[str]]:
    selection = {d: _chart_selection(d) for d in CHART_DIMS}
    selection["org"] = set(st.session_state.get(_widget_key("org", "orgpick"), []))
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
.block-container { padding-top: 4rem; }
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
    """Compact sticky bar: title, organization filter, refresh, clear all, chips (FR-006e)."""
    with st.container(key="topbar"):
        title, org, refresh, clear = st.columns([3, 7, 1.2, 1.2], vertical_alignment="center")
        with title:
            st.markdown("**Tyk Configuration Analytics**")
            if snapshot:
                st.caption(f"Data loaded at {snapshot.loaded_at:%Y-%m-%d %H:%M:%S} UTC")
        if snapshot and snapshot.records and not st.session_state.error:
            with org:
                _org_filter(snapshot.records)
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
        if selection:
            for col, (dim, values) in zip(st.columns(len(selection) + 1), selection.items(), strict=False):
                col.button(
                    f"{TITLES[dim]}: {', '.join(sorted(values))} ✕",
                    key=f"chip_{dim}_{st.session_state.epochs[dim]}",
                    on_click=_clear,
                    args=([dim],),
                )


def _org_filter(records: list[ApiRecord]) -> None:
    """Organization multiselect; the only way to select an organization (FR-006d)."""
    totals = counts(records, "org")
    count_of = dict(totals)
    st.multiselect(
        "Organization",
        [label for label, _ in totals],
        key=_widget_key("org", "orgpick"),
        format_func=lambda label: f"{label} ({count_of[label]:,})",
        placeholder="All organizations",
        label_visibility="collapsed",
    )


def _summary(snapshot: Snapshot, shown: list[ApiRecord]) -> None:
    """One small line of text; scrolls with the page."""
    total = len(snapshot.records)
    active = sum(1 for r in shown if r.active.value == "Active")
    inactive = sum(1 for r in shown if r.active.value == "Inactive")
    cov = snapshot.coverage
    st.caption(
        f"**{len(shown):,}** of {total:,} APIs · **{active:,}** active · **{inactive:,}** inactive · "
        f"**{cov.unclassified_count:,}** unclassified"
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
    draw = pie_figure if dim in PIE_DIMS else breakdown_figure
    fig = draw(TITLES[dim], rows, picked, height=height)
    st.plotly_chart(fig, key=_chart_key(dim), on_select="rerun", selection_mode="points", width="stretch")
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
    st.subheader("Matching APIs")
    if not shown:
        st.info("No matching APIs.")
        st.button("Clear all", on_click=_clear, args=(list(DIMENSIONS),), key="clear_nomatch")
        return
    total = len(st.session_state.snapshot.records)
    st.caption(f"Showing {len(shown):,} of {total:,}")
    df = pd.DataFrame(
        {
            "Name": [r.name for r in shown],
            "API type": [r.api_type.value for r in shown],
            "TLS": ["Yes" if r.tls_enabled else "" for r in shown],
            "Active": [r.active.value for r in shown],
            "Authentication": [", ".join(sorted(m.value for m in r.auth_methods)) for r in shown],
            "Organization": [r.org_label for r in shown],
        }
    )
    event = st.dataframe(
        df, hide_index=True, width="stretch", height=360,
        on_select="rerun", selection_mode="single-row", key="api_table",
    )
    rows = event.selection.rows if event and event.selection else []
    if rows:
        rec = shown[rows[0]]
        with st.container(border=True):
            st.markdown(f"**{rec.name or '(unnamed)'}** · `{rec.api_id or rec.id}`")
            st.write(
                f"API type: **{rec.api_type.value}** · Active: **{rec.active.value}** · "
                f"Organization: **{rec.org_label}**"
            )
            st.caption("Values the classification is based on:")
            st.table(pd.DataFrame({"Field": list(rec.evidence), "Value": list(rec.evidence.values())}).set_index("Field"))
            if rec.unclassified:
                st.warning("Unclassified: " + ", ".join(rec.unclassified))


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
    _charts(snapshot, selection)
    _table(shown)


main()
