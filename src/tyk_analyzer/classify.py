"""Pure classification of one Tyk API definition. Rules: contracts/classification-rules.md.

Nothing here raises on malformed input: unexpected shapes become "not understood" so the API
is still counted (spec edge case) and shows up in the coverage indicator.
"""

from collections.abc import Mapping
from typing import Any

from tyk_analyzer.model import (
    ApiRecord,
    ApiType,
    AuthMethod,
    Organization,
    OrgStatus,
)

_MCP_KEYS = ("mcpTools", "mcpPrompts", "mcpResources")
_GATEWAY = "x-tyk-api-gateway"

# (document flag, method). Several flags can map to one method.
_AUTH_FLAGS: tuple[tuple[str, AuthMethod], ...] = (
    ("use_keyless", AuthMethod.NONE),
    ("use_standard_auth", AuthMethod.API_KEY),
    ("enable_jwt", AuthMethod.JWT),
    ("use_basic_auth", AuthMethod.BASIC),
    ("use_oauth2", AuthMethod.OAUTH2),
    ("use_openid", AuthMethod.OPENID),
    ("use_mutual_tls_auth", AuthMethod.MUTUAL_TLS),
    ("enable_signature_checking", AuthMethod.REQUEST_SIGNATURE),
    ("use_go_plugin_auth", AuthMethod.CUSTOM_PLUGIN),
    ("enable_coprocess_auth", AuthMethod.CUSTOM_PLUGIN),
    ("custom_plugin_auth_enabled", AuthMethod.CUSTOM_PLUGIN),
)

_ABSENT = object()


def _path(doc: Any, *keys: str) -> Any:
    """Walk nested mappings; return _ABSENT if any step is missing or not a mapping."""
    cur = doc
    for key in keys:
        if not isinstance(cur, Mapping) or key not in cur:
            return _ABSENT
        cur = cur[key]
    return cur


def _is_empty(value: Any) -> bool:
    return value is _ABSENT or value is None or value == "" or value == [] or value == {}


# Optional middleware (contracts/classification-rules.md). Names are shared by both styles.
_EXTENDED_PATHS: dict[str, str] = {
    "white_list": "Allow list",
    "black_list": "Block list",
    "ignored": "Ignore authentication",
    "cache": "Cache",
    "advance_cache_config": "Cache",
    "circuit_breakers": "Circuit breaker",
    "hard_timeouts": "Enforce timeout",
    "rate_limit": "Rate limit",
    "size_limits": "Request size limit",
    "url_rewrites": "URL rewrite",
    "validate_json": "Validate request",
    "virtual": "Virtual endpoint",
    "method_transforms": "Method transform",
    "transform": "Body transform",
    "transform_response": "Body transform",
    "transform_headers": "Request header transform",
    "transform_response_headers": "Response header transform",
    "track_endpoints": "Track endpoint",
    "do_not_track_endpoints": "Do not track endpoint",
    "internal": "Internal endpoint",
}

_OAS_OPERATIONS: dict[str, str] = {
    "allow": "Allow list",
    "block": "Block list",
    "ignoreAuthentication": "Ignore authentication",
    "cache": "Cache",
    "circuitBreaker": "Circuit breaker",
    "enforceTimeout": "Enforce timeout",
    "rateLimit": "Rate limit",
    "requestSizeLimit": "Request size limit",
    "urlRewrite": "URL rewrite",
    "validateRequest": "Validate request",
    "mockResponse": "Mock response",
    "virtualEndpoint": "Virtual endpoint",
    "transformRequestBody": "Body transform",
    "transformResponseBody": "Body transform",
    "transformRequestHeaders": "Request header transform",
    "transformResponseHeaders": "Response header transform",
    "trackEndpoint": "Track endpoint",
    "doNotTrackEndpoint": "Do not track endpoint",
    "internal": "Internal endpoint",
}

_OAS_GLOBAL: dict[str, str] = {
    "cache": "Cache",
    "cors": "CORS",
    "contextVariables": "Context variables",
    "trafficLogs": "Traffic logs",
    "transformRequestHeaders": "Request header transform",
    "transformResponseHeaders": "Response header transform",
}

