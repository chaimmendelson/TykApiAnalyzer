"""Dimensions, per-dimension counts and selection filtering over a list of ApiRecord."""

from collections import Counter
from collections.abc import Iterable, Mapping

from tyk_analyzer.model import ApiRecord

DIMENSIONS = ("api_type", "auth", "org", "mw_global", "mw_endpoint")

TITLES = {
    "api_type": "API type",
    "auth": "Authentication",
    "org": "Organization",
    "mw_global": "Global middleware",
    "mw_endpoint": "Per-endpoint middleware",
}


def labels(record: ApiRecord, dimension: str) -> list[str]:
    """The categories a record falls into for a dimension (authentication can have several)."""
    if dimension == "api_type":
        return [record.api_type.value]
    if dimension == "auth":
        return sorted(m.value for m in record.auth_methods)
    if dimension == "org":
        return [record.org_label]
    if dimension == "mw_global":
        return sorted(record.mw_global)
    if dimension == "mw_endpoint":
        return sorted(record.mw_endpoint)
    raise KeyError(dimension)


def counts(records: Iterable[ApiRecord], dimension: str) -> list[tuple[str, int]]:
    """Category counts, largest first, ties by label."""
    tally: Counter[str] = Counter()
    for rec in records:
        tally.update(labels(rec, dimension))
    return sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))


Selection = Mapping[str, Iterable[str]]


def apply_selection(
    records: Iterable[ApiRecord], selection: Selection, ignore: str | None = None
) -> list[ApiRecord]:
    """Records matching every dimension that has a selection (AND); within a dimension, OR."""
    active = {d: set(v) for d, v in selection.items() if d != ignore and v}
    if not active:
        return list(records)
    return [
        rec
        for rec in records
        if all(set(labels(rec, dim)) & wanted for dim, wanted in active.items())
    ]


def counts_with_selection(
    records: Iterable[ApiRecord], selection: Selection, dimension: str
) -> list[tuple[str, int]]:
    """Counts for one chart given the other dimensions' selections, so siblings stay visible."""
    return counts(apply_selection(records, selection, ignore=dimension), dimension)


def toggle(selected: Iterable[str], label: str) -> list[str]:
    """Add `label` when absent, remove it when present (FR-006f)."""
    current = list(selected)
    return [s for s in current if s != label] if label in current else current + [label]
