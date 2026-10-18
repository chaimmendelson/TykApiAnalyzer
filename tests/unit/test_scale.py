import copy
import time

from conftest import InMemorySource
from tyk_analyzer.filters import DIMENSIONS, counts
from tyk_analyzer.snapshot import build_snapshot


def test_ten_thousand_apis_classify_and_count_quickly(api_docs, org_docs):
    docs = []
    for i in range(10_000):
        doc = copy.deepcopy(api_docs[i % len(api_docs)])
        doc["_id"] = f"scale-{i}"
        docs.append(doc)
    started = time.monotonic()
    snap = build_snapshot(InMemorySource(docs, org_docs))
    for dim in DIMENSIONS:
        counts(snap.records, dim)
    elapsed = time.monotonic() - started
    assert len(snap.records) == 10_000
    # SC-005 allows 15 s end to end including the database read.
    assert elapsed < 5, f"{elapsed:.2f}s"
