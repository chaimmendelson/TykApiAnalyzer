import pytest

from tyk_analyzer.config import ConfigError, load_dotenv, load_settings, redact, secrets_in_uri

URI = "mongodb://reader:s3cr%40t@db.internal:27017/tyk_analytics"


def test_defaults_applied():
    s = load_settings({"MONGO_URI": "mongodb://h:27017"})
    assert (s.mongo_db, s.apis_collection, s.orgs_collection, s.timeout_ms) == (
        "tyk_analytics",
        "tyk_apis",
        "tyk_organisations",
        5000,
    )


def test_overrides_applied():
    s = load_settings(
        {"MONGO_URI": "mongodb://h", "MONGO_DB": "d", "TYK_APIS_COLLECTION": "a",
         "TYK_ORGS_COLLECTION": "o", "MONGO_TIMEOUT_MS": "100"}
    )
    assert (s.mongo_db, s.apis_collection, s.orgs_collection, s.timeout_ms) == ("d", "a", "o", 100)


def test_missing_uri_raises_without_echoing_values():
    with pytest.raises(ConfigError) as exc:
        load_settings({"MONGO_DB": "x"})
    assert "MONGO_URI" in str(exc.value)


def test_bad_timeout_raises():
    with pytest.raises(ConfigError):
        load_settings({"MONGO_URI": "mongodb://h", "MONGO_TIMEOUT_MS": "soon"})


def test_redact_removes_uri_user_and_password():
    text = f"failed connecting to {URI}: auth failed for reader with s3cr%40t / s3cr@t"
    cleaned = redact(text, secrets_in_uri(URI))
    for secret in (URI, "reader", "s3cr%40t", "s3cr@t"):
        assert secret not in cleaned


def test_redact_without_credentials_is_safe():
    assert redact("plain message", secrets_in_uri("mongodb://h:27017")) == "plain message"


def test_dotenv_loads_without_overriding_real_environment(tmp_path):
    f = tmp_path / ".env"
    f.write_text('# comment\n\nMONGO_URI="mongodb://from-file"\nexport MONGO_DB=filedb\nTYK_APIS_COLLECTION=x\n')
    env = {"MONGO_DB": "realdb"}
    load_dotenv(f, env)
    assert env == {"MONGO_URI": "mongodb://from-file", "MONGO_DB": "realdb", "TYK_APIS_COLLECTION": "x"}


def test_dotenv_missing_file_is_fine(tmp_path):
    env = {}
    load_dotenv(tmp_path / "nope.env", env)
    assert env == {}
