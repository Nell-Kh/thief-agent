"""Tests for the sender - MIME anatomy, both modes, 429 back-off, the gates."""

from __future__ import annotations

import base64
import email
import json
from types import SimpleNamespace

import pytest

from police_thief.infra.email.sender import (
    MODE_SEND,
    GmailSender,
    RateLimitedError,
    build_report_email,
)
from police_thief.shared.gatekeeper import Gatekeeper


class FakeGmail:
    """A Gmail service double recording drafts and sends."""

    def __init__(self, error: Exception | None = None) -> None:
        """Start with empty draft and sent logs, and no pending error."""
        self.drafts_created: list[dict] = []
        self.messages_sent: list[dict] = []
        self._error = error

    def users(self) -> FakeGmail:
        """Mimic the Gmail API's fluent ``users()`` step."""
        return self

    def drafts(self) -> SimpleNamespace:
        # ``userId`` mirrors the real Gmail API keyword, hence the noqa.
        """Mimic the Gmail API's ``drafts()`` resource."""
        create = lambda userId, body: self._request(self.drafts_created, body)  # noqa: N803, E731
        return SimpleNamespace(create=create)

    def messages(self) -> SimpleNamespace:
        """Mimic the Gmail API's ``messages()`` resource."""
        send = lambda userId, body: self._request(self.messages_sent, body)  # noqa: N803, E731
        return SimpleNamespace(send=send)

    def _request(self, bucket: list[dict], body: dict) -> SimpleNamespace:
        """Record the request and return an object with the API's ``execute`` step."""
        def execute() -> dict:
            """Raise the configured error, or record the call and return a stub id."""
            if self._error is not None:
                raise self._error
            bucket.append(body)
            return {"id": "msg-1"}

        return SimpleNamespace(execute=execute)


def test_the_report_is_a_machine_readable_json_attachment() -> None:
    payload = {"game_id": "G1", "totals": {"police": 20, "thief": 5}}
    message = build_report_email("prof@example.com", "Result", "result_G1.json", payload)
    parsed = email.message_from_bytes(base64.urlsafe_b64decode(message["raw"]))
    assert parsed["to"] == "prof@example.com"
    parts = list(parsed.walk())
    attachment = next(p for p in parts if p.get_filename() == "result_G1.json")
    body = json.loads(attachment.get_payload(decode=True))
    assert body == payload  # not plaintext - ch. 9.3.3 iron rule


def test_the_email_body_carries_the_same_canonical_bytes_as_the_attachment() -> None:
    """Kit SPEC section 2: the body is the compact canonical report, not a note."""
    from police_thief.shared.config_io import canonical_json

    payload = {"b": 2, "a": 1}
    message = build_report_email("prof@example.com", "Result", "r.json", payload)
    parsed = email.message_from_bytes(base64.urlsafe_b64decode(message["raw"]))
    text_part = next(p for p in parsed.walk() if p.get_content_type() == "text/plain")
    assert text_part.get_payload(decode=True).decode("utf-8") == canonical_json(payload)


def test_draft_mode_parks_the_message_in_drafts() -> None:
    service = FakeGmail()
    sender = GmailSender(service, "prof@example.com", mode="draft")
    assert sender.send_report("s", "r.json", {"x": 1}) == "sent"
    assert len(service.drafts_created) == 1
    assert service.messages_sent == []


def test_send_mode_really_sends() -> None:
    service = FakeGmail()
    sender = GmailSender(service, "prof@example.com", mode=MODE_SEND)
    sender.send_report("s", "r.json", {"x": 1})
    assert len(service.messages_sent) == 1
    assert service.drafts_created == []


def test_an_unknown_mode_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="unknown email mode"):
        GmailSender(FakeGmail(), "prof@example.com", mode="broadcast")


