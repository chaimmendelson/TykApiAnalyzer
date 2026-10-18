from datetime import timedelta

import pytest

from conftest import InMemorySource
from tyk_analyzer.snapshot import build_snapshot
from tyk_analyzer.source import SourceError


def test_source_failure_raises_and_returns_nothing(api_docs, org_docs):
    failing = InMemorySource(api_docs, org_docs, error="Could not read 'tyk_apis'")
    with pytest.raises(SourceError):
        build_snapshot(failing)


def test_empty_source_gives_empty_snapshot():
    snap = build_snapshot(InMemorySource([], []))
    assert snap.records == [] and snap.organizations == {}
    assert snap.coverage.total == 0 and snap.coverage.unclassified_count == 0
    assert snap.coverage.by_reason == {}


def test_loaded_at_moves_forward_on_each_build(source):
    first = build_snapshot(source)
    second = build_snapshot(source)
    assert second.loaded_at >= first.loaded_at
    assert second.loaded_at - first.loaded_at < timedelta(seconds=5)


def test_refresh_reflects_changed_source(api_docs, org_docs):
    src = InMemorySource(api_docs[:5], org_docs)
    assert len(build_snapshot(src).records) == 5
    src._apis = api_docs
    assert len(build_snapshot(src).records) == len(api_docs)


def test_reasons_count_each_api_once(source):
    by_reason = build_snapshot(source).coverage.by_reason
    assert by_reason["org_unmatched"] == 1 and by_reason["api_type"] == 2
