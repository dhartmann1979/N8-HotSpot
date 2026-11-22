"""
Site icons for the link menu: fetch the favicon of a linked website once, check it and
cache it in SQLite (table link_icons). Same logic as in ADN FRN Server and N8-HotSpot.

Only public internet addresses are fetched (no LAN/loopback, also after redirects),
images are size-limited and type-checked; SVG only when it contains nothing active.
"""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import ipaddress
import re
import socket
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, Optional, Tuple
from urllib.parse import urljoin, urlsplit

import sqlite3
import threading

MAX_BYTES = 256 * 1024
CACHE_SECONDS = 30 * 86400
MISS_CACHE_SECONDS = 3600
TIMEOUT = 3.5


def origin_for(url: str) -> Optional[str]:
    try:
        p = urlsplit(str(url))
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
            return None
        default_port = 80 if p.scheme == "http" else 443
        if p.port not in (None, default_port):
            return None
        try:
            host = ipaddress.ip_address(p.hostname).compressed.lower()
        except ValueError:
            if "%" in p.hostname:
                return None
            host = p.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        if not host or len(host) > 253:
            return None
        return f"{p.scheme.lower()}://{f'[{host}]' if ':' in host else host}"
    except (ValueError, UnicodeError):
        return None


def key_for(url: str) -> Optional[str]:
    origin = origin_for(url)
    return hashlib.sha256(origin.encode("utf-8")).hexdigest() if origin else None


def _public_target(url: str) -> bool:
    origin = origin_for(url)
    if not origin:
        return False
    p = urlsplit(origin)
    host = p.hostname or ""
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            port = 443 if p.scheme == "https" else 80
            addresses = {ipaddress.ip_address(row[4][0]) for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
        except (OSError, ValueError):
            return False
    return bool(addresses) and all(ip.is_global for ip in addresses)


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        if self.count > 4 or not _public_target(newurl):
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _get(url: str, accept: str) -> Tuple[Optional[bytes], str]:
    if not _public_target(url):
        return None, "not a public HTTP(S) address"
    opener = urllib.request.build_opener(_SafeRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "N8-dashboard-site-icon/1.0", "Accept": accept})
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return None, "icon exceeds size limit"
            return data, ""
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        return None, str(exc)[:180]


def _image_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"\x00\x00\x01\x00", b"\x00\x00\x02\x00")):
        return "image/x-icon"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if _safe_svg(data):
        return "image/svg+xml"
    return ""


def _safe_svg(data: bytes) -> bool:
    """Accept self-contained SVG icons only; reject active or externally loaded content."""
    if len(data) > MAX_BYTES:
        return False
    try:
        text = data.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        return False
    if not re.search(r"<svg(?:\s|>)", text, re.I) or re.search(
        r"<!DOCTYPE|<!ENTITY|<\s*script\b|<\s*foreignObject\b|\bon[a-z]+\s*=|url\s*\(|@import|xml-stylesheet|(?:href|src)\s*=\s*['\"](?!#)",
        text, re.I,
    ):
        return False
    return True


class _IconLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "link":
            return
        fields = {key.lower(): value or "" for key, value in attrs}
        rel = set(fields.get("rel", "").lower().split())
        href = fields.get("href", "").strip()
        if href and rel.intersection({"icon", "shortcut", "apple-touch-icon", "mask-icon"}):
            self.hrefs.append(("apple-touch-icon" in rel, href))


