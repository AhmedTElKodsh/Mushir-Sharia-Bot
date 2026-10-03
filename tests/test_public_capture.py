from __future__ import annotations

import gzip
import io
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta

import pytest

from src.acquisition.public_capture import AccessRecord, PublicCollector, Response, digest, load_decisions
from scripts import capture_entity_identity_pages as identity
from src.acquisition import public_capture as capture_module

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
SITE = "https://research.example"
HTML = b"<html><body>Published standard terms and complete public identity.</body></html>"
ROBOTS = b"User-agent: *\nAllow: /\n"


def record(**kwargs):
    base = AccessRecord("fixture-review", SITE, ("/robots.txt", "/terms", "/other"),
                        "reviewed_allowed", "fixture-terms", "fixture analyst", (NOW - timedelta(minutes=5)).isoformat(),
                        (NOW + timedelta(hours=1)).isoformat())
    return replace(base, **kwargs)


def response(body=HTML, status=200, content_type="text/html; charset=utf-8", **headers):
    return Response(status, {"content-type": content_type, **headers}, body)


def collector(tmp_path, routes=None, records=None, **kwargs):
    calls, waits = [], []
    routes = routes or {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                        SITE + "/terms": response()}
    elapsed = [0.0]

    def sleep(seconds):
        waits.append(seconds)
        elapsed[0] += seconds

    def fetch(url, limit, timeout):
        calls.append(url)
        value = routes[url]
        if isinstance(value, list):
            value = value.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    result = PublicCollector(tmp_path / "run", records if records is not None else [record()],
                             transport=fetch, resolver=lambda *a: [(2, 1, 6, "", ("8.8.8.8", 443))],
                             now=lambda: NOW, sleep=sleep, monotonic=lambda: elapsed[0], **kwargs)
    return result, calls, waits


def test_complete_capture_preserves_artifacts_and_decision_lineage(tmp_path):
    client, calls, _ = collector(tmp_path)
    captured = client.capture("fixture", SITE + "/terms", extractor=identity.extract)
    assert captured["state"] == "captured"
    assert captured["applicability"] == "unreviewed"
    assert calls == [SITE + "/robots.txt", SITE + "/terms"]
    for field in ("raw", "decoded", "extraction"):
        artifact = captured[field]
        assert digest((client.output / artifact["artifact_path"]).read_bytes()) == artifact["sha256"]
    events = [json.loads(line) for line in client.manifest.read_text(encoding="utf-8").splitlines()]
    assert events[0]["record_type"] == "access_decision"
    assert events[0]["decision"]["terms_reference"] == "fixture-terms"
    assert len([e for e in events if e["record_type"] == "attempt"]) == 2
    assert client.finish([captured])["states"] == {"captured": 1}


@pytest.mark.parametrize("status,state", [(401, "login_gated"), (403, "blocked_by_security"), (451, "blocked_by_security")])
@pytest.mark.parametrize("encoding,body", [("br", b"encoded"), ("gzip", b"corrupt gzip")])
def test_encoded_refusal_stops_later_same_host_capture(tmp_path, status, state, encoding, body):
    client, calls, _ = collector(tmp_path, {
        SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
        SITE + "/terms": response(body, status, **{"content-encoding": encoding}),
        SITE + "/other": response(),
    })
    first = client.capture("first", SITE + "/terms")
    assert first["state"] == state
    assert first["encoding_state"] in {"unsupported_content_encoding", "invalid_content_encoding"}
    second = client.capture("second", SITE + "/other")
    assert second["state"] == state
    assert SITE + "/other" not in calls


def test_encoded_rate_limit_preserves_host_retry_after(tmp_path):
    client, calls, _ = collector(tmp_path, {
        SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
        SITE + "/terms": response(b"encoded", 429, **{"content-encoding": "br", "retry-after": "120"}),
        SITE + "/other": response(),
    })
    assert client.capture("first", SITE + "/terms")["state"] == "rate_limited"
    assert client.capture("second", SITE + "/other")["state"] == "retry_deferred"
    assert SITE + "/other" not in calls


@pytest.mark.parametrize("navigation", [b"<nav>Home Products About Contact Help</nav>",
    b"<div role='navigation'>Home Products About Contact Help</div>",
    b"<header>Home Products About Contact Help</header>",
    b"<div role='banner'>Home Products About Contact Help</div>"])
def test_navigation_footer_only_document_requires_render(tmp_path, navigation):
    shell = navigation + b"<main id='root'></main><script>renderTerms()</script><footer>Copyright Company All Rights Reserved</footer>"
    client, _, _ = collector(tmp_path, {
        SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
        SITE + "/terms": response(shell),
    })
    result = client.capture("terms", SITE + "/terms")
    assert result["state"] == "render_needed"
    assert not result["acquisition_complete"]


@pytest.mark.parametrize("change", [{"terms_state": "unknown"}, {"terms_state": "restricted"},
                                    {"revoked": True}, {"expires_at": NOW.isoformat()},
                                    {"allowed_paths": ("/other",)}, {"origin": "https://different.example"}])
def test_invalid_access_never_requests_content(tmp_path, change):
    client, calls, _ = collector(tmp_path, records=[record(**change)])
    assert client.capture("test", SITE + "/terms")["state"] != "captured"
    assert calls == []


def test_no_decision_and_ambiguous_decisions_refuse_before_request(tmp_path):
    client, calls, _ = collector(tmp_path, records=[])
    assert client.capture("test", SITE + "/terms")["state"] == "access_decision_missing_or_expired"
    assert calls == []
    other, calls, _ = collector(tmp_path / "other", records=[record(), record(decision_id="second")])
    assert other.capture("test", SITE + "/terms")["state"] == "access_decision_ambiguous"
    assert calls == []


