import logging

import pytest
from test_source import SETTINGS, URI, FakeClient, FakeCollection

from conftest import InMemorySource
from tyk_analyzer.snapshot import build_snapshot
from tyk_analyzer.source import MongoApiSource, SourceError

SECRETS = (URI, "reader", "hunter2")


def assert_clean(caplog):
    text = "\n".join(r.getMessage() for r in caplog.records)
    for secret in SECRETS:
        assert secret not in text


def test_successful_load_logs_counts_not_documents(caplog, api_docs, org_docs):
    caplog.set_level(logging.DEBUG)
    colls = {"apis": FakeCollection(api_docs), "orgs": FakeCollection(org_docs)}
    build_snapshot(MongoApiSource(SETTINGS, client=FakeClient(colls)))
    assert_clean(caplog)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "rest-classic" not in text and "api_id" not in text
    assert "snapshot: 21 APIs" in text


def test_failed_load_logs_no_secrets(caplog):
    caplog.set_level(logging.DEBUG)
    colls = {
        "apis": FakeCollection(error=ConnectionError(f"cannot reach {URI}")),
        "orgs": FakeCollection(),
    }
    with pytest.raises(SourceError):
        build_snapshot(MongoApiSource(SETTINGS, client=FakeClient(colls)))
    assert_clean(caplog)


def test_in_memory_source_failure_logs_nothing_sensitive(caplog, api_docs, org_docs):
    caplog.set_level(logging.DEBUG)
    with pytest.raises(SourceError):
        build_snapshot(InMemorySource(api_docs, org_docs, error="boom"))
    assert_clean(caplog)
