import pytest
from bson import ObjectId

from tyk_analyzer.classify import classify_active, classify_org
from tyk_analyzer.model import ActiveState, Organization, OrgStatus

ORGS = {"687a64bbcd28f000015d2514": Organization("687a64bbcd28f000015d2514", "perimeter")}


def test_matched_org_uses_name():
    assert classify_org({"org_id": "687a64bbcd28f000015d2514"}, ORGS) == ("perimeter", OrgStatus.MATCHED, [])


@pytest.mark.parametrize("doc", [{}, {"org_id": ""}, {"org_id": None}])
def test_missing_org_is_not_set(doc):
    assert classify_org(doc, ORGS) == ("Not set", OrgStatus.NOT_SET, [])


def test_unknown_org_is_unmatched_with_reason():
    label, status, reasons = classify_org({"org_id": "abc"}, ORGS)
    assert (label, status, reasons) == ("abc (unmatched)", OrgStatus.UNMATCHED, ["org_unmatched"])


def test_non_string_org_id_is_coerced():
    oid = ObjectId("687a64bbcd28f000015d2514")
    assert classify_org({"org_id": oid}, ORGS)[1] is OrgStatus.MATCHED


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, ActiveState.ACTIVE), (False, ActiveState.INACTIVE), (None, ActiveState.UNKNOWN), ("yes", ActiveState.UNKNOWN), (1, ActiveState.UNKNOWN)],
)
def test_active_states(value, expected):
    assert classify_active({"active": value}) is expected


def test_missing_active_is_unknown():
    assert classify_active({}) is ActiveState.UNKNOWN