@pytest.mark.parametrize("robots,expected", [
    (response(b"", 404, "text/plain"), "robots_missing_unacknowledged"),
    (response(b"", content_type="text/plain"), "robots_empty_unacknowledged"),
    (response(b"<html><body>App shell</body></html>"), "robots_malformed"),
    (response(b"<title>Request Rejected</title>"), "blocked_by_security"),
    (response(b"", 401), "login_gated"), (response(b"", 403), "blocked_by_security"),
    (response(b"", 429), "rate_limited"), (response(b"", 503), "robots_unreachable"),
    (response(b"garbage", content_type="text/plain"), "robots_malformed"),
    (response(b"User-agent: *\nDisallow: /terms", content_type="text/plain"), "robots_disallowed"),
])
def test_robots_states_do_not_become_permission(tmp_path, robots, expected):
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": robots})
    assert client.capture("test", SITE + "/terms")["state"] == expected
    assert calls == [SITE + "/robots.txt"]


@pytest.mark.parametrize("state,status,body", [("robots_missing", 404, b""), ("robots_empty", 200, b"# comment")])
def test_current_payload_acknowledgement_is_consumed(tmp_path, state, status, body):
    approval = record(robots_acknowledgement={"state": state, "sha256": digest(body)})
    routes = {SITE + "/robots.txt": response(body, status, "text/plain"), SITE + "/terms": response()}
    client, _, _ = collector(tmp_path, routes, [approval])
    assert client.capture("test", SITE + "/terms")["state"] == "captured"
    changed, calls, _ = collector(tmp_path / "changed", routes, [replace(approval,
                                           robots_acknowledgement={"state": state, "sha256": "old"})])
    assert changed.capture("test", SITE + "/terms")["state"] == state + "_unacknowledged"
    assert len(calls) == 1


def test_source_robots_exception_never_defeats_live_security(tmp_path):
    robots = b"User-agent: *\nDisallow: /terms"
    permission = {"issuer": "fixture source", "reference": "fixture written permission",
                  "robots_exception": True, "robots_sha256": digest(robots)}
    routes = {SITE + "/robots.txt": response(robots, content_type="text/plain"),
              SITE + "/terms": response(b"<title>Access Denied</title>")}
    client, calls, _ = collector(tmp_path, routes, [record(source_permission=permission)])
    assert client.capture("test", SITE + "/terms")["state"] == "blocked_by_security"
    assert len(calls) == 2


@pytest.mark.parametrize("blocked,state", [
    (response(b"<title>Verify you are human</title>"), "blocked_by_security"),
    (response(b"<form><input type='password'></form>"), "login_gated"),
    (response(b"<title>Subscription required</title>"), "paywall_gated"),
    (response(b"<script src='/cdn-cgi/challenge-platform/test'></script>"), "blocked_by_security"),
    (response(b"<div id='root'></div><script>render()</script>"), "render_needed"),
    (response(b"", 401), "login_gated"), (response(b"", 403), "blocked_by_security"),
    (response(b"<title>Access Denied</title>", 503), "blocked_by_security"),
])
def test_gates_and_shells_are_not_success(tmp_path, blocked, state):
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                          SITE + "/terms": blocked})
    result = client.capture("test", SITE + "/terms")
    assert result["state"] == state
    assert not result["acquisition_complete"]
    assert "extraction" not in result
    assert calls.count(SITE + "/terms") == 1


@pytest.mark.parametrize("target", ["https://other.example/terms", "http://127.0.0.1/private", "/private"])
def test_redirect_destination_is_rechecked_before_request(tmp_path, target):
    routes = {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
              SITE + "/terms": response(b"", 302, location=target)}
    client, calls, _ = collector(tmp_path, routes)
    assert client.capture("test", SITE + "/terms")["state"] != "captured"
    assert calls == [SITE + "/robots.txt", SITE + "/terms"]


def test_robots_redirect_cannot_escape_scope(tmp_path):
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(b"", 302, location="https://other.example/robots.txt")})
    assert client.capture("test", SITE + "/terms")["state"] == "access_decision_missing_or_expired"
    assert calls == [SITE + "/robots.txt"]


def test_private_dns_is_rejected_before_robots(tmp_path):
    client, calls, _ = collector(tmp_path)
    client.resolver = lambda *a: [(2, 1, 6, "", ("127.0.0.1", 443))]
    assert client.capture("test", SITE + "/terms")["state"] == "unsafe_or_invalid_url"
    assert calls == []


def test_rate_limits_and_transient_retries_are_bounded(tmp_path):
    routes = {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
              SITE + "/terms": [response(b"", 429, **{"retry-after": "5"}), response(b"", 503), response()]}
    client, calls, waits = collector(tmp_path, routes)
    assert client.capture("test", SITE + "/terms")["state"] == "captured"
    assert calls.count(SITE + "/terms") == 3
    assert 5 in waits
    failing, calls, _ = collector(tmp_path / "failing", {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                                        SITE + "/terms": response(b"", 503)})
    assert failing.capture("test", SITE + "/terms")["state"] == "server_failed"
    assert calls.count(SITE + "/terms") == 3


def test_long_retry_after_defers_and_robots_timeout_is_not_missing(tmp_path):
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                          SITE + "/terms": response(b"", 429, **{"retry-after": "3600"})})
    assert client.capture("test", SITE + "/terms")["state"] == "retry_deferred"
    assert len(calls) == 2
    timeout, calls, _ = collector(tmp_path / "timeout", {SITE + "/robots.txt": TimeoutError()})
    assert timeout.capture("test", SITE + "/terms")["state"] == "robots_unreachable"
    assert len(calls) == 1


def test_limits_and_old_runs_are_preserved(tmp_path):
    client, calls, _ = collector(tmp_path, max_requests=1)
    assert client.capture("test", SITE + "/terms")["state"] == "request_budget_exhausted"
    assert len(calls) == 1
    original = client.manifest.read_bytes()
    with pytest.raises(FileExistsError):
        PublicCollector(client.output, [])
    assert client.manifest.read_bytes() == original


def test_compressed_wire_and_decoded_bytes_have_distinct_lineage(tmp_path):
    compressed = gzip.compress(HTML)
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                       SITE + "/terms": response(compressed, **{"content-encoding": "gzip"})})
    result = client.capture("test", SITE + "/terms")
    assert result["state"] == "captured"
    assert result["raw"]["sha256"] == digest(compressed)
    assert result["decoded"]["sha256"] == digest(HTML)


