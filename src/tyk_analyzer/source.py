"""Read-only access to the Tyk Dashboard's MongoDB collections."""

import logging
import time
from typing import Any, Protocol

from pymongo import MongoClient

from tyk_analyzer.config import Settings, redact

log = logging.getLogger(__name__)

_GW = "oas_doc.x-tyk-api-gateway"

# Only the fields needed for classification. Heavy bodies (paths, schemas, certificates,
# secrets) are deliberately absent.
API_PROJECTION: dict[str, int] = {
    f: 1
    for f in (
        "name",
        "api_id",
        "org_id",
        "protocol",
        "is_oas",
        "listen_port",
        "use_keyless",
        "use_standard_auth",
        "enable_jwt",
        "use_basic_auth",
        "use_oauth2",
        "use_openid",
        "use_mutual_tls_auth",
        "enable_signature_checking",
        "use_go_plugin_auth",
        "enable_coprocess_auth",
        "custom_plugin_auth_enabled",
        "external_oauth.enabled",
        "graphql.enabled",
        "graphql.execution_mode",
        "graphql.supergraph.subgraphs",
        "graphql.engine.data_sources",
        "oas_doc.x-tyk-streaming",
        "cache_options",
        "CORS",
        "global_rate_limit",
        "enable_context_vars",
        "enable_ip_whitelisting",
        "enable_ip_blacklisting",
        "enable_batch_request_support",
        "enable_detailed_recording",
        "do_not_track",
        "event_handlers.events",
        "uptime_tests.check_list",
        "proxy.strip_listen_path",
        "domain",
        "version_data.versions",
        f"{_GW}.middleware",
        f"{_GW}.server",
        f"{_GW}.upstream.rateLimit",
    )
}

ORG_PROJECTION: dict[str, int] = {"owner_name": 1, "owner_slug": 1}


class SourceError(Exception):
    """A read from the data source failed or was incomplete. Messages never hold secrets."""


class ApiSource(Protocol):
    def fetch_apis(self) -> list[dict[str, Any]]: ...

    def fetch_organizations(self) -> list[dict[str, Any]]: ...


class MongoApiSource:
    """Reads API definitions and organizations. Exposes reads only."""

    def __init__(self, settings: Settings, client: Any = None) -> None:
        self._settings = settings
        self._client = client

    def fetch_apis(self) -> list[dict[str, Any]]:
        return self._read(self._settings.apis_collection, API_PROJECTION)

    def fetch_organizations(self) -> list[dict[str, Any]]:
        return self._read(self._settings.orgs_collection, ORG_PROJECTION)

    def _db(self) -> Any:
        if self._client is None:
            self._client = MongoClient(
                self._settings.mongo_uri,
                serverSelectionTimeoutMS=self._settings.timeout_ms,
                socketTimeoutMS=max(self._settings.timeout_ms * 6, 30000),
            )
        return self._client[self._settings.mongo_db]

    def _read(self, collection: str, projection: dict[str, int]) -> list[dict[str, Any]]:
        started = time.monotonic()
        try:
            docs = list(self._db()[collection].find({}, projection))
        except Exception as exc:  # any failure, including a cursor dying midway, is a SourceError
            raise SourceError(self._safe(f"Could not read '{collection}': {exc}")) from None
        log.info("read %d documents from %s in %.2fs", len(docs), collection, time.monotonic() - started)
        return docs

    def _safe(self, message: str) -> str:
        return redact(message, self._settings.secrets)[:300]
