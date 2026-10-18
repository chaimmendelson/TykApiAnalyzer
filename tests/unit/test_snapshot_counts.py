from datetime import UTC

from tyk_analyzer.filters import counts
from tyk_analyzer.model import ApiType, AuthMethod, OrgStatus
from tyk_analyzer.snapshot import build_snapshot


def as_dict(rows):
    return dict(rows)


def test_snapshot_contains_every_document(source, api_docs):
    snap = build_snapshot(source)
    assert len(snap.records) == len(api_docs) == 21
    assert len({r.id for r in snap.records}) == 21


def test_non_auth_dimensions_sum_to_total(source):
    snap = build_snapshot(source)
    for dim in ("api_type", "org"):
        assert sum(n for _, n in counts(snap.records, dim)) == len(snap.records), dim


def test_authentication_counts_each_method_per_api_and_may_exceed_total(source):
    snap = build_snapshot(source)
    auth = as_dict(counts(snap.records, "auth"))
    assert sum(auth.values()) > len(snap.records)
    assert auth[AuthMethod.API_KEY.value] == 3  # rest-oas, mcp, multi-auth
    assert auth[AuthMethod.NONE.value] == 11
    assert auth[AuthMethod.NOT_SET.value] == 2  # no-auth-flags, empty document


def test_api_type_counts(source):
    types = as_dict(counts(build_snapshot(source).records, "api_type"))
    assert types == {
        ApiType.REST_CLASSIC.value: 9,
        ApiType.REST_OAS.value: 3,
        ApiType.GRAPHQL.value: 1,
        ApiType.UDG.value: 1,
        ApiType.FEDERATION.value: 1,
        ApiType.MCP.value: 1,
        ApiType.STREAMING.value: 1,
        ApiType.TCP.value: 2,
        ApiType.NOT_UNDERSTOOD.value: 2,
    }


def test_counts_are_sorted_descending(source):
    rows = counts(build_snapshot(source).records, "api_type")
    assert [n for _, n in rows] == sorted((n for _, n in rows), reverse=True)


def test_organization_counts_and_labels(source):
    orgs = as_dict(counts(build_snapshot(source).records, "org"))
    assert orgs == {
        "perimeter": 13,
        "acme": 6,
        "Not set": 1,
        "ffffffffffffffffffffffff (unmatched)": 1,
    }


def test_organization_name_falls_back_to_slug_then_id(source):
    orgs = build_snapshot(source).organizations
    assert orgs["687a64bbcd28f000015d2515"].name == "acme"
    assert orgs["687a64bbcd28f000015d2516"].name == "687a64bbcd28f000015d2516"


def test_coverage(source):
    cov = build_snapshot(source).coverage
    assert cov.total == 21
    assert cov.unclassified_count == 5
    assert cov.by_reason == {"api_type": 2, "auth": 1, "auth_oas_mismatch": 1, "org_unmatched": 1}


def test_loaded_at_is_utc(source):
    assert build_snapshot(source).loaded_at.tzinfo == UTC


def test_records_carry_evidence_not_documents(source):
    rec = next(r for r in build_snapshot(source).records if r.name == "tls")
    assert rec.evidence["protocol"] == "tls"
    assert rec.org_status is OrgStatus.MATCHED
    assert all(isinstance(v, str) and len(v) < 200 for v in rec.evidence.values())
