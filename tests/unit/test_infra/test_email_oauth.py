"""Tests for the OAuth layer - every Google call replaced by a double.

The guideline is absolute: no test touches an external service. The Google
modules are swapped in ``sys.modules`` before the lazy imports run, so no
browser opens and no network packet leaves the machine.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from police_thief.infra.email.oauth import (
    GMAIL_SEND_SCOPE,
    CredentialsMissingError,
    build_gmail_service,
    load_credentials,
)


class FakeCredentials:
    """A stand-in for google.oauth2 Credentials with scriptable state."""

    loaded_from: tuple[str, list[str]] | None = None

    def __init__(self, valid: bool = True, expired: bool = False, refresh_token: str = "") -> None:
        """Record the validity the test wants this credential to report."""
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refreshed = False

    @classmethod
    def from_authorized_user_file(cls, path: str, scopes: list[str]) -> FakeCredentials:
        """Remember the load arguments so the test can assert the scope requested."""
        cls.loaded_from = (path, scopes)
        return cls._next

    #: Set by a test to make :meth:`refresh` fail the way a revoked token does.
    refresh_raises: bool = False

    def refresh(self, request: object) -> None:
        """Mark the credential refreshed and valid, or fail like a revoked token.

        Raises:
            RefreshError: when ``refresh_raises`` is set, mirroring Google's
                ``invalid_grant`` for an expired or revoked refresh token.
        """
        if self.refresh_raises:
            from google.auth.exceptions import RefreshError

            raise RefreshError("invalid_grant: Token has been expired or revoked.")
        self.refreshed = True
        self.valid = True

    def to_json(self) -> str:
        """Serialize to a placeholder token document."""
        return '{"token": "fake"}'


@pytest.fixture
def google_doubles(monkeypatch: pytest.MonkeyPatch) -> type[FakeCredentials]:
    """Install fake google modules for the duration of one test."""
    creds_mod = types.ModuleType("google.oauth2.credentials")
    creds_mod.Credentials = FakeCredentials
    request_mod = types.ModuleType("google.auth.transport.requests")
    request_mod.Request = object
    errors_mod = types.ModuleType("google.auth.exceptions")

    class RefreshError(Exception):
        """Stand-in for Google's refresh failure."""

    errors_mod.RefreshError = RefreshError
    flow_mod = types.ModuleType("google_auth_oauthlib.flow")

    class FakeFlow:
        """Stand-in for Google's installed-app OAuth flow, asserting the send-only scope."""
        @classmethod
        def from_client_secrets_file(cls, path: str, scopes: list[str]) -> FakeFlow:
            """Assert the send-only scope was requested, then hand back the flow."""
            assert scopes == [GMAIL_SEND_SCOPE]
            return cls()

        def run_local_server(self, port: int = 0) -> FakeCredentials:
            """Return a valid credential without opening a browser."""
            return FakeCredentials(valid=True)

    flow_mod.InstalledAppFlow = FakeFlow
    monkeypatch.setitem(sys.modules, "google.auth.exceptions", errors_mod)
    monkeypatch.setitem(sys.modules, "google.oauth2.credentials", creds_mod)
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", request_mod)
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib.flow", flow_mod)
    return FakeCredentials


def test_a_valid_token_is_reused_without_any_flow(
    google_doubles: type[FakeCredentials], tmp_path: Path
) -> None:
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")
    google_doubles._next = FakeCredentials(valid=True)
    creds = load_credentials(tmp_path / "credentials.json", token)
    assert creds is google_doubles._next
    assert google_doubles.loaded_from == (str(token), [GMAIL_SEND_SCOPE])


def test_an_expired_token_is_refreshed_and_rewritten(
    google_doubles: type[FakeCredentials], tmp_path: Path
) -> None:
    token = tmp_path / "token.json"
    token.write_text("stale", encoding="utf-8")
    google_doubles._next = FakeCredentials(valid=False, expired=True, refresh_token="r")
    creds = load_credentials(tmp_path / "credentials.json", token)
    assert creds.refreshed
    assert token.read_text(encoding="utf-8") == '{"token": "fake"}'


def test_a_revoked_refresh_token_re_authorizes_instead_of_aborting(
    google_doubles: type[FakeCredentials], tmp_path: Path
) -> None:
    """The failure that killed a report on 2026-08-17, held as a test.

    Google expires an unused refresh token, and revokes it after seven days
    while the Cloud project is in testing mode. The raw ``RefreshError:
    invalid_grant`` propagated out of three libraries and aborted the send.
    A revoked token is not an error condition - it is a token to mint again -
    and rule #35 punishes a missing report as heavily as a false one.
    """
    secrets_file = tmp_path / "credentials.json"
    secrets_file.write_text("{}", encoding="utf-8")
    token = tmp_path / "token.json"
    token.write_text("revoked", encoding="utf-8")
    stale = FakeCredentials(valid=False, expired=True, refresh_token="r")
    stale.refresh_raises = True
    google_doubles._next = stale

    creds = load_credentials(secrets_file, token)

    assert creds is not stale and creds.valid, "a revoked token must be re-minted"
    assert token.read_text(encoding="utf-8") == '{"token": "fake"}'


def test_a_revoked_token_with_no_secret_file_still_says_what_to_do(
    google_doubles: type[FakeCredentials], tmp_path: Path
) -> None:
    """Re-authorizing needs the Cloud Console file; say so instead of RefreshError."""
    token = tmp_path / "token.json"
    token.write_text("revoked", encoding="utf-8")
    stale = FakeCredentials(valid=False, expired=True, refresh_token="r")
    stale.refresh_raises = True
    google_doubles._next = stale
    with pytest.raises(CredentialsMissingError, match="Cloud Console"):
        load_credentials(tmp_path / "nope.json", token)


def test_first_run_mints_the_token_via_the_consent_flow(
    google_doubles: type[FakeCredentials], tmp_path: Path
) -> None:
    secrets_file = tmp_path / "credentials.json"
    secrets_file.write_text("{}", encoding="utf-8")
    token = tmp_path / "token.json"
    creds = load_credentials(secrets_file, token)
    assert creds.valid
    assert token.exists()  # Appendix A step 5: token.json created automatically


def test_missing_credentials_fail_loudly_with_guidance(
    google_doubles: type[FakeCredentials], tmp_path: Path
) -> None:
    with pytest.raises(CredentialsMissingError, match="Cloud Console"):
        load_credentials(tmp_path / "nope.json", tmp_path / "token.json")


def test_the_service_is_built_for_gmail_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple] = []
    discovery = types.ModuleType("googleapiclient.discovery")
    discovery.build = lambda api, ver, credentials: calls.append((api, ver, credentials)) or "svc"
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", discovery)
    assert build_gmail_service("creds") == "svc"
    assert calls == [("gmail", "v1", "creds")]