# (top-level flag, name): enabled when the value is exactly True.
_CLASSIC_GLOBAL_FLAGS: tuple[tuple[str, str], ...] = (
    ("enable_context_vars", "Context variables"),
    ("enable_ip_whitelisting", "IP allow list"),
    ("enable_ip_blacklisting", "IP block list"),
    ("enable_batch_request_support", "Batch requests"),
    ("enable_detailed_recording", "Traffic logs"),
    ("do_not_track", "Do not track"),
)

_NO_MIDDLEWARE: tuple[frozenset[str], frozenset[str]] = (frozenset(), frozenset())


def _is_true(value: Any) -> bool:
    return value is True


def _non_empty(value: Any) -> bool:
    return isinstance(value, (list, dict, str)) and len(value) > 0


def _entries_enabled(value: Any) -> bool:
    """A classic endpoint list counts when it has an entry that is not switched off."""
    if not isinstance(value, list):
        return False
    return any(not (isinstance(e, Mapping) and e.get("disabled") is True) for e in value)


def _classic_middleware(doc: Mapping[str, Any], glob: set[str], endpoint: set[str]) -> None:
    if _path(doc, "cache_options", "enable_cache") is True:
        glob.add("Cache")
    if _path(doc, "CORS", "enable") is True:
        glob.add("CORS")
    rate = _path(doc, "global_rate_limit", "rate")
    if isinstance(rate, (int, float)) and not isinstance(rate, bool) and rate > 0:
        glob.add("Rate limit (API)")
    glob.update(name for flag, name in _CLASSIC_GLOBAL_FLAGS if _is_true(doc.get(flag)))
    if _non_empty(_path(doc, "event_handlers", "events")):
        glob.add("Event handlers")
    if _non_empty(_path(doc, "uptime_tests", "check_list")):
        glob.add("Uptime tests")
    if _path(doc, "proxy", "strip_listen_path") is True:
        glob.add("Strip listen path")
    if _non_empty(doc.get("domain")):
        glob.add("Custom domain")
    versions = _path(doc, "version_data", "versions")
    if not isinstance(versions, Mapping):
        return
    for version in versions.values():
        if not isinstance(version, Mapping):
            continue
        if isinstance(version.get("global_headers"), Mapping) and version["global_headers"]:
            glob.add("Request header transform")
        if isinstance(version.get("global_response_headers"), Mapping) and version["global_response_headers"]:
            glob.add("Response header transform")
        if isinstance(version.get("override_target"), str) and version["override_target"]:
            glob.add("Override target")
        paths = version.get("extended_paths")
        if isinstance(paths, Mapping):
            endpoint.update(
                name for key, name in _EXTENDED_PATHS.items() if _entries_enabled(paths.get(key))
            )


def _oas_middleware(doc: Mapping[str, Any], glob: set[str], endpoint: set[str]) -> None:
    gateway = _path(doc, "oas_doc", _GATEWAY)
    if not isinstance(gateway, Mapping):
        return
    middleware = gateway.get("middleware")
    if isinstance(middleware, Mapping):
        section = middleware.get("global")
        if isinstance(section, Mapping):
            for key, name in _OAS_GLOBAL.items():
                if _path(section, key, "enabled") is True:
                    glob.add(name)
        operations = middleware.get("operations")
        if isinstance(operations, Mapping):
            for operation in operations.values():
                if not isinstance(operation, Mapping):
                    continue
                for key, name in _OAS_OPERATIONS.items():
                    entry = operation.get(key)
                    if isinstance(entry, Mapping) and entry.get("enabled") is not False:
                        endpoint.add(name)
    if _path(gateway, "upstream", "rateLimit", "enabled") is True:
        glob.add("Rate limit (API)")
    if _path(gateway, "server", "customDomain", "enabled") is True:
        glob.add("Custom domain")
    if _non_empty(_path(gateway, "server", "eventHandlers")):
        glob.add("Event handlers")
    if _path(gateway, "server", "detailedActivityLogs", "enabled") is True:
        glob.add("Traffic logs")
    if _path(gateway, "server", "listenPath", "strip") is True:
        glob.add("Strip listen path")