def _fetch_icon(origin: str) -> Tuple[Optional[bytes], str, str]:
    failures = []
    for path in ("/favicon.ico", "/favicon.png", "/apple-touch-icon.png"):
        data, error = _get(origin + path, "image/avif,image/webp,image/png,image/*,*/*;q=0.5")
        if data:
            content_type = _image_type(data)
            if content_type:
                return data, content_type, ""
            failures.append("server returned an unsupported image format")
        elif error:
            failures.append(error)
    # Many sites keep their icon at a nonstandard path and advertise it in the page head.
    page, error = _get(origin + "/", "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5")
    if page:
        parser = _IconLinks()
        try:
            parser.feed(page.decode("utf-8", "replace"))
        except Exception:
            parser.hrefs = []
        # Prefer the site's normal favicon, then its touch icon; hrefs are resolved relative to the site.
        for _, href in sorted(parser.hrefs, key=lambda row: row[0])[:8]:
            icon_url = urljoin(origin + "/", href)
            data, icon_error = _get(icon_url, "image/avif,image/webp,image/png,image/*,*/*;q=0.5")
            if data:
                content_type = _image_type(data)
                if content_type:
                    return data, content_type, ""
                failures.append("site-advertised icon has an unsupported image format")
            elif icon_error:
                failures.append(icon_error)
    elif error:
        failures.append(error)
    return None, "", failures[-1] if failures else "no site icon found"



SCHEMA = """CREATE TABLE IF NOT EXISTS link_icons (
    url_hash TEXT PRIMARY KEY, origin TEXT NOT NULL, content_type TEXT NOT NULL DEFAULT '',
    data BLOB, fetched_at REAL NOT NULL, error TEXT NOT NULL DEFAULT '')"""


class IconCache:
    """SQLite cache of site icons (thread safe; one short connection per call)."""

    def __init__(self, path):
        self.path = str(path)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.execute(SCHEMA)

    def _conn(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def _row(self, key):
        with self._conn() as c:
            return c.execute("SELECT * FROM link_icons WHERE url_hash=?", (key,)).fetchone()

    def refresh_one(self, url: str, force: bool = False) -> bool:
        origin = origin_for(url)
        if not origin:
            return False
        key = hashlib.sha256(origin.encode("utf-8")).hexdigest()
        cur = self._row(key)
        interval = CACHE_SECONDS if cur and cur["data"] is not None else MISS_CACHE_SECONDS
        if cur and not force and time.time() - float(cur["fetched_at"]) < interval:
            return cur["data"] is not None
        data, content_type, error = _fetch_icon(origin)
        with self._lock, self._conn() as c:
            c.execute("""INSERT INTO link_icons(url_hash,origin,content_type,data,fetched_at,error) VALUES(?,?,?,?,?,?)
                         ON CONFLICT(url_hash) DO UPDATE SET origin=excluded.origin, content_type=excluded.content_type,
                         data=excluded.data, fetched_at=excluded.fetched_at, error=excluded.error""",
                      (key, origin, content_type, data, time.time(), error))
        return data is not None

    def store(self, url: str, data: bytes, content_type: str) -> bool:
        """Put a known icon into the cache (demo data, or an icon uploaded by hand)."""
        origin = origin_for(url)
        if not origin or _image_type(data) != content_type:
            return False
        key = hashlib.sha256(origin.encode("utf-8")).hexdigest()
        with self._lock, self._conn() as c:
            c.execute("""INSERT INTO link_icons(url_hash,origin,content_type,data,fetched_at,error) VALUES(?,?,?,?,?,'')
                         ON CONFLICT(url_hash) DO UPDATE SET content_type=excluded.content_type, data=excluded.data,
                         fetched_at=excluded.fetched_at, error=''""", (key, origin, content_type, data, time.time()))
        return True

    def refresh_many(self, urls: Iterable[str], force: bool = False) -> None:
        unique = {}
        for url in urls:
            origin = origin_for(url)
            if origin:
                unique[origin] = url
        if unique:
            with ThreadPoolExecutor(max_workers=5) as pool:
                list(pool.map(lambda u: self.refresh_one(u, force), unique.values()))
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM link_icons WHERE fetched_at < ?", (time.time() - CACHE_SECONDS,))

    def cached(self, key: str) -> Optional[Dict[str, Any]]:
        r = self._row(key)
        if not r or r["data"] is None:
            return None
        return {"content_type": r["content_type"], "data": bytes(r["data"]), "fetched_at": r["fetched_at"]}

    def status(self, key: str) -> Optional[Dict[str, Any]]:
        r = self._row(key)
        return None if not r else {"ok": r["data"] is not None, "error": r["error"], "fetched_at": r["fetched_at"]}
