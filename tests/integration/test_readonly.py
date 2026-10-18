"""Opt-in checks against a real MongoDB.

Reads run when MONGO_URI is set. The write-rejection check additionally needs
TYK_EXPECT_READONLY=1, to be used only with the read-only account from quickstart.md.
"""

import os

import pytest
from pymongo import MongoClient
from pymongo.errors import OperationFailure

from tyk_analyzer.config import load_settings
from tyk_analyzer.snapshot import build_snapshot
from tyk_analyzer.source import MongoApiSource

pytestmark = pytest.mark.skipif(not os.environ.get("MONGO_URI"), reason="MONGO_URI not set")


def test_reads_succeed():
    snap = build_snapshot(MongoApiSource(load_settings()))
    assert snap.coverage.total == len(snap.records)
    assert len({r.id for r in snap.records}) == len(snap.records)


@pytest.mark.skipif(os.environ.get("TYK_EXPECT_READONLY") != "1", reason="TYK_EXPECT_READONLY not set")
def test_write_is_rejected_for_the_read_only_account():
    settings = load_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=settings.timeout_ms)
    probe = client[settings.mongo_db]["__tyk_analyzer_write_probe__"]
    try:
        with pytest.raises(OperationFailure):
            probe.insert_one({"probe": True})
    finally:
        client.close()