@pytest.mark.parametrize("compressed", [False, True])
def test_oversized_body_is_never_complete(tmp_path, compressed):
    body = b"x" * 500
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                      SITE + "/terms": response(gzip.compress(body) if compressed else body,
                                         **({"content-encoding": "gzip"} if compressed else {}))}, max_bytes=100)
    assert client.capture("test", SITE + "/terms")["state"] == (
        "decoded_response_too_large" if compressed else "response_too_large")


def test_declared_windows_1256_preserves_arabic_and_ordinary_captcha_mentions(tmp_path):
    text = "<html><body>الشركة للتمويل الاستهلاكي. CAPTCHA is a term in this privacy policy.</body></html>"
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                      SITE + "/terms": response(text.encode("windows-1256"), content_type="text/html; charset=windows-1256")})
    result = client.capture("test", SITE + "/terms")
    assert result["state"] == "captured"
    data = json.loads((client.output / result["extraction"]["artifact_path"]).read_text(encoding="utf-8"))
    assert "الشركة" in data["text"]


def pdf_bytes(encrypted=False):
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    if encrypted:
        writer.encrypt("fixture-password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize("body,expected", [(pdf_bytes(), "ocr_needed"),
                                          (pdf_bytes(True), "pdf_encrypted"), (b"%PDF-broken", "pdf_parse_failed")])
def test_pdf_capture_preserves_raw_and_explicit_extraction_gaps(tmp_path, body, expected):
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                      SITE + "/terms": response(body, content_type="application/pdf")})
    result = client.capture("test", SITE + "/terms")
    assert result["state"] == "captured"
    assert result["extraction_status"] == expected
    assert result["raw"]["sha256"] == digest(body)


def test_decision_json_and_cli_roundtrip(tmp_path, monkeypatch, capsys):
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps([asdict(record())]), encoding="utf-8")
    assert load_decisions(path) == [record()]
    urls = tmp_path / "urls.txt"
    urls.write_text("fixture " + SITE + "/terms\n", encoding="utf-8")
    actual, _, _ = collector(tmp_path / "fixture")
    def real_collector(output, decisions, **kwargs):
        return PublicCollector(output, decisions, transport=actual.transport, resolver=actual.resolver,
                               now=actual.now, sleep=actual.sleep, monotonic=actual.monotonic, **kwargs)
    monkeypatch.setattr(identity, "PublicCollector", real_collector)
    assert identity.main([str(urls), "--decisions", str(path), "--output-root", str(tmp_path / "out"), "--run-id", "fixture"]) == 0
    assert json.loads(capsys.readouterr().out)["states"] == {"captured": 1}
    events = [json.loads(line) for line in (tmp_path / "out/fixture/manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(e.get("decision", {}).get("terms_reference") == "fixture-terms" for e in events)


def test_empty_decisions_cli_records_gap_without_network(tmp_path, capsys):
    decisions = tmp_path / "decisions.json"
    decisions.write_text("[]", encoding="utf-8")
    urls = tmp_path / "urls.txt"
    urls.write_text("fixture https://8.8.8.8/terms", encoding="utf-8")
    assert identity.main([str(urls), "--decisions", str(decisions), "--output-root", str(tmp_path / "out"), "--run-id", "empty"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["request_count"] == 0
    assert result["states"] == {"access_decision_missing_or_expired": 1}


def test_redirect_loop_is_bounded_and_never_complete(tmp_path):
    client, calls, _ = collector(tmp_path, {
        SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
        SITE + "/terms": response(b"", 302, location="/terms")}, max_hops=2)
    assert client.capture("loop", SITE + "/terms")["state"] == "redirect_limit"
    assert calls.count(SITE + "/terms") == 3


def test_expiry_during_rate_wait_prevents_content_request(tmp_path):
    client, calls, waits = collector(tmp_path, records=[record(expires_at=(NOW + timedelta(seconds=1)).isoformat())])
    elapsed = [0.0]
    client.now = lambda: NOW + timedelta(seconds=elapsed[0])
    client.monotonic = lambda: elapsed[0]
    client.sleep = lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds)
    assert client.capture("expires", SITE + "/terms")["state"] == "access_decision_missing_or_expired"
    assert calls == [SITE + "/robots.txt"]


def test_policy_cache_refresh_invalidates_prior_missing_ack(tmp_path):
    client, calls, _ = collector(tmp_path, {
        SITE + "/robots.txt": [response(b"", 404, "text/plain"), response(b"new missing page", 404, "text/plain")],
        SITE + "/terms": response()}, records=[record(robots_acknowledgement={"state": "robots_missing", "sha256": digest(b"")})])
    assert client.capture("first", SITE + "/terms")["state"] == "captured"
    # Advance monotonic policy age without expiring the injected access decision.
    client.monotonic = lambda: 86401.0
    assert client.capture("changed", SITE + "/terms")["state"] == "robots_missing_unacknowledged"
    assert calls.count(SITE + "/terms") == 1


@pytest.mark.parametrize("body,headers,expected", [
    (b"broken", {"content-encoding": "gzip"}, "invalid_content_encoding"),
    (b"text", {"content-encoding": "br"}, "unsupported_content_encoding"),
    (b"\xff" * 40, {}, "text_encoding_unresolved"),
    (HTML, {"content-type": "text/html; charset=unknown-fixture"}, "text_encoding_unresolved"),
])
def test_encoding_gaps_never_emit_success(tmp_path, body, headers, expected):
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                      SITE + "/terms": response(body, **headers)})
    result = client.capture("encoding", SITE + "/terms")
    assert result["state"] == expected
    assert result["acquisition_complete"] is False


def text_pdf_bytes(blank=False, text=b"Public standard terms fixture"):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 200 Td (" + text + b") Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream.flate_encode())
    if blank:
        writer.add_blank_page(width=300, height=300)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_pdf_text_has_real_one_based_page_anchors(tmp_path):
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                      SITE + "/terms": response(text_pdf_bytes(), content_type="application/pdf")})
    result = client.capture("pdf", SITE + "/terms")
    assert result["extraction_status"] == "page_text"
    extracted = json.loads((client.output / result["extraction"]["artifact_path"]).read_text(encoding="utf-8"))
    assert extracted["pages"] == [{"page": 1, "text": "Public standard terms fixture"}]


