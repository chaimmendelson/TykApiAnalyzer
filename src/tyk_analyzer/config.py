"""Runtime configuration from environment variables, and secret redaction."""

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db: str = "tyk_analytics"
    apis_collection: str = "tyk_apis"
    orgs_collection: str = "tyk_organisations"
    timeout_ms: int = 5000

    @property
    def secrets(self) -> tuple[str, ...]:
        return secrets_in_uri(self.mongo_uri)


def load_dotenv(path: str | Path = ".env", env: dict[str, str] | None = None) -> None:
    """Load KEY=VALUE lines from a .env file into the environment without overriding it.

    Real environment variables win, so containers and CI keep control. A missing file is fine.
    """
    target = os.environ if env is None else env
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip().removeprefix("export ").strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        target.setdefault(key, value)


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    uri = env.get("MONGO_URI", "").strip()
    if not uri:
        raise ConfigError("MONGO_URI is not set. Provide the MongoDB connection string.")
    try:
        timeout = int(env.get("MONGO_TIMEOUT_MS", "5000"))
    except ValueError:
        raise ConfigError("MONGO_TIMEOUT_MS must be an integer number of milliseconds.") from None
    return Settings(
        mongo_uri=uri,
        mongo_db=env.get("MONGO_DB", "tyk_analytics"),
        apis_collection=env.get("TYK_APIS_COLLECTION", "tyk_apis"),
        orgs_collection=env.get("TYK_ORGS_COLLECTION", "tyk_organisations"),
        timeout_ms=timeout,
    )


def secrets_in_uri(uri: str) -> tuple[str, ...]:
    """Return the strings that must never be shown: the URI, its user and its password."""
    found = [uri]
    try:
        parts = urlsplit(uri)
        for value in (parts.username, parts.password):
            if value:
                found.extend([value, unquote(value)])
    except ValueError:
        pass
    return tuple(dict.fromkeys(s for s in found if s))


def redact(text: str, secrets: Iterable[str]) -> str:
    """Replace every secret in text, longest first so a URI goes before its parts."""
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret:
            text = text.replace(secret, "***")
    return text
