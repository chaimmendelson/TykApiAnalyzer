import json
from pathlib import Path
from typing import Any

import pytest
from bson import ObjectId

from tyk_analyzer.source import SourceError

FIXTURES = Path(__file__).parent / "fixtures"


def _revive(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$oid"}:
            return ObjectId(value["$oid"])
        return {k: _revive(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_revive(v) for v in value]
    return value


def load_fixture(name: str) -> list[dict[str, Any]]:
    return _revive(json.loads((FIXTURES / name).read_text()))


class InMemorySource:
    """ApiSource backed by lists, optionally failing like a broken database."""

    def __init__(self, apis, orgs, error: str | None = None) -> None:
        self._apis, self._orgs, self._error = apis, orgs, error

    def fetch_apis(self):
        if self._error:
            raise SourceError(self._error)
        return list(self._apis)

    def fetch_organizations(self):
        if self._error:
            raise SourceError(self._error)
        return list(self._orgs)


@pytest.fixture
def api_docs() -> list[dict[str, Any]]:
    return load_fixture("apis.json")


@pytest.fixture
def org_docs() -> list[dict[str, Any]]:
    return load_fixture("organizations.json")


@pytest.fixture
def api_by_name(api_docs):
    return {d.get("name", d["_id"]): d for d in api_docs}


@pytest.fixture
def source(api_docs, org_docs) -> InMemorySource:
    return InMemorySource(api_docs, org_docs)