@pytest.mark.parametrize("rules,path,allowed", [
    ("Allow: /\nDisallow: /terms", "/terms", False),
    ("Disallow: /terms*", "/terms", False),
    ("Disallow: /*terms$", "/terms", False),
    ("Disallow: /\nAllow: /terms", "/terms", True),
    ("Disallow: /terms\nAllow: /terms", "/terms", True),
    ("Disallow: /terms$", "/terms?lang=en", True),
    ("Disallow: /%74erms", "/terms", False),
    ("Allow: /\nUser-agent: *\nDisallow: /terms", "/terms", False),
])
def test_robots_specificity_wildcards_anchors_and_merged_groups(tmp_path, rules, path, allowed):
    policy = ("User-agent: *\n" + rules).encode()
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(policy, content_type="text/plain"),
                                         SITE + path: response()}, records=[record(allowed_paths=("/robots.txt", path))])
    result = client.capture("rules", SITE + path)
    assert result["state"] == ("captured" if allowed else "robots_disallowed")
    assert (SITE + path in calls) is allowed


@pytest.mark.parametrize("hash_value,expected", [(digest(b"User-agent: *\nDisallow: /"), "captured"),
                                              ("old-policy", "robots_disallowed"), (None, "robots_disallowed")])
def test_source_exception_requires_current_hash(tmp_path, hash_value, expected):
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(b"User-agent: *\nDisallow: /", content_type="text/plain"),
                                         SITE + "/terms": response()}, records=[record(source_permission={
        "issuer": "fixture source", "reference": "fixture permission", "robots_exception": True, "robots_sha256": hash_value})])
    assert client.capture("source", SITE + "/terms")["state"] == expected
    assert (SITE + "/terms" in calls) is (expected == "captured")


def test_deferred_host_is_not_requested_for_a_second_url(tmp_path):
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                         SITE + "/terms": response(b"", 429, **{"retry-after": "3600"})})
    first = client.capture("first", SITE + "/terms")
    assert first["state"] == "retry_deferred" and first["next_permitted_at"]
    assert client.capture("second", SITE + "/other")["state"] == "retry_deferred"
    assert calls == [SITE + "/robots.txt", SITE + "/terms"]


def test_final_attempt_honors_host_cooldown(tmp_path):
    client, calls, waits = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
        SITE + "/terms": [response(b"", 503), response(b"", 503), response(b"", 429, **{"retry-after": "3600"})]})
    assert client.capture("final", SITE + "/terms")["state"] == "retry_deferred"
    assert client.capture("next", SITE + "/other")["state"] == "retry_deferred"
    assert len(calls) == 4


def test_hostname_pacing_spans_schemes(tmp_path):
    other = SITE.replace("https:", "http:")
    approval = record(origin=other, decision_id="http-fixture")
    client, _, waits = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                          other + "/terms": response()}, records=[record(), approval])
    client.request(SITE + "/robots.txt", "robots")
    client.request(other + "/terms", "content")
    assert waits == [2.0]


@pytest.mark.parametrize("body,expected", [
    (b"<head><title>Consumer Finance Terms and Conditions</title></head><body><div id='root'></div></body>", "render_needed"),
    (b"<h2>Access Denied</h2>", "blocked_by_security"),
    (b" " * 270000 + b"<h3>Verify you are human</h3>", "blocked_by_security"),
    (b"Access denied", "blocked_by_security"),
], ids=["titled-shell", "h2-denial", "late-h3-denial", "plain-denial"])
def test_head_only_shell_and_security_headings(tmp_path, body, expected):
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                      SITE + "/terms": response(body)})
    assert client.capture("gate", SITE + "/terms")["state"] == expected


def test_gated_robots_redirect_never_follows_location(tmp_path):
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(b"<h2>Access denied</h2>", 302, location="/other")})
    assert client.capture("robots-gate", SITE + "/terms")["state"] == "blocked_by_security"
    assert calls == [SITE + "/robots.txt"]


@pytest.mark.parametrize("path", ["/public/../private", "/public/%2e%2e/private", "/public/./terms"])
def test_noncanonical_targets_never_reach_transport(tmp_path, path):
    client, calls, _ = collector(tmp_path, records=[record(allowed_paths=("/robots.txt", path))])
    assert client.capture("canonical", SITE + path)["state"] == "unsafe_or_invalid_url"
    assert calls == []


def test_each_attempt_has_scoped_snapshot_headers_and_wire_lineage(tmp_path):
    policy = gzip.compress(ROBOTS)
    robot_decision = record(decision_id="robots-only", allowed_paths=("/robots.txt",))
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(policy, content_type="text/plain", **{"content-encoding": "gzip", "set-cookie": "secret"}),
                                       SITE + "/terms": response()}, records=[robot_decision, record(allowed_paths=("/terms",))])
    assert client.capture("audit", SITE + "/terms")["state"] == "captured"
    events = [json.loads(line) for line in client.manifest.read_text(encoding="utf-8").splitlines()]
    assert any(e.get("decision", {}).get("decision_id") == "robots-only" for e in events)
    attempt = next(e for e in events if e["record_type"] == "attempt")
    assert attempt["headers"]["content-encoding"] == "gzip" and "set-cookie" not in attempt["headers"]
    assert attempt["raw"]["sha256"] == digest(policy) and attempt["decoded"]["sha256"] == digest(ROBOTS)


