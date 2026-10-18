import pytest
from tests.conftest import InMemorySource, load_fixture

from tyk_analyzer.classify import classify_middleware
from tyk_analyzer.filters import counts
from tyk_analyzer.snapshot import build_snapshot

GLOBAL_CLASSIC = {
    "Cache", "CORS", "Rate limit (API)", "Context variables", "IP allow list", "IP block list",
    "Batch requests", "Traffic logs", "Do not track", "Event handlers", "Uptime tests",
    "Strip listen path", "Custom domain", "Request header transform", "Response header transform",
    "Override target",
}
ENDPOINT_CLASSIC = {
    "Allow list", "Block list", "Ignore authentication", "Cache", "Circuit breaker", "Enforce timeout",
    "Rate limit", "Request size limit", "URL rewrite", "Validate request", "Virtual endpoint",
    "Method transform", "Body transform", "Request header transform", "Response header transform",
    "Track endpoint", "Do not track endpoint", "Internal endpoint",
}
GLOBAL_OAS = {
    "Cache", "CORS", "Context variables", "Traffic logs", "Request header transform",
    "Response header transform", "Rate limit (API)", "Custom domain", "Event handlers", "Strip listen path",
}
ENDPOINT_OAS = (ENDPOINT_CLASSIC - {"Method transform"}) | {"Mock response"}


@pytest.fixture(scope="module")
def docs():
    return {d["name"]: d for d in load_fixture("middleware.json")}


@pytest.mark.parametrize(
    ("name", "glob", "endpoint"),
    [
        ("classic-global", GLOBAL_CLASSIC, set()),
        ("classic-endpoint", set(), ENDPOINT_CLASSIC),
        ("oas-global", GLOBAL_OAS, set()),
        ("oas-endpoint", set(), ENDPOINT_OAS),
        ("nothing-enabled", set(), set()),
        ("oas-disabled", set(), set()),
        ("wrong-types", set(), set()),
        ("wrong-types-2", set(), set()),
        ("several", {"CORS", "Cache"}, {"Cache", "Circuit breaker"}),
    ],
)
def test_middleware_names(docs, name, glob, endpoint):
    assert classify_middleware(docs[name]) == (frozenset(glob), frozenset(endpoint))


def test_same_middleware_has_same_name_in_both_styles(docs):
    classic = classify_middleware(docs["classic-global"])[0]
    oas = classify_middleware(docs["oas-global"])[0]
    assert {"Cache", "CORS", "Context variables"} <= classic & oas


def test_non_mapping_input_does_not_raise():
    assert classify_middleware(None) == (frozenset(), frozenset())  # type: ignore[arg-type]


def test_counts_count_an_api_once_per_middleware():
    snap = build_snapshot(InMemorySource(load_fixture("middleware.json"), []))
    cache = dict(counts(snap.records, "mw_endpoint"))["Cache"]
    assert cache == 3  # classic-endpoint, oas-endpoint, several (two versions still count once)
    assert "Allow list" in dict(counts(snap.records, "mw_endpoint"))
    nothing = next(r for r in snap.records if r.name == "nothing-enabled")
    assert nothing.mw_global == frozenset() and nothing.mw_endpoint == frozenset()
    assert nothing.evidence["global middleware"] == "(none)"
