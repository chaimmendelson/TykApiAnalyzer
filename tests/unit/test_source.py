import inspect

import pytest

from tyk_analyzer import source as source_module
from tyk_analyzer.config import Settings
from tyk_analyzer.source import API_PROJECTION, MongoApiSource, SourceError

URI = "mongodb://reader:hunter2@db.internal:27017/tyk_analytics"
SETTINGS = Settings(mongo_uri=URI)


class FakeCollection:
    def __init__(self, docs=None, error=None, fail_after=None):
        self.docs, self.error, self.fail_after = docs or [], error, fail_after
        self.calls = []

    def find(self, query, projection):
        self.calls.append((query, projection))
        if self.error:
            raise self.error

        def gen():
            for i, d in enumerate(self.docs):
                if self.fail_after is not None and i >= self.fail_after:
                    raise RuntimeError(f"cursor died talking to {URI}")
                yield d

        return gen()


class FakeClient:
    def __init__(self, colls):
        self.colls = colls

    def __getitem__(self, db):
        return {"tyk_apis": self.colls["apis"], "tyk_organisations": self.colls["orgs"]}


def make(apis=None, orgs=None):
    colls = {"apis": apis or FakeCollection(), "orgs": orgs or FakeCollection()}
    return MongoApiSource(SETTINGS, client=FakeClient(colls)), colls


def test_only_two_public_read_methods():
    public = {n for n, _ in inspect.getmembers(MongoApiSource, inspect.isfunction) if not n.startswith("_")}
    assert public == {"fetch_apis", "fetch_organizations"}


def test_module_never_references_write_operations():
    code = inspect.getsource(source_module)
    for word in ("insert", "update", "delete", "replace_one", "drop", "bulk_write", "create_index"):
        assert word not in code.replace("fetch_", "")


def test_projection_excludes_heavy_bodies():
    for path in API_PROJECTION:
        assert not path.startswith("oas_doc.paths")
        assert not path.startswith("graphql.schema")
        assert "certificate" not in path
    assert "oas_doc" not in API_PROJECTION and "graphql" not in API_PROJECTION


def test_reads_use_projection():
    src, colls = make(apis=FakeCollection([{"_id": 1}]))
    assert src.fetch_apis() == [{"_id": 1}]
    assert colls["apis"].calls == [({}, API_PROJECTION)]


def test_driver_error_becomes_source_error_without_secrets():
    src, _ = make(apis=FakeCollection(error=ConnectionError(f"cannot reach {URI} as reader/hunter2")))
    with pytest.raises(SourceError) as exc:
        src.fetch_apis()
    for secret in (URI, "reader", "hunter2"):
        assert secret not in str(exc.value)


def test_cursor_failing_midway_raises_not_partial():
    src, _ = make(apis=FakeCollection([{"_id": 1}, {"_id": 2}, {"_id": 3}], fail_after=2))
    with pytest.raises(SourceError) as exc:
        src.fetch_apis()
    assert "hunter2" not in str(exc.value) and URI not in str(exc.value)