def test_stream_limit_has_one_attempt_and_output_failure_never_retries(tmp_path):
    client, calls, _ = collector(tmp_path)
    client.transport = lambda *a: (_ for _ in ()).throw(capture_module.CaptureStop("response_too_large", bytes_received=101))
    assert client.capture("limit", SITE + "/terms")["state"] == "response_too_large"
    events = [json.loads(line) for line in client.manifest.read_text(encoding="utf-8").splitlines()]
    assert len([e for e in events if e["record_type"] == "attempt"]) == client.request_count == 1
    other, calls, _ = collector(tmp_path / "disk")
    other.artifact = lambda *a, **kw: (_ for _ in ()).throw(OSError("fixture output failure"))
    with pytest.raises(OSError):
        other.capture("disk", SITE + "/terms")
    assert calls == [SITE + "/robots.txt"]
    events = [json.loads(line) for line in other.manifest.read_text(encoding="utf-8").splitlines()]
    assert len([e for e in events if e["record_type"] == "attempt"]) == 1
    assert events[-1]["state"] == "output_failed"


def test_production_adapter_pins_dns_preserves_redirect_and_limits_stream(tmp_path, monkeypatch):
    requests, connects, tls = [], [], []
    payload = [b"HTTP/1.1 302 Found\r\nLocation: http://private.example/secret\r\nContent-Length: 0\r\n\r\n"]
    dns_calls = []
    def dns(*a, **kw):
        dns_calls.append(a)
        return [(2, 1, 6, "", ("8.8.8.8" if len(dns_calls) == 1 else "127.0.0.1", 443))]
    class Socket:
        def settimeout(self, value): pass
        def connect(self, address): connects.append(address)
        def sendall(self, value): requests.append(value)
        def makefile(self, *a, **kw): return io.BytesIO(payload[0])
        def close(self): pass
    monkeypatch.setattr(capture_module.socket, "getaddrinfo", dns)
    monkeypatch.setattr(capture_module.socket, "socket", lambda *a: Socket())
    def wrap(context, stream, server_hostname):
        assert context.check_hostname and context.verify_mode == capture_module.ssl.CERT_REQUIRED
        tls.append(server_hostname)
        return stream
    monkeypatch.setattr(capture_module.ssl.SSLContext, "wrap_socket", wrap)
    result = capture_module.http_transport(SITE + "/terms", 100, 5)
    assert result.status == 302 and result.headers["location"] == "http://private.example/secret"
    assert len(requests) == len(dns_calls) == 1 and connects == [("8.8.8.8", 443)]
    assert tls == ["research.example"] and b"GET /terms HTTP/1.1" in requests[0]
    payload[0] = b"HTTP/1.1 200 OK\r\nContent-Length: 101\r\n\r\n" + b"x" * 101
    dns_calls.clear()
    with pytest.raises(capture_module.CaptureStop, match="response_too_large"):
        capture_module.http_transport(SITE + "/terms", 100, 5)


def test_production_adapter_whole_request_deadline(monkeypatch):
    elapsed = [0.0]
    class Stream(io.BytesIO):
        def read1(self, n):
            elapsed[0] += 0.6
            return super().read1(1)
    class Socket:
        def settimeout(self, value): pass
        def connect(self, address): pass
        def sendall(self, value): pass
        def makefile(self, *a, **kw): return Stream(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n" + b"x" * 100)
        def close(self): pass
    monkeypatch.setattr(capture_module.time, "monotonic", lambda: elapsed[0])
    monkeypatch.setattr(capture_module.socket, "socket", lambda *a: Socket())
    monkeypatch.setattr(capture_module.socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", ("8.8.8.8", 80))])
    with pytest.raises(capture_module.CaptureStop, match="request_timeout"):
        capture_module.http_transport("http://research.example/terms", 200, 1)


def test_pdf_worker_timeout_is_an_explicit_gap(monkeypatch):
    def timeout(*a, **kw): raise capture_module.subprocess.TimeoutExpired(a[0], 0.01)
    monkeypatch.setattr(capture_module.subprocess, "run", timeout)
    assert capture_module.extract_pdf(b"%PDF-", 100)["status"] == "pdf_extraction_timeout"


def test_mixed_pdf_pages_have_explicit_ocr_gaps():
    result = capture_module.extract_pdf(text_pdf_bytes(blank=True), 3 * 1024 * 1024)
    assert result["status"] == "partial_page_text" and result["ocr_needed_pages"] == [2]
    assert result["pages"][1] == {"page": 2, "text": ""}


def test_compressed_pdf_expansion_stops_at_extraction_budget():
    body = text_pdf_bytes(text=b"A" * 100000)
    assert len(body) < 4096
    result = capture_module.extract_pdf(body, 4096)
    assert result["status"] == "extraction_too_large" and result["pages"] == []


def test_source_exception_invalidates_after_policy_refresh(tmp_path):
    old = b"User-agent: *\nDisallow: /terms"
    new = old + b"\n# new version"
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": [response(old, content_type="text/plain"), response(new, content_type="text/plain")],
                                         SITE + "/terms": response()}, records=[record(source_permission={
        "issuer": "fixture", "reference": "fixture", "robots_exception": True, "robots_sha256": digest(old)})])
    assert client.capture("before", SITE + "/terms")["state"] == "captured"
    client.monotonic = lambda: 86401.0
    assert client.capture("after", SITE + "/terms")["state"] == "robots_disallowed"
    assert calls.count(SITE + "/terms") == 1


def test_http_date_retry_after_is_respected(tmp_path):
    client, calls, waits = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
        SITE + "/terms": [response(b"", 429, **{"retry-after": "Thu, 01 Oct 2026 12:00:10 GMT"}), response()]})
    assert client.capture("date", SITE + "/terms")["state"] == "captured"
    assert 10.0 in waits


def test_arabic_security_heading_with_declared_charset_stops(tmp_path):
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
        SITE + "/terms": response("<h2>الوصول مرفوض</h2>".encode("windows-1256"), content_type="text/html; charset=windows-1256")})
    assert client.capture("arabic-denial", SITE + "/terms")["state"] == "blocked_by_security"


