import pytest

from tyk_analyzer.classify import classify_api_type
from tyk_analyzer.model import ApiType

CASES = [
    ("rest-classic", ApiType.REST_CLASSIC, False),
    ("rest-oas", ApiType.REST_OAS, False),
    ("graphql-proxy", ApiType.GRAPHQL, False),
    ("udg", ApiType.UDG, False),
    ("federation", ApiType.FEDERATION, False),
    ("mcp", ApiType.MCP, False),
    ("streaming", ApiType.STREAMING, False),
    ("tcp", ApiType.TCP, False),
    ("tls", ApiType.TCP, True),
    ("unknown-protocol", ApiType.NOT_UNDERSTOOD, False),
    ("graphql-disabled-with-mode", ApiType.REST_CLASSIC, False),
    ("bad-types", ApiType.NOT_UNDERSTOOD, False),
]


@pytest.mark.parametrize(("name", "expected", "tls"), CASES)
def test_api_type(api_by_name, name, expected, tls):
    assert classify_api_type(api_by_name[name]) == (expected, tls)


def test_graphql_disabled_never_counts_as_graphql(api_by_name):
    api_type, _ = classify_api_type(api_by_name["graphql-disabled-with-mode"])
    assert api_type not in {ApiType.GRAPHQL, ApiType.UDG, ApiType.FEDERATION}


def test_mcp_wins_over_rest_oas(api_by_name):
    assert api_by_name["mcp"]["is_oas"] is True
    assert classify_api_type(api_by_name["mcp"])[0] is ApiType.MCP


def test_federation_with_proxy_only_mode(api_by_name):
    assert api_by_name["federation"]["graphql"]["execution_mode"] == "proxyOnly"
    assert classify_api_type(api_by_name["federation"])[0] is ApiType.FEDERATION


def test_tls_is_not_a_type():
    assert "TLS" not in {t.name for t in ApiType}
    assert "TLS" not in {t.value for t in ApiType}


def test_empty_document_is_rest_classic():
    assert classify_api_type({"_id": "x"}) == (ApiType.REST_CLASSIC, False)


@pytest.mark.parametrize("doc", [{"protocol": None}, {"is_oas": []}, {"graphql": 3}, {"oas_doc": "x", "is_oas": True}])
def test_malformed_input_does_not_raise(doc):
    classify_api_type(doc)