def classify_middleware(doc: Mapping[str, Any]) -> tuple[frozenset[str], frozenset[str]]:
    """Return (global middleware names, per-endpoint middleware names) explicitly enabled."""
    if not isinstance(doc, Mapping):
        return _NO_MIDDLEWARE
    glob: set[str] = set()
    endpoint: set[str] = set()
    _classic_middleware(doc, glob, endpoint)
    _oas_middleware(doc, glob, endpoint)
    return frozenset(glob), frozenset(endpoint)


def classify_api_type(doc: Mapping[str, Any]) -> tuple[ApiType, bool]:
    """Return (api type, tls_enabled). First matching rule wins."""
    is_oas = doc.get("is_oas")
    protocol = doc.get("protocol")
    gql = doc.get("graphql")
    gql_enabled = gql.get("enabled") if isinstance(gql, Mapping) else None

    malformed = (
        (is_oas is not None and not isinstance(is_oas, bool))
        or (protocol is not None and not isinstance(protocol, str))
        or (gql is not None and not isinstance(gql, Mapping))
        or (gql_enabled is not None and not isinstance(gql_enabled, bool))
    )
    if malformed:
        return ApiType.NOT_UNDERSTOOD, False

    oas = is_oas is True
    if oas:
        middleware = _path(doc, "oas_doc", _GATEWAY, "middleware")
        if isinstance(middleware, Mapping) and any(k in middleware for k in _MCP_KEYS):
            return ApiType.MCP, False
        if _path(doc, "oas_doc", "x-tyk-streaming") is not _ABSENT:
            return ApiType.STREAMING, False

    if gql_enabled is True:
        mode = gql.get("execution_mode")
        subgraphs = _path(gql, "supergraph", "subgraphs")
        if not _is_empty(subgraphs) or mode in ("supergraph", "subgraph"):
            return ApiType.FEDERATION, False
        if mode == "executionEngine":
            return ApiType.UDG, False
        return ApiType.GRAPHQL, False

    if protocol in ("tcp", "tls"):
        return ApiType.TCP, protocol == "tls"
    if oas:
        return ApiType.REST_OAS, False
    if _is_empty(protocol):
        return ApiType.REST_CLASSIC, False
    return ApiType.NOT_UNDERSTOOD, False


def _flag(value: Any) -> bool | None:
    """True/False for booleans, None for absent, raises ValueError for anything else."""
    if value is None or value is _ABSENT:
        return None
    if isinstance(value, bool):
        return value
    raise ValueError(value)


def classify_auth(doc: Mapping[str, Any]) -> tuple[frozenset[AuthMethod], list[str]]:
    """Return (authentication methods, unclassified reasons)."""
    methods: set[AuthMethod] = set()
    reasons: list[str] = []

    def apply(raw: Any, method: AuthMethod) -> None:
        try:
            if _flag(raw):
                methods.add(method)
        except ValueError:
            methods.add(AuthMethod.NOT_UNDERSTOOD)
            if "auth" not in reasons:
                reasons.append("auth")

    for flag, method in _AUTH_FLAGS:
        apply(doc.get(flag), method)
    external = doc.get("external_oauth")
    if external is not None and not isinstance(external, Mapping):
        apply(external, AuthMethod.EXTERNAL_OAUTH)
    else:
        apply(_path(external, "enabled"), AuthMethod.EXTERNAL_OAUTH)

    if doc.get("is_oas") is True:
        oas_auth = _path(doc, "oas_doc", _GATEWAY, "server", "authentication", "enabled")
        if oas_auth is True:
            real = methods - {AuthMethod.NONE, AuthMethod.NOT_UNDERSTOOD}
            if AuthMethod.NONE in methods or not real:
                methods.add(AuthMethod.NOT_UNDERSTOOD)
                reasons.append("auth_oas_mismatch")

    if not methods:
        methods.add(AuthMethod.NOT_SET)
    return frozenset(methods), reasons