def test_production_adapter_header_deadline_interrupts_blocking_read(monkeypatch):
    import threading
    interrupted = threading.Event()
    class BlockingHeaders(io.BytesIO):
        def readline(self, *args):
            assert interrupted.wait(1), "whole-request timer did not interrupt header read"
            raise OSError("fixture interrupted socket")
    class Socket:
        def settimeout(self, value): pass
        def connect(self, address): pass
        def sendall(self, value): pass
        def makefile(self, *a, **kw): return BlockingHeaders()
        def shutdown(self, direction): interrupted.set()
        def close(self): pass
    monkeypatch.setattr(capture_module.socket, "socket", lambda *a: Socket())
    monkeypatch.setattr(capture_module.socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", ("8.8.8.8", 80))])
    with pytest.raises(capture_module.CaptureStop, match="request_timeout"):
        capture_module.http_transport("http://research.example/terms", 100, 0.03)


def test_production_adapter_private_dns_answer_never_connects(monkeypatch):
    monkeypatch.setattr(capture_module.socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", ("127.0.0.1", 80))])
    def no_socket(*a): pytest.fail("private address reached socket creation")
    monkeypatch.setattr(capture_module.socket, "socket", no_socket)
    with pytest.raises(ValueError, match="non-public"):
        capture_module.http_transport("http://research.example/terms", 100, 1)


@pytest.mark.parametrize("body,expected", [(b"User-agent:\nDisallow: /terms", "robots_malformed"),
                                         (b"User-agent:\nAllow", "robots_malformed")])
def test_empty_agent_policy_remains_unresolved(tmp_path, body, expected):
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(body, content_type="text/plain")})
    assert client.capture("empty-agent", SITE + "/terms")["state"] == expected
    assert calls == [SITE + "/robots.txt"]


def test_corrupt_deflate_has_audited_failure(tmp_path):
    body = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\xff" + b"\x00" * 8
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
        SITE + "/terms": response(body, **{"content-encoding": "gzip"})})
    assert client.capture("deflate", SITE + "/terms")["state"] == "invalid_content_encoding"
    events = [json.loads(line) for line in client.manifest.read_text(encoding="utf-8").splitlines()]
    assert len([e for e in events if e["record_type"] == "attempt"]) == client.request_count == 2


@pytest.mark.parametrize("body", [b"<h2>Forbidden activities</h2><p>Public contractual terms describe prohibited acts and customer rights.</p>",
                                  HTML + b"<footer><script src='hcaptcha.js'></script><div class='g-recaptcha'></div></footer>"])
def test_public_prohibitions_and_captcha_assets_are_not_gates(tmp_path, body):
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"), SITE + "/terms": response(body)})
    assert client.capture("public-terms", SITE + "/terms")["state"] == "captured"


def test_div_only_security_denial_stops(tmp_path):
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                      SITE + "/terms": response(b"<div>Access denied</div><p>Contact the owner.</p>")})
    assert client.capture("div", SITE + "/terms")["state"] == "blocked_by_security"


@pytest.mark.parametrize("body,state", [(b"<h1>Access denied</h1>", "blocked_by_security"),
                                       (b"<h1>Login required</h1>", "login_gated"),
                                       (b"<h1>Subscription required</h1>", "paywall_gated")])
def test_gate_pauses_later_capture_across_same_hostname_origins(tmp_path, body, state):
    other = SITE.replace("https:", "http:")
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                          SITE + "/terms": response(body)}, records=[record(), record(origin=other, decision_id="http-fixture")])
    assert client.capture("gate", SITE + "/terms")["state"] == state
    prior = list(calls)
    assert client.capture("later", other + "/terms")["state"] == state
    assert calls == prior


def test_transient_robots_failure_can_recover_after_cooldown(tmp_path):
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": [response(b"", 503), response(ROBOTS, content_type="text/plain")],
                                          SITE + "/terms": response()})
    assert client.capture("failure", SITE + "/terms")["state"] == "robots_unreachable"
    assert client.capture("recovered", SITE + "/terms")["state"] == "captured"
    assert calls.count(SITE + "/robots.txt") == 2


def test_real_timeout_category_retries_content_but_not_robots(tmp_path):
    timeout = capture_module.CaptureStop("request_timeout")
    client, calls, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
                                          SITE + "/terms": [timeout, response()]})
    assert client.capture("retry", SITE + "/terms")["state"] == "captured"
    assert calls.count(SITE + "/terms") == 2
    other, calls, _ = collector(tmp_path / "robots", {SITE + "/robots.txt": timeout})
    assert other.capture("robots", SITE + "/terms")["state"] == "robots_unreachable"
    assert len(calls) == 1


def test_glob_repeated_stars_does_not_backtrack():
    assert capture_module.robots_rules(b"User-agent: *\nDisallow: /" + b"*a" * 30 + b"b$", SITE + "/" + "a" * 200)[0]
    assert not capture_module.robots_rules(b"User-agent: *\nDisallow: /" + b"*a" * 30 + b"$", SITE + "/" + "a" * 200)[0]


def test_crawl_delay_is_scoped_and_refresh_can_lower_it(tmp_path):
    other = "https://other.example"
    slow = b"User-agent: *\nAllow: /\nCrawl-delay: 10"
    client, _, waits = collector(tmp_path, {SITE + "/robots.txt": [response(slow, content_type="text/plain"), response(ROBOTS, content_type="text/plain")],
        SITE + "/terms": response(), other + "/robots.txt": response(ROBOTS, content_type="text/plain"), other + "/terms": response()},
        records=[record(), record(origin=other, decision_id="other-fixture")])
    assert client.capture("slow", SITE + "/terms")["state"] == "captured" and waits == [10]
    assert client.capture("other", other + "/terms")["state"] == "captured" and waits[-1] == 2
    client.monotonic = lambda: 86401
    assert client.capture("refresh", SITE + "/terms")["state"] == "captured"
    assert client.policy_delays[SITE] == 0


