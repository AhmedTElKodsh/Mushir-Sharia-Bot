"""Scoped, bounded public-document capture; acquisition is not claim verification."""
from __future__ import annotations

import gzip
import hashlib
import io
import http.client
import json
import queue
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
import uuid
import zlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from src.acquisition.url_safety import ensure_public_url

USER_AGENT = "MushirResearchBot/0.2 (+public-source evidence research)"
TOOL_VERSION = "public_capture/0.2"
_DNS_SLOTS = threading.BoundedSemaphore(8)


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("decision dates require a timezone")
    return parsed.astimezone(UTC)


def origin(url: str) -> str:
    if len(url) > 8192:
        raise ValueError("URL exceeds the request-target budget")
    if not url.isascii() or any(ord(c) <= 32 or ord(c) == 127 for c in url) or "\\" in url:
        raise ValueError("URL must use ASCII percent encoding without whitespace/backslashes")
    parts = urlsplit(url)
    if parts.scheme not in {"https", "http"} or not parts.hostname:
        raise ValueError("public HTTP(S) URL required")
    if parts.username or parts.password or parts.fragment:
        raise ValueError("credentials and fragments are not permitted")
    if any(segment in {".", ".."} for segment in unquote(parts.path).split("/")):
        raise ValueError("dot-segment paths are not permitted")
    port = parts.port
    if port == 0:
        raise ValueError("port zero is not a public origin")
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    suffix = f":{port}" if port and port != (443 if parts.scheme == "https" else 80) else ""
    return f"{parts.scheme}://{host}{suffix}"


def request_path(url: str) -> str:
    parts = urlsplit(url)
    return (parts.path or "/") + (f"?{parts.query}" if parts.query else "")


@dataclass(frozen=True)
class AccessRecord:
    decision_id: str
    origin: str
    allowed_paths: tuple[str, ...]
    terms_state: str
    terms_reference: str
    reviewed_by: str
    reviewed_at: str
    expires_at: str
    revoked: bool = False
    robots_acknowledgement: dict = field(default_factory=dict)
    source_permission: dict = field(default_factory=dict)
    reuse_rights: str = "internal_research_only"

    def __post_init__(self):
        for name in ("decision_id", "origin", "terms_state", "terms_reference", "reviewed_by", "reviewed_at", "expires_at", "reuse_rights"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a nonblank string")
        if self.origin != origin(self.origin) or request_path(self.origin) != "/":
            raise ValueError("decision origin must be a canonical origin without a path/query")
        if not self.decision_id or not self.reviewed_by or not self.terms_reference:
            raise ValueError("decision id, reviewer and terms reference are required")
        if not self.allowed_paths or any(not isinstance(p, str) or not p.startswith("/") or
                                         "*" in p or "#" in p for p in self.allowed_paths):
            raise ValueError("allowed_paths must contain exact paths/query strings, without wildcards")
        if self.terms_state not in {"reviewed_allowed", "source_permission", "unknown", "restricted"}:
            raise ValueError("invalid terms_state")
        if utc(self.expires_at) <= utc(self.reviewed_at):
            raise ValueError("decision expiry must follow review")
        if not isinstance(self.revoked, bool):
            raise ValueError("revoked must be boolean")
        if not isinstance(self.robots_acknowledgement, dict) or not isinstance(self.source_permission, dict):
            raise ValueError("permission/acknowledgement must be objects")

    def current(self, url: str, now: datetime) -> bool:
        return (not self.revoked and utc(self.reviewed_at) <= now < utc(self.expires_at)
                and self.origin == origin(url) and request_path(url) in self.allowed_paths)

    def terms_allowed(self) -> bool:
        if self.terms_state == "reviewed_allowed":
            return True
        return self.terms_state == "source_permission" and bool(
            all(isinstance(self.source_permission.get(k), str) and self.source_permission[k].strip()
                for k in ("issuer", "reference")))


def load_decisions(path: Path) -> list[AccessRecord]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("decisions must be a JSON array")
    result = []
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("allowed_paths"), list):
            raise ValueError("decision must have an allowed_paths array")
        result.append(AccessRecord(**{**item, "allowed_paths": tuple(item["allowed_paths"])}))
    if len({r.decision_id for r in result}) != len(result):
        raise ValueError("decision ids must be unique")
    return result


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes
    connected_address: str | None = None
    request_id: str | None = None


