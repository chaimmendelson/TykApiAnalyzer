import pytest

from tyk_analyzer.classify import classify_auth
from tyk_analyzer.model import AuthMethod as A


@pytest.mark.parametrize(
    ("flag", "method"),
    [
        ("use_keyless", A.NONE),
        ("use_standard_auth", A.API_KEY),
        ("enable_jwt", A.JWT),
        ("use_basic_auth", A.BASIC),
        ("use_oauth2", A.OAUTH2),
        ("use_openid", A.OPENID),
        ("use_mutual_tls_auth", A.MUTUAL_TLS),
        ("enable_signature_checking", A.REQUEST_SIGNATURE),
        ("use_go_plugin_auth", A.CUSTOM_PLUGIN),
        ("enable_coprocess_auth", A.CUSTOM_PLUGIN),
        ("custom_plugin_auth_enabled", A.CUSTOM_PLUGIN),
    ],
)
def test_each_flag_maps_to_its_method(flag, method):
    assert classify_auth({flag: True}) == (frozenset({method}), [])


def test_external_oauth():
    assert classify_auth({"external_oauth": {"enabled": True}})[0] == {A.EXTERNAL_OAUTH}


def test_several_flags_give_several_methods(api_by_name):
    assert classify_auth(api_by_name["multi-auth"])[0] == {A.API_KEY, A.JWT, A.OAUTH2}


def test_all_remaining_methods(api_by_name):
    methods, reasons = classify_auth(api_by_name["all-methods"])
    assert methods == {A.OPENID, A.REQUEST_SIGNATURE, A.CUSTOM_PLUGIN, A.EXTERNAL_OAUTH}
    assert reasons == []


def test_no_flag_is_not_set(api_by_name):
    assert classify_auth(api_by_name["no-auth-flags"]) == (frozenset({A.NOT_SET}), [])
    assert classify_auth({"_id": "x"}) == (frozenset({A.NOT_SET}), [])


def test_false_flag_is_not_a_method():
    assert classify_auth({"use_keyless": False, "enable_jwt": True})[0] == {A.JWT}


def test_non_boolean_flag_is_not_understood(api_by_name):
    methods, reasons = classify_auth(api_by_name["bad-flags"])
    assert methods == {A.NOT_UNDERSTOOD}
    assert reasons == ["auth"]


def test_oas_and_classic_with_same_flag_classify_the_same(api_by_name):
    oas = classify_auth(api_by_name["rest-oas"])
    classic = classify_auth({"use_standard_auth": True})
    assert oas == classic == (frozenset({A.API_KEY}), [])


def test_consistent_oas_definitions_have_no_mismatch(api_by_name):
    for name in ("mcp", "streaming", "rest-oas-keyless"):
        assert classify_auth(api_by_name[name])[1] == []


def test_oas_schemes_contradicting_flags_are_flagged(api_by_name):
    methods, reasons = classify_auth(api_by_name["oas-auth-mismatch"])
    assert methods == {A.NONE, A.NOT_UNDERSTOOD}
    assert reasons == ["auth_oas_mismatch"]


def test_oas_auth_enabled_with_no_flags_is_flagged():
    doc = {"is_oas": True, "oas_doc": {"x-tyk-api-gateway": {"server": {"authentication": {"enabled": True}}}}}
    methods, reasons = classify_auth(doc)
    assert A.NOT_UNDERSTOOD in methods and reasons == ["auth_oas_mismatch"]


def test_malformed_oas_doc_does_not_raise():
    classify_auth({"is_oas": True, "oas_doc": "x", "use_keyless": True})