def test_production_dns_resolution_and_collector_preflight_are_bounded(monkeypatch, tmp_path):
    import threading
    hold = threading.Event()
    monkeypatch.setattr(capture_module.socket, "getaddrinfo", lambda *a, **kw: hold.wait(1))
    try:
        with pytest.raises(capture_module.CaptureStop, match="request_timeout"):
            capture_module.http_transport(SITE + "/terms", 100, 0.01)
        client, calls, _ = collector(tmp_path, timeout=0.01)
        client.resolver = lambda *a: hold.wait(1)
        assert client.capture("dns", SITE + "/terms")["state"] == "dns_timeout"
        assert calls == []
    finally:
        hold.set()


def test_production_framing_and_address_fallback(monkeypatch):
    connects = []
    class Socket:
        def settimeout(self, value): pass
        def connect(self, address):
            connects.append(address)
            if address[0] == "2001:4860:4860::8888": raise OSError("fixture IPv6 unavailable")
        def sendall(self, value): pass
        def makefile(self, *a, **kw): return io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n" + HTML)
        def close(self): pass
    monkeypatch.setattr(capture_module.socket, "socket", lambda *a: Socket())
    monkeypatch.setattr(capture_module.socket, "getaddrinfo", lambda *a, **kw: [(10, 1, 6, "", ("2001:4860:4860::8888", 80, 0, 0)), (2, 1, 6, "", ("8.8.8.8", 80))])
    with pytest.raises(capture_module.CaptureStop, match="response_truncated"):
        capture_module.http_transport("http://research.example/terms", 200, 1)
    assert [address[0] for address in connects] == ["2001:4860:4860::8888", "8.8.8.8"]


def test_literal_observations_have_exact_source_spans_and_truncation():
    result = identity.extract("<head><title>Example Consumer Finance</title></head><body>" +
                              "<p>Example Consumer Finance</p>" * 2 + "".join(f"<p>Entity {i} Consumer Finance</p>" for i in range(15)) + "</body>")
    assert digest(result["source_text"].encode()) == result["source_text_sha256"]
    assert result["observations_truncated"] is True
    assert len(result["observations"]) == 12
    for observation in result["observations"]:
        assert result["source_text"][observation["start"]:observation["end"]] == observation["text"]


def test_pdf_worker_installs_effective_os_memory_and_cpu_limits():
    probe = '''
import ctypes,json,os,struct
from ctypes import wintypes
from src.acquisition.pdf_extract_worker import resource_limits
resource_limits()
if os.name == "nt":
    assert struct.calcsize("P") == 8
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.QueryInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p]
    kernel.QueryInformationJobObject.restype=wintypes.BOOL
    buffer=ctypes.create_string_buffer(144)
    assert kernel.QueryInformationJobObject(resource_limits.job,9,buffer,144,None)
    flags=struct.unpack_from("<I",buffer.raw,16)[0]
    assert flags & 0x100 and flags & 0x2
    cpu=struct.unpack_from("<q",buffer.raw,0)[0]/10000000
    memory=struct.unpack_from("<Q",buffer.raw,112)[0]
else:
    import resource
    cpu=resource.getrlimit(resource.RLIMIT_CPU)[0]
    memory=resource.getrlimit(resource.RLIMIT_AS)[0]
print(json.dumps({"cpu":cpu,"memory":memory}))
'''
    result = capture_module.subprocess.run([capture_module.sys.executable, "-c", probe], capture_output=True, timeout=10, check=True)
    assert json.loads(result.stdout) == {"cpu": 8, "memory": 512 * 1024 * 1024}


def test_pdf_limits_unavailable_refuses_parsing(monkeypatch, capsys):
    from src.acquisition import pdf_extract_worker as worker
    def unavailable(): raise OSError("fixture denied job assignment")
    monkeypatch.setattr(worker, "resource_limits", unavailable)
    monkeypatch.setattr(worker.sys, "argv", ["worker", "100"])
    monkeypatch.setattr(worker, "extract", lambda *a: pytest.fail("uncontained parser was invoked"))
    assert worker.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pdf_limits_unavailable"


def test_product_token_matches_exactly_and_case_insensitively():
    policy = b"User-agent: *\nDisallow: /terms\nUser-agent: Bot\nAllow: /terms"
    assert not capture_module.robots_rules(policy, SITE + "/terms")[0]
    explicit = policy + b"\nUser-agent: mushirresearchbot\nAllow: /terms"
    assert capture_module.robots_rules(explicit, SITE + "/terms")[0]


@pytest.mark.parametrize("permission,expected", [({"issuer": "fixture source", "reference": "fixture approval"}, "captured"),
    ({"reference": "fixture approval"}, "terms_not_permitted"), ({"issuer": "fixture source"}, "terms_not_permitted"),
    ({}, "terms_not_permitted"), ({"issuer": " ", "reference": 123}, "terms_not_permitted")])
def test_source_permission_terms_requires_named_issuer_and_reference(tmp_path, permission, expected):
    client, calls, _ = collector(tmp_path, records=[record(terms_state="source_permission", source_permission=permission)])
    assert client.capture("terms-permission", SITE + "/terms")["state"] == expected
    if expected != "captured": assert calls == []


@pytest.mark.parametrize("field,value", [("reviewed_by", 42), ("decision_id", ["x"]), ("terms_reference", "   "),
                                      ("expires_at", None)])
def test_audit_fields_require_nonblank_strings(field, value):
    with pytest.raises(ValueError, match="nonblank string"):
        record(**{field: value})


def test_explicit_zero_port_is_not_a_default_origin(tmp_path):
    client, calls, _ = collector(tmp_path)
    assert client.capture("port-zero", SITE + ":0/terms")["state"] == "unsafe_or_invalid_url"
    assert calls == []


@pytest.mark.parametrize("markup", ["<script>const charset='windows-1256';</script>",
                                  "<!-- <meta charset='windows-1256'> -->", "<p>charset=windows-1256</p>"])
def test_charset_like_content_does_not_override_utf8(markup):
    text, encoding = capture_module.html_text((markup + "<p>الشركة للتمويل الاستهلاكي</p>").encode(), "text/html")
    assert "الشركة" in text and encoding == "utf-8-sig"