class CaptureStop(Exception):
    def __init__(self, state: str, **diagnostics):
        self.state = state
        self.diagnostics = diagnostics
        super().__init__(state)


def _resolve(host, port, resolver, timeout):
    started = time.monotonic()
    slots = _DNS_SLOTS
    if not slots.acquire(timeout=timeout):
        raise CaptureStop("dns_timeout")
    result = queue.Queue(maxsize=1)
    def run():
        try:
            result.put((True, resolver(host, port)))
        except Exception as exc:
            result.put((False, exc))
        finally:
            slots.release()
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    try:
        ok, value = result.get(timeout=max(0, timeout - (time.monotonic() - started)))
    except queue.Empty:
        raise CaptureStop("dns_timeout") from None
    if not ok:
        raise value
    return value


def _public_url(url, resolver, timeout):
    parts = urlsplit(url)
    try:
        addresses = _resolve(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), resolver, timeout)
    except OSError:
        raise ValueError("host resolution failed") from None
    ensure_public_url(url, resolver=lambda *a: addresses)
    return addresses


def http_transport(url: str, max_bytes: int, timeout: float) -> Response:
    # Resolve once, validate that exact answer set, then connect directly to an IP.
    # The original hostname remains the Host header and TLS SNI/certificate name.
    origin(url)
    parts = urlsplit(url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    deadline = time.monotonic() + timeout
    try:
        addresses = _public_url(url, lambda h, p: socket.getaddrinfo(h, p, type=socket.SOCK_STREAM), timeout)
    except CaptureStop as exc:
        if exc.state == "dns_timeout":
            raise CaptureStop("request_timeout") from None
        raise
    stream = None
    connection = http.client.HTTPConnection(parts.hostname, port, timeout=timeout)
    expired = threading.Event()
    def expire():
        expired.set()
        try:
            if stream is not None:
                stream.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
    timer = threading.Timer(max(0.001, deadline - time.monotonic()), expire)
    timer.daemon = True
    timer.start()
    try:
        candidates = addresses[:8]
        for index, (family, kind, proto, _, address) in enumerate(candidates):
            if time.monotonic() >= deadline:
                raise CaptureStop("request_timeout")
            stream = socket.socket(family, kind, proto)
            stream.settimeout(max(0.001, (deadline - time.monotonic()) / (len(candidates) - index)))
            try:
                stream.connect(address)
                break
            except OSError:
                stream.close()
                stream = None
        if stream is None:
            raise OSError("validated public addresses could not connect")
        if parts.scheme == "https":
            stream.settimeout(max(0.001, deadline - time.monotonic()))
            stream = ssl.create_default_context().wrap_socket(stream, server_hostname=parts.hostname)
        connection.sock = stream
        connection.request("GET", request_path(url), headers={"User-Agent": USER_AGENT,
                           "Accept-Language": "ar,en;q=0.8", "Accept-Encoding": "identity"})
        stream.settimeout(max(0.001, deadline - time.monotonic()))
        response = connection.getresponse()
        headers = {k.lower(): v for k, v in response.getheaders()}
        payload = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CaptureStop("request_timeout", http_status=response.status, bytes_received=len(payload))
            stream.settimeout(remaining)
            chunk = response.read1(min(65536, max_bytes + 1 - len(payload)))
            if not chunk:
                if expired.is_set():
                    raise CaptureStop("request_timeout", http_status=response.status, bytes_received=len(payload))
                if response.length not in (None, 0):
                    raise CaptureStop("response_truncated", http_status=response.status, bytes_received=len(payload))
                break
            payload.extend(chunk)
            if len(payload) > max_bytes:
                raise CaptureStop("response_too_large", http_status=response.status, bytes_received=len(payload))
        return Response(response.status, headers, bytes(payload), address[0])
    except (OSError, http.client.HTTPException):
        if expired.is_set():
            raise CaptureStop("request_timeout") from None
        raise
    finally:
        timer.cancel()
        connection.close()
        if stream is not None:
            stream.close()


def _glob_matches(pattern, text, terminal):
    pieces = pattern.split("*")
    if not text.startswith(pieces[0]):
        return False
    if len(pieces) == 1:
        return not terminal or text == pieces[0]
    cursor = len(pieces[0])
    for piece in pieces[1:-1]:
        found = text.find(piece, cursor)
        if found < 0:
            return False
        cursor = found + len(piece)
    if terminal:
        return text.endswith(pieces[-1]) and len(text) - len(pieces[-1]) >= cursor
    return text.find(pieces[-1], cursor) >= 0


def robots_rules(body: bytes, url: str) -> tuple[bool, float]:
    """RFC 9309 groups and most-specific rules, including * and terminal $."""
    if len(body) > 512 * 1024:
        raise CaptureStop("robots_policy_too_large")
    groups, agents, rules, delays = [], [], [], []
    rule_count = 0
    for line in body.decode("utf-8-sig").splitlines():
        name, sep, value = line.split("#", 1)[0].partition(":")
        if not sep:
            continue
        name, value = name.strip().lower(), value.strip()
        if name == "user-agent":
            if rules or delays:
                groups.append((agents, rules, delays))
                agents, rules, delays = [], [], []
            if value:
                agents.append(value.lower())
        elif agents and name in {"allow", "disallow"}:
            rule_count += 1
            if rule_count > 10000:
                raise CaptureStop("robots_rule_budget")
            rules.append((name, value))
        elif agents and name == "crawl-delay":
            try:
                delay = float(value)
                if 0 <= delay < float("inf"):
                    delays.append(delay)
            except ValueError:
                pass
    groups.append((agents, rules, delays))
    product = USER_AGENT.split("/", 1)[0].lower()
    applicable = []
    for group in groups:
        scores = [0 if a == "*" else len(a) for a in group[0] if a == "*" or a == product]
        if scores:
            applicable.append((max(scores), group))
    if not applicable:
        return True, 0
    best = max(score for score, _ in applicable)

    def normalized(value):
        def octet(match):
            number = int(match.group(1), 16)
            char = chr(number)
            return char if char.isascii() and (char.isalnum() or char in "-._~") else "%" + match.group(1).upper()
        value = "".join(c if ord(c) < 128 else "".join(f"%{b:02X}" for b in c.encode("utf-8")) for c in value)
        return re.sub(r"%([0-9a-fA-F]{2})", octet, value)

    target, matches, delay = normalized(request_path(url)), [], 0.0
    for score, (_, selected, waits) in applicable:
        if score != best:
            continue
        delay = max([delay, *waits])
        for name, value in selected:
            if not value:
                continue
            value = normalized(value)
            end = value.endswith("$")
            literal = value[:-1] if end else value
            if _glob_matches(literal, target, end):
                octets = len(re.sub(r"%[0-9A-F]{2}", "x", literal.replace("*", "")))
                matches.append((octets, name == "allow"))
    return (max(matches)[1] if matches else True), delay


def extract_pdf(body: bytes, limit: int, timeout=10.0) -> dict:
    worker = Path(__file__).with_name("pdf_extract_worker.py")
    try:
        completed = subprocess.run([sys.executable, str(worker), str(limit)], input=body,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "pdf_extraction_timeout", "pages": []}
    if completed.returncode or len(completed.stdout) > limit:
        return {"status": "pdf_resource_limit", "pages": []}
    try:
        return json.loads(completed.stdout)
    except (ValueError, UnicodeError):
        return {"status": "pdf_parse_failed", "pages": []}


def decoded_body(response: Response, limit: int) -> bytes:
    encoding = response.headers.get("content-encoding", "identity").lower()
    if encoding in {"", "identity"}:
        body = response.body
    elif encoding == "gzip":
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(response.body)) as compressed:
                body = compressed.read(limit + 1)
        except (OSError, EOFError, zlib.error):
            raise CaptureStop("invalid_content_encoding") from None
    else:
        raise CaptureStop("unsupported_content_encoding")
    if len(body) > limit:
        raise CaptureStop("decoded_response_too_large")
    return body


