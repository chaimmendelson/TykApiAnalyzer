"""Domain types shared by the classification, snapshot and UI layers."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ApiType(str, Enum):
    REST_CLASSIC = "REST (classic)"
    REST_OAS = "REST (OpenAPI)"
    GRAPHQL = "GraphQL"
    UDG = "Universal Data Graph"
    FEDERATION = "Federation"
    MCP = "MCP"
    TCP = "TCP"
    STREAMING = "Streaming"
    NOT_UNDERSTOOD = "Not understood"


class AuthMethod(str, Enum):
    NONE = "None (keyless)"
    API_KEY = "API key"
    JWT = "JWT"
    BASIC = "Basic"
    OAUTH2 = "OAuth 2.0"
    OPENID = "OpenID Connect"
    MUTUAL_TLS = "Mutual TLS"
    REQUEST_SIGNATURE = "Request signature"
    CUSTOM_PLUGIN = "Custom plugin"
    EXTERNAL_OAUTH = "External OAuth"
    NOT_SET = "Not set"
    NOT_UNDERSTOOD = "Not understood"


class ActiveState(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    UNKNOWN = "Unknown"


class OrgStatus(str, Enum):
    MATCHED = "matched"
    NOT_SET = "not set"
    UNMATCHED = "unmatched"


@dataclass(frozen=True)
class Organization:
    id: str
    name: str


@dataclass(frozen=True)
class ApiRecord:
    id: str
    api_id: str | None
    name: str
    active: ActiveState
    api_type: ApiType
    tls_enabled: bool
    auth_methods: frozenset[AuthMethod]
    org_id: str | None
    org_label: str
    org_status: OrgStatus
    unclassified: tuple[str, ...] = ()
    evidence: dict[str, str] = field(default_factory=dict)
    mw_global: frozenset[str] = frozenset()
    mw_endpoint: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Coverage:
    total: int
    unclassified_count: int
    by_reason: dict[str, int]


@dataclass(frozen=True)
class Snapshot:
    records: list[ApiRecord]
    organizations: dict[str, Organization]
    loaded_at: datetime
    coverage: Coverage