def test_actual_meta_charset_and_valueless_attributes_are_handled():
    text, encoding = capture_module.html_text("<head><meta charset='windows-1256'></head><p>الشركة للتمويل</p>".encode("windows-1256"), "text/html")
    assert encoding == "windows-1256" and "الشركة" in text
    parser = capture_module.VisibleText()
    parser.feed("<meta http-equiv><div aria-hidden style>Public standard terms here.</div>")
    assert "Public standard" in parser.text()


@pytest.mark.parametrize("attribute", ["hidden", "aria-hidden='true'", "style='display: none'", "style='visibility:hidden'"])
def test_explicitly_hidden_content_does_not_make_shell_substantive(tmp_path, attribute):
    body = ("<div " + attribute + ">Obsolete Consumer Finance Company long hidden template</div>").encode()
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"), SITE + "/terms": response(body)})
    assert client.capture("hidden", SITE + "/terms")["state"] == "render_needed"


@pytest.mark.parametrize("control,state", [(b"<form><input type='password'></form>", "login_gated"),
                                         (b"<div class='g-recaptcha'>Complete the CAPTCHA to continue.</div>", "blocked_by_security")])
def test_long_active_gates_still_stop(tmp_path, control, state):
    body = b"<title>Account portal</title><p>" + b"Account access instructions. " * 40 + b"</p>" + control
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"), SITE + "/terms": response(body)})
    assert client.capture("long-gate", SITE + "/terms")["state"] == state


def test_optional_footer_login_does_not_block_public_terms(tmp_path):
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": response(ROBOTS, content_type="text/plain"),
        SITE + "/terms": response(HTML + b"<footer><form><input type='password'></form></footer>")})
    assert client.capture("optional", SITE + "/terms")["state"] == "captured"


def test_repeated_dns_timeouts_bound_outstanding_resolvers(monkeypatch):
    import threading
    slots = threading.BoundedSemaphore(2)
    hold, done = threading.Event(), []
    calls = []
    monkeypatch.setattr(capture_module, "_DNS_SLOTS", slots)
    def blocked(*a):
        calls.append(a)
        hold.wait(1)
        done.append(True)
        return []
    try:
        for _ in range(4):
            with pytest.raises(capture_module.CaptureStop, match="dns_timeout"):
                capture_module._resolve("research.example", 443, blocked, 0.01)
        assert len(calls) == 2
    finally:
        hold.set()


def test_refreshed_acknowledged_empty_policy_clears_crawl_delay(tmp_path):
    client, _, _ = collector(tmp_path, {SITE + "/robots.txt": [response(b"User-agent: *\nCrawl-delay: 10", content_type="text/plain"), response(b"", content_type="text/plain")],
        SITE + "/terms": response()}, records=[record(robots_acknowledgement={"state": "robots_empty", "sha256": digest(b"")})])
    assert client.capture("first", SITE + "/terms")["state"] == "captured"
    client.monotonic = lambda: 86401
    assert client.capture("empty", SITE + "/terms")["state"] == "captured"
    assert client.policy_delays[SITE] == 0


def test_attempts_join_to_capture_and_cached_policy_request(tmp_path):
    client, _, _ = collector(tmp_path)
    first = client.capture("first", SITE + "/terms")
    second = client.capture("second", SITE + "/terms")
    events = [json.loads(line) for line in client.manifest.read_text(encoding="utf-8").splitlines()]
    attempts = [event for event in events if event["record_type"] == "attempt"]
    assert len({event["request_id"] for event in attempts}) == len(attempts)
    assert {event["capture_id"] for event in attempts} == {first["capture_id"], second["capture_id"]}
    assert first["robots"]["policy_request_id"] == second["robots"]["policy_request_id"] == attempts[0]["request_id"]


def test_connection_budget_leaves_time_after_blackholed_first_address(monkeypatch):
    elapsed, connected = [0.0], []
    class Socket:
        def settimeout(self, value): self.timeout = value
        def connect(self, address):
            connected.append(address[0])
            if len(connected) == 1:
                elapsed[0] += self.timeout
                raise TimeoutError("fixture blackhole")
        def sendall(self, value): pass
        def makefile(self, *a, **kw): return io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
        def close(self): pass
    monkeypatch.setattr(capture_module.time, "monotonic", lambda: elapsed[0])
    monkeypatch.setattr(capture_module.socket, "socket", lambda *a: Socket())
    monkeypatch.setattr(capture_module.socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", ("8.8.8.8", 80)), (2, 1, 6, "", ("1.1.1.1", 80))])
    assert capture_module.http_transport("http://research.example/terms", 100, 1).status == 200
    assert connected == ["8.8.8.8", "1.1.1.1"] and elapsed[0] == 0.5


def test_only_one_collector_dns_preflight_per_attempt(tmp_path):
    client, _, _ = collector(tmp_path)
    resolutions = []
    client.resolver = lambda *a: resolutions.append(a) or [(2, 1, 6, "", ("8.8.8.8", 443))]
    assert client.capture("bounded-preflights", SITE + "/terms")["state"] == "captured"
    assert len(resolutions) == client.request_count == 2


def test_attempt_aggregate_budget_is_preflight_plus_http_operation(monkeypatch, tmp_path):
    elapsed = [0.0]
    def resolver(*a, **kw):
        elapsed[0] += 0.6
        return [(2, 1, 6, "", ("8.8.8.8", 80))]
    class Socket:
        def settimeout(self, value): pass
        def connect(self, address): pass
        def sendall(self, value): pass
        def makefile(self, *a, **kw): return io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
        def close(self): pass
    client, _, _ = collector(tmp_path, records=[record(origin="http://research.example")], timeout=1)
    client.resolver, client.transport = resolver, capture_module.http_transport
    monkeypatch.setattr(capture_module.time, "monotonic", lambda: elapsed[0])
    monkeypatch.setattr(capture_module.socket, "getaddrinfo", resolver)
    monkeypatch.setattr(capture_module.socket, "socket", lambda *a: Socket())
    assert client.request("http://research.example/terms", "content")[0].status == 200
    assert elapsed[0] == 1.2 and elapsed[0] <= 2 * client.timeout