def test_google_429_becomes_a_back_off_never_a_blind_retry() -> None:
    quota_error = Exception("quota")
    quota_error.resp = SimpleNamespace(status=429)
    sender = GmailSender(FakeGmail(error=quota_error), "prof@example.com", mode=MODE_SEND)
    with pytest.raises(RateLimitedError, match="429"):
        sender.send_report("s", "r.json", {})


def test_other_api_errors_pass_through_unmasked() -> None:
    boom = Exception("boom")
    boom.resp = SimpleNamespace(status=500)
    sender = GmailSender(FakeGmail(error=boom), "prof@example.com", mode=MODE_SEND)
    with pytest.raises(Exception, match="boom"):
        sender.send_report("s", "r.json", {})


def test_configured_sender_reads_everything_from_config(tmp_path) -> None:
    from police_thief.infra.email.sender import configured_sender

    limits = tmp_path / "rate_limits.json"
    limits.write_text(
        json.dumps({"rate_limits": {"services": {"gmail": {
            "requests_per_minute": 30, "daily_quota": 100, "queue_depth": 10,
            "dos_max_per_window": 2, "dos_window_sec": 5.0}}}}),
        encoding="utf-8",
    )
    manager = SimpleNamespace(
        private=lambda section: {"recipient": "prof@example.com", "mode": "draft"}
    )
    sender = configured_sender(manager, FakeGmail(), rate_limits_path=str(limits))
    assert sender.recipient == "prof@example.com"
    assert sender.mode == "draft"
    assert sender.send_report("s", "r.json", {}) == "sent"  # gates wired in
    # The DOS window is the file's 2, not the class's old hardcoded default of
    # 12 - a third send within the window must trip the lock, not sail through.
    sender.send_report("s", "r.json", {})
    assert sender.send_report("s", "r.json", {}) == "locked"


def test_every_send_passes_the_gatekeeper() -> None:
    clock = lambda: 0.0  # noqa: E731 - a frozen clock is clearest inline
    keeper = Gatekeeper(
        requests_per_minute=60, daily_quota=1, queue_depth=2,
        dos_max_per_window=10, dos_window_sec=1.0, clock=clock,
    )
    service = FakeGmail()
    sender = GmailSender(service, "prof@example.com", mode=MODE_SEND, gatekeeper=keeper)
    assert sender.send_report("s", "r.json", {"n": 1}) == "sent"
    assert sender.send_report("s", "r.json", {"n": 2}) == "queued"
    assert len(service.messages_sent) == 1  # the quota gate held the second
    assert keeper.log[0]["label"] == "r.json"


def test_a_signed_hebrew_report_survives_the_mime_round_trip() -> None:
    """The emailed bytes carry the raw Hebrew signature key, never \\u escapes.

    The league joins both teams' reports on these exact bytes (kit SPEC 2/6):
    an ASCII-escaped or re-serialized attachment hashes differently and nearly
    scored a real team zero.
    """
    from police_thief.infra.email.consensus import SIGNATURE_KEY, sign_report, verify_signed_report
    from police_thief.shared.config_io import canonical_json

    signed = sign_report({"game_uid": "u", "תוצאה": {"ניקוד": [20, 5]}})
    message = build_report_email("prof@example.com", "s", "result.json", signed)
    parsed = email.message_from_bytes(base64.urlsafe_b64decode(message["raw"]))
    attachment = [part for part in parsed.walk()
                  if part.get_content_type() == "application/json"][0]
    raw_bytes = attachment.get_payload(decode=True)
    assert raw_bytes == canonical_json(signed).encode("utf-8")  # byte-identical to disk
    assert SIGNATURE_KEY.encode("utf-8") in raw_bytes  # raw UTF-8, not \uXXXX
    assert b"\\u05d7" not in raw_bytes
    assert verify_signed_report(json.loads(raw_bytes))  # the signature survives transit

    text_part = [part for part in parsed.walk() if part.get_content_type() == "text/plain"][0]
    body_bytes = text_part.get_payload(decode=True)
    assert body_bytes == raw_bytes  # the body is the same bytes, not a separate note