class _MetaCharset(HTMLParser):
    def __init__(self):
        super().__init__()
        self.charset = None

    def handle_starttag(self, tag, attrs):
        if tag != "meta" or self.charset:
            return
        values = {key: value or "" for key, value in attrs}
        if values.get("charset"):
            self.charset = values["charset"]
        elif values.get("http-equiv", "").lower() == "content-type":
            match = re.search(r"charset\s*=\s*[\"']?([^\s;\"'>]+)", values.get("content", ""), re.I)
            if match:
                self.charset = match.group(1)


def html_text(body: bytes, content_type: str) -> tuple[str, str]:
    charset = re.search(r"charset\s*=\s*[\"']?([^\s;\"'>]+)", content_type, re.I)
    metadata = _MetaCharset()
    metadata.feed(body[:4096].decode("latin-1"))
    encoding = charset.group(1) if charset else (metadata.charset or "utf-8-sig")
    try:
        return body.decode(encoding, errors="strict"), encoding
    except (UnicodeError, LookupError):
        raise CaptureStop("text_encoding_unresolved") from None


class VisibleText(HTMLParser):
    def __init__(self, excluded_regions=()):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0
        self.stack = []
        self.excluded = {"head", "title", "script", "style", "noscript", *excluded_regions}
        self.forms = []
        self.password_form = False

    def handle_starttag(self, tag, attrs):
        values = {key: value or "" for key, value in attrs}
        hidden = (tag in self.excluded or "hidden" in values or values.get("aria-hidden", "").lower() == "true"
                  or bool(re.search(r"(?i)(?:display\s*:\s*none|visibility\s*:\s*hidden|content-visibility\s*:\s*hidden)", values.get("style", ""))))
        if tag == "form":
            self.forms.append(not self.hidden and not hidden)
        if tag == "input" and values.get("type", "").lower() == "password" and any(self.forms) and not self.hidden:
            self.password_form = True
        if tag in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            return
        self.stack.append((tag, hidden))
        if hidden:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag == "form" and self.forms:
            self.forms.pop()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.hidden -= sum(hidden for _, hidden in self.stack[i:])
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())

    def text(self):
        return "\n".join(self.parts)


