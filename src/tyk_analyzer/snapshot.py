"""Build one in-memory snapshot of all API definitions per refresh."""

import logging
from collections import Counter
from datetime import UTC, datetime

from tyk_analyzer.classify import classify_api
from tyk_analyzer.model import Coverage, Organization, Snapshot
from tyk_analyzer.source import ApiSource

log = logging.getLogger(__name__)


def _organization(doc: dict) -> Organization:
    org_id = str(doc["_id"])
    name = (doc.get("owner_name") or "").strip() or (doc.get("owner_slug") or "").strip() or org_id
    return Organization(id=org_id, name=name)


def build_snapshot(source: ApiSource, now: datetime | None = None) -> Snapshot:
    """Read everything once and classify it. Raises SourceError on any read failure."""
    orgs = {o.id: o for o in map(_organization, source.fetch_organizations())}
    records = [classify_api(doc, orgs) for doc in source.fetch_apis()]

    reasons: Counter[str] = Counter()
    unclassified = 0
    for rec in records:
        if rec.unclassified:
            unclassified += 1
            reasons.update(set(rec.unclassified))
    coverage = Coverage(total=len(records), unclassified_count=unclassified, by_reason=dict(reasons))
    log.info("snapshot: %d APIs, %d organizations, %d unclassified", len(records), len(orgs), unclassified)
    return Snapshot(records=records, organizations=orgs, loaded_at=now or datetime.now(UTC), coverage=coverage)