def classify_org(
    doc: Mapping[str, Any], organizations: Mapping[str, Organization]
) -> tuple[str, OrgStatus, list[str]]:
    """Return (label, status, unclassified reasons)."""
    raw = doc.get("org_id")
    if raw is None or raw == "":
        return "Not set", OrgStatus.NOT_SET, []
    org_id = str(raw)
    org = organizations.get(org_id)
    if org is not None:
        return org.name, OrgStatus.MATCHED, []
    return f"{org_id} (unmatched)", OrgStatus.UNMATCHED, ["org_unmatched"]


def _clip(value: Any, limit: int = 120) -> str:
    text = "(absent)" if value is _ABSENT else str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _evidence(doc: Mapping[str, Any]) -> dict[str, str]:
    """The raw values behind the classifications. Never the whole document (FR-008)."""
    ev: dict[str, str] = {
        "is_oas": _clip(doc.get("is_oas", _ABSENT)),
        "protocol": _clip(doc.get("protocol", _ABSENT)),
        "org_id": _clip(doc.get("org_id", _ABSENT)),
    }
    gql = doc.get("graphql")
    if isinstance(gql, Mapping):
        ev["graphql.enabled"] = _clip(gql.get("enabled", _ABSENT))
        ev["graphql.execution_mode"] = _clip(gql.get("execution_mode", _ABSENT))
        subgraphs = _path(gql, "supergraph", "subgraphs")
        if not _is_empty(subgraphs):
            ev["graphql.supergraph.subgraphs"] = f"{len(subgraphs)} configured"
        sources = _path(gql, "engine", "data_sources")
        if not _is_empty(sources):
            ev["graphql.engine.data_sources"] = f"{len(sources)} configured"
    middleware = _path(doc, "oas_doc", _GATEWAY, "middleware")
    if isinstance(middleware, Mapping):
        present = [k for k in _MCP_KEYS if k in middleware]
        if present:
            ev["mcp markers"] = ", ".join(present)
    if _path(doc, "oas_doc", "x-tyk-streaming") is not _ABSENT:
        ev["x-tyk-streaming"] = "present"
    ev["auth flags set"] = ", ".join(f for f, _ in _AUTH_FLAGS if doc.get(f) is True) or "(none)"
    if _path(doc, "external_oauth", "enabled") is True:
        ev["auth flags set"] += ", external_oauth.enabled"
    oas_auth = _path(doc, "oas_doc", _GATEWAY, "server", "authentication", "enabled")
    if oas_auth is not _ABSENT:
        ev["oas server.authentication.enabled"] = _clip(oas_auth)
    return ev


def classify_api(doc: Mapping[str, Any], organizations: Mapping[str, Organization]) -> ApiRecord:
    api_type, tls = classify_api_type(doc)
    methods, auth_reasons = classify_auth(doc)
    org_label, org_status, org_reasons = classify_org(doc, organizations)
    mw_global, mw_endpoint = classify_middleware(doc)

    reasons: list[str] = []
    if api_type is ApiType.NOT_UNDERSTOOD:
        reasons.append("api_type")
    reasons += auth_reasons + org_reasons

    name = doc.get("name")
    api_id = doc.get("api_id")
    org_id = doc.get("org_id")
    return ApiRecord(
        id=str(doc.get("_id", "")),
        api_id=None if api_id is None else str(api_id),
        name="" if name is None else str(name),
        api_type=api_type,
        tls_enabled=tls,
        auth_methods=methods,
        mw_global=mw_global,
        mw_endpoint=mw_endpoint,
        org_id=None if org_id in (None, "") else str(org_id),
        org_label=org_label,
        org_status=org_status,
        unclassified=tuple(reasons),
        evidence={
            **_evidence(doc),
            "global middleware": ", ".join(sorted(mw_global)) or "(none)",
            "per-endpoint middleware": ", ".join(sorted(mw_endpoint)) or "(none)",
        },
    )