def gate(response: Response, body: bytes) -> str | None:
    if response.status == 401:
        return "login_gated"
    if response.status in {403, 451}:
        return "blocked_by_security"
    if response.status == 429:
        return "rate_limited"
    # Look for challenge-specific markup or a challenge/error heading, not arbitrary
    # mentions of CAPTCHA/forbidden inside a substantive contract.
    try:
        sample, _ = html_text(body, response.headers.get("content-type", ""))
    except CaptureStop:
        sample = body.decode("utf-8", errors="replace")
    headings = [re.sub(r"<[^>]*>", " ", h).strip().lower() for h in
                re.findall(r"(?is)<(?:title|h[1-6])[^>]*>(.*?)</(?:title|h[1-6])>", sample)]
    visible = VisibleText(excluded_regions=("footer", "nav", "aside"))
    visible.feed(sample)
    text = visible.text().strip().lower()
    short = len(text) < 300
    security = ("access denied", "request rejected", "request blocked", "verify you are human", "just a moment",
                "الوصول مرفوض", "تم حظر طلبك", "تحقق من أنك إنسان")
    if re.search(r"(?i)(?:cf-chl-|challenge-platform)", sample):
        return "blocked_by_security"
    if any(any(h.startswith(marker) for marker in security) or h in {"forbidden", "403 forbidden"} for h in headings):
        return "blocked_by_security"
    if short and (any(text.startswith(marker) for marker in security) or text in {"forbidden", "403 forbidden"}):
        return "blocked_by_security"
    if short and any(marker in text for marker in ("complete the captcha", "enable javascript and cookies", "confirm you are not a robot")):
        return "blocked_by_security"
    if any(marker in text for marker in ("complete the captcha to continue", "complete the captcha to access", "complete the captcha to view")):
        return "blocked_by_security"
    if len(text) < 20 and re.search(r"(?i)(?:g-recaptcha|hcaptcha)", sample):
        return "blocked_by_security"
    if any(any(marker in h for marker in ("login required", "sign in to continue", "log in to continue", "تسجيل الدخول مطلوب")) for h in headings):
        return "login_gated"
    if visible.password_form:
        return "login_gated"
    if any(h == "paywall" or "subscription required" in h for h in headings):
        return "paywall_gated"
    return None


class PublicCollector:
    def __init__(self, output: Path, decisions: list[AccessRecord], *, transport=http_transport,
                 resolver=socket.getaddrinfo, now=lambda: datetime.now(UTC), sleep=time.sleep,
                 monotonic=time.monotonic, delay=2.0, max_bytes=3 * 1024 * 1024,
                 max_requests=100, max_hops=5, retries=2, max_retry_wait=60.0, timeout=25.0):
        if delay < 2 or not 0 <= retries <= 2 or min(max_bytes, max_requests) <= 0 or max_hops < 0:
            raise ValueError("invalid capture limits")
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        (self.output / "raw").mkdir()
        (self.output / "derived").mkdir()
        self.decisions, self.transport, self.resolver = decisions, transport, resolver
        self.now, self.sleep, self.monotonic = now, sleep, monotonic
        self.delay, self.max_bytes, self.max_requests = delay, max_bytes, max_requests
        self.max_hops, self.retries, self.max_retry_wait, self.timeout = max_hops, retries, max_retry_wait, timeout
        self.request_count = 0
        self.last_request: dict[str, float] = {}
        self.cooldowns: dict[str, tuple[float, str | None]] = {}
        self.paused: dict[str, str] = {}
        self.policy_delays: dict[str, float] = {}
        self.policies: dict[str, tuple[float, Response, bytes]] = {}
        self.manifest = self.output / "manifest.jsonl"
        self.manifest.touch()

    def event(self, record: dict):
        with self.manifest.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"recorded_at": self.now().isoformat(), **record}, ensure_ascii=False) + "\n")

    def artifact(self, body: bytes, suffix: str, directory="raw") -> dict:
        name = digest(body)
        relative = f"{directory}/{name}{suffix}"
        target = self.output / relative
        if target.exists():
            if target.read_bytes() != body:
                raise CaptureStop("artifact_hash_conflict")
        else:
            with target.open("xb") as handle:
                handle.write(body)
        return {"sha256": name, "artifact_path": relative, "bytes": len(body)}

    def decision(self, url: str) -> AccessRecord:
        matched = [r for r in self.decisions if r.current(url, self.now())]
        if not matched:
            raise CaptureStop("access_decision_missing_or_expired")
        if len(matched) != 1:
            raise CaptureStop("access_decision_ambiguous")
        if not matched[0].terms_allowed():
            raise CaptureStop("terms_not_permitted")
        return matched[0]

    def request(self, url: str, purpose: str) -> tuple[Response, bytes]:
        origin(url)
        self.decision(url)
        host = urlsplit(url).hostname.lower()
        safe_headers = {"content-type", "content-encoding", "content-language", "location", "retry-after",
                        "etag", "last-modified", "date", "cf-ray", "x-request-id"}
        for attempt in range(self.retries + 1):
            record = self.decision(url)
            if host in self.paused:
                raise CaptureStop(self.paused[host])
            if self.request_count >= self.max_requests:
                raise CaptureStop("request_budget_exhausted")
            cooldown, next_at = self.cooldowns.get(host, (float("-inf"), None))
            wait = cooldown - self.monotonic()
            if wait > self.max_retry_wait:
                raise CaptureStop("retry_deferred", next_permitted_at=next_at)
            host_delay = max([self.delay, *(d for authority, d in self.policy_delays.items() if urlsplit(authority).hostname == host)])
            remaining = max(wait, host_delay - (self.monotonic() - self.last_request.get(host, float("-inf"))))
            if remaining > 0:
                self.sleep(remaining)
            _public_url(url, self.resolver, self.timeout)
            record = self.decision(url)
            request_id = str(uuid.uuid4())
            self.event({"record_type": "access_decision", "url": url, "purpose": purpose, "request_id": request_id, "capture_id": getattr(self, "capture_id", None), "decision": record.__dict__})
            self.request_count += 1
            self.last_request[host] = self.monotonic()
            audit = {"record_type": "attempt", "url": url, "purpose": purpose,
                     "attempt": attempt + 1, "decision_id": record.decision_id, "request_id": request_id, "capture_id": getattr(self, "capture_id", None)}
            try:
                response = self.transport(url, self.max_bytes, self.timeout)
            except CaptureStop as exc:
                state = "robots_unreachable" if purpose == "robots" and exc.state == "request_timeout" else exc.state
                self.event({**audit, "state": state, **exc.diagnostics})
                if exc.state == "request_timeout" and purpose != "robots" and attempt < self.retries:
                    self.sleep(min(2 ** (attempt + 1), self.max_retry_wait))
                    continue
                raise CaptureStop(state, **exc.diagnostics) from None
            except Exception as exc:
                self.event({**audit, "state": "transport_failed", "error_type": type(exc).__name__})
                if attempt == self.retries or purpose == "robots":
                    raise CaptureStop("robots_unreachable" if purpose == "robots" else "transport_failed") from None
                self.sleep(min(2 ** (attempt + 1), self.max_retry_wait))
                continue
            response = Response(response.status, {k.lower(): v for k, v in response.headers.items()}, response.body, response.connected_address, request_id)
            audit.update(connected_address=response.connected_address, http_status=response.status, content_type=response.headers.get("content-type", ""),
                         headers={k: v for k, v in response.headers.items() if k in safe_headers})
            if len(response.body) > self.max_bytes:
                self.event({**audit, "state": "response_too_large", "bytes_received": len(response.body)})
                raise CaptureStop("response_too_large")
            # Storage errors propagate; they must never cause another network request.
            try:
                raw = self.artifact(response.body, ".bin")
            except OSError as exc:
                self.event({**audit, "state": "output_failed", "error_type": type(exc).__name__})
                raise
            audit.update(raw=raw, **raw)
            try:
                body = decoded_body(response, self.max_bytes)
            except CaptureStop as exc:
                self.event({**audit, "state": exc.state})
                raise
            try:
                audit["decoded"] = self.artifact(body, ".bin", "derived")
            except OSError as exc:
                self.event({**audit, "state": "output_failed", "error_type": type(exc).__name__})
                raise
            self.event(audit)
            security_gate = gate(response, body)
            if security_gate and security_gate != "rate_limited":
                self.paused[host] = security_gate
                return response, body
            if response.status == 429 or response.status >= 500:
                retry_after = response.headers.get("retry-after", "")
                try:
                    wait = float(retry_after) if retry_after else 2 ** (attempt + 1)
                except ValueError:
                    try:
                        wait = max(0, (parsedate_to_datetime(retry_after).astimezone(UTC) - self.now()).total_seconds())
                    except (ValueError, TypeError, OverflowError):
                        wait = 2 ** (attempt + 1)
                if not 0 <= wait < float("inf"):
                    wait = float("inf")
                next_at = (self.now() + timedelta(seconds=wait)).isoformat() if wait < 10 ** 9 else None
                self.cooldowns[host] = (self.monotonic() + wait, next_at)
                self.event({"record_type": "host_cooldown", "host": host, "next_permitted_at": next_at})
                if purpose == "robots":
                    return response, body
                if wait > self.max_retry_wait:
                    raise CaptureStop("retry_deferred", next_permitted_at=next_at)
                if attempt == self.retries:
                    raise CaptureStop("rate_limited" if response.status == 429 else "server_failed", next_permitted_at=next_at)
                continue
            return response, body
        raise CaptureStop("transport_failed")

    def robots(self, url: str) -> tuple[str, Response, bytes]:
        authority = origin(url)
        cached = self.policies.get(authority)
        if cached and self.monotonic() - cached[0] < 86400:
            return self.policy_state(cached[1], cached[2]), cached[1], cached[2]
        target = authority + "/robots.txt"
        for _ in range(self.max_hops + 1):
            response, body = self.request(target, "robots")
            if gate(response, body):
                raise CaptureStop(gate(response, body))
            if response.status in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise CaptureStop("robots_redirect_invalid")
                target = urljoin(target, location)
                continue
            state = self.policy_state(response, body)
            if state in {"robots_valid", "robots_empty", "robots_missing"}:
                self.policies[authority] = (self.monotonic(), response, body)
            return state, response, body
        raise CaptureStop("robots_redirect_limit")

    @staticmethod
    def policy_state(response: Response, body: bytes) -> str:
        refusal = gate(response, body)
        if refusal:
            return refusal
        if response.status >= 500:
            return "robots_unreachable"
        if response.status in {404, 410}:
            return "robots_missing"
        if response.status != 200:
            return "robots_unresolved"
        if "html" in response.headers.get("content-type", "").lower() or re.search(rb"(?i)<(?:html|body|!doctype)", body):
            return "robots_malformed"
        if not body.strip():
            return "robots_empty"
        try:
            text = body.decode("utf-8-sig")
        except UnicodeError:
            return "robots_malformed"
        # A comments-only UTF-8 policy is genuinely empty; HTML/no-directive garbage is not.
        lines = [line.split("#", 1)[0].strip() for line in text.splitlines()]
        if not any(lines):
            return "robots_empty"
        valid_group = any(re.fullmatch(r"(?i)[ \t]*user-agent[ \t]*:[ \t]*(?:\*|[a-z_-]+)[ \t]*(?:#.*)?", line)
                          for line in text.splitlines())
        return "robots_valid" if valid_group else "robots_malformed"

    def check_robots(self, url: str, record: AccessRecord) -> dict:
        state, response, body = self.robots(url)
        policy_hash = digest(body)
        info = {"state": state, "sha256": policy_hash, "http_status": response.status, "policy_request_id": response.request_id, "capture_id": getattr(self, "capture_id", None)}
        self.event({"record_type": "robots_observation", "url": url, "decision_id": record.decision_id, **info})
        if state in {"robots_missing", "robots_empty"}:
            self.policy_delays[origin(url)] = 0
            acknowledgement = record.robots_acknowledgement
            if acknowledgement.get("state") != state or acknowledgement.get("sha256") != policy_hash:
                raise CaptureStop(state + "_unacknowledged")
        elif state == "robots_valid":
            permitted, delay = robots_rules(body, url)
            if not permitted:
                permission = record.source_permission
                if not (all(isinstance(permission.get(k), str) and permission[k].strip() for k in ("issuer", "reference")) and
                        permission.get("robots_exception") is True and permission.get("robots_sha256") == policy_hash):
                    raise CaptureStop("robots_disallowed")
                info["source_permission_reference"] = permission["reference"]
            if delay > self.max_retry_wait:
                raise CaptureStop("crawl_delay_deferred")
            self.policy_delays[origin(url)] = delay
        else:
            raise CaptureStop(state)
        self.event({"record_type": "robots_decision", "url": url, "decision_id": record.decision_id, **info})
        return info

    def capture(self, label: str, url: str, *, extractor=None) -> dict:
        result = {"record_type": "capture", "capture_id": str(uuid.uuid4()), "label": label,
                  "requested_url": url, "captured_at": self.now().isoformat(), "method": "http_fetch",
                  "tool_version": TOOL_VERSION, "redirect_chain": [], "acquisition_complete": False}
        self.capture_id = result["capture_id"]
        try:
            for _ in range(self.max_hops + 1):
                origin(url)
                record = self.decision(url)
                self.event({"record_type": "access_decision", "url": url, "capture_id": result["capture_id"], "decision": record.__dict__})
                policy = self.check_robots(url, record)
                response, body = self.request(url, "content")
                result.update(final_url=url, decision_id=record.decision_id, robots=policy,
                              http_status=response.status, content_type=response.headers.get("content-type", ""),
                              raw=self.artifact(response.body, ".bin"))
                refusal = gate(response, body)
                if refusal:
                    raise CaptureStop(refusal)
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise CaptureStop("redirect_invalid")
                    result["redirect_chain"].append({"url": url, "status": response.status, "location": location})
                    url = urljoin(url, location)
                    continue
                if response.status != 200:
                    raise CaptureStop("http_not_successful")
                if not body:
                    raise CaptureStop("empty_response")
                result["decoded"] = self.artifact(body, ".bin", "derived")
                content_type = result["content_type"].split(";", 1)[0].strip().lower()
                if content_type == "application/pdf" or body.startswith(b"%PDF-"):
                    if not body.startswith(b"%PDF-"):
                        raise CaptureStop("invalid_pdf_signature")
                    result["document_type"] = "pdf"
                    extracted = extract_pdf(body, self.max_bytes)
                    result["extraction_status"] = extracted.pop("status")
                elif content_type in {"text/html", "application/xhtml+xml", "text/plain"}:
                    html, charset = html_text(body, result["content_type"])
                    result["charset"] = charset
                    parser = VisibleText()
                    parser.feed(html)
                    text = parser.text() if content_type != "text/plain" else html
                    if len(text.strip()) < 20:
                        raise CaptureStop("render_needed")
                    extracted = {"text": text, "literal_identity": extractor(html) if extractor else {}}
                    result["extraction_status"] = "visible_text"
                else:
                    raise CaptureStop("unsupported_content_type")
                result["extraction"] = self.artifact(json.dumps(extracted, ensure_ascii=False).encode("utf-8"), ".json", "derived")
                result.update(state="captured", acquisition_complete=True, applicability="unreviewed")
                break
            else:
                raise CaptureStop("redirect_limit")
        except CaptureStop as exc:
            result.update(state=exc.state, **exc.diagnostics)
        except ValueError as exc:
            result.update(state="unsafe_or_invalid_url", error_type=type(exc).__name__)
        except OSError as exc:
            result.update(state="output_failed", error_type=type(exc).__name__)
            raise
        finally:
            result.setdefault("final_url", url)
            self.event(result)
        return result

    def finish(self, captures: list[dict]):
        summary = {"tool_version": TOOL_VERSION, "request_count": self.request_count,
                   "capture_count": len(captures), "states": {state: sum(r["state"] == state for r in captures)
                   for state in sorted({r["state"] for r in captures})}}
        with (self.output / "summary.json").open("x", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)
        return summary
