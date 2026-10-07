from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from . import __version__
from .models import sha256_text, stable_id
from .network_security import assert_public_dns_for_url, media_type_allowed, normalized_media_type, validate_https_allowlisted_url
from .registry import LawEntry


class UpstreamUnavailable(RuntimeError):
    pass


class OfficialSourceNotFound(RuntimeError):
    pass


class OfficialSourceTooLarge(UpstreamUnavailable):
    pass


class UnsupportedOfficialSource(UpstreamUnavailable):
    pass


_GII_HOSTS = {"www.gesetze-im-internet.de", "gesetze-im-internet.de"}
_GII_MEDIA_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}


@dataclass
class ParsedNorm:
    title: str
    heading: str
    text: str
    structure: list[str]
    canonical_url: str
    content_hash: str


class GesetzeImInternetAdapter:
    """Read-only adapter for the official 'Gesetze im Internet' service.

    The service provides the current consolidated federal law. This MVP does not
    infer historical validity from the current page. All outbound requests use
    strict HTTPS/host validation, public-DNS checks, bounded redirects, timeouts,
    response-size limits and content-type validation.
    """

    def __init__(
        self,
        timeout_seconds: float = 15.0,
        max_bytes: int = 5 * 1024 * 1024,
        max_redirects: int = 5,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.transport = transport

    @staticmethod
    def _validate_url(url: str) -> str:
        return validate_https_allowlisted_url(
            url,
            _GII_HOSTS,
            error_cls=UpstreamUnavailable,
            label="Gesetze-im-Internet",
        )

    async def _fetch(self, url: str) -> str:
        headers = {
            "User-Agent": f"LegalResearchMCP/{__version__} (+read-only legal research)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
        }
        current = self._validate_url(url)
        timeout = httpx.Timeout(self.timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers=headers, transport=self.transport) as client:
                for _ in range(self.max_redirects + 1):
                    assert_public_dns_for_url(
                        current,
                        error_cls=UpstreamUnavailable,
                        label="Gesetze-im-Internet",
                    )
                    async with client.stream("GET", current) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                raise UpstreamUnavailable("Official source returned a redirect without Location header.")
                            current = self._validate_url(urljoin(current, location))
                            continue
                        if response.status_code == 404:
                            raise OfficialSourceNotFound("Official source returned HTTP 404")
                        if response.status_code >= 500:
                            raise UpstreamUnavailable(f"Official source returned HTTP {response.status_code}")
                        response.raise_for_status()

                        content_length = response.headers.get("content-length")
                        if content_length and content_length.isdigit() and int(content_length) > self.max_bytes:
                            raise OfficialSourceTooLarge("Official source exceeds the configured response-size limit.")

                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > self.max_bytes:
                                raise OfficialSourceTooLarge("Official source exceeds the configured response-size limit.")

                        media_type = normalized_media_type(response.headers.get("content-type"))
                        if not media_type_allowed(media_type, _GII_MEDIA_TYPES):
                            raise UnsupportedOfficialSource(
                                f"Official source returned unsupported media type: {media_type or 'unknown'}"
                            )
                        self._validate_url(str(response.url))
                        encoding = response.encoding or "utf-8"
                        return bytes(data).decode(encoding, errors="replace")
                raise UpstreamUnavailable("Official source exceeded the redirect limit.")
        except (OfficialSourceNotFound, UpstreamUnavailable):
            raise
        except httpx.HTTPError as exc:
            raise UpstreamUnavailable(f"Official source unavailable: {type(exc).__name__}") from exc

    @staticmethod
    def _visible_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup(["script", "style", "noscript", "svg"]):
            node.decompose()
        root = soup.select_one("main") or soup.select_one("#content") or soup.body or soup
        lines = []
        for raw in root.get_text("\n", strip=True).splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if line and (not lines or lines[-1] != line):
                lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def parse_norm_html(html: str, entry: LawEntry, section: str) -> ParsedNorm:
        visible = GesetzeImInternetAdapter._visible_text(html)
        marker = re.compile(rf"^§\s*{re.escape(section)}(?:\s|$)", re.IGNORECASE)
        lines = visible.splitlines()

        start = None
        for i, line in enumerate(lines):
            if marker.search(line):
                start = i
                break
        if start is None:
            # Individual norm pages may render the section heading together with the law title.
            for i, line in enumerate(lines):
                if f"§ {section}" in line or f"§{section}" in line:
                    start = i
                    break
        if start is None:
            raise OfficialSourceNotFound(f"Section {section} heading not found in official page")

        selected: list[str] = []
        for line in lines[start:]:
            if selected and line.lower() in {"fußnote", "fussnote"}:
                break
            if selected and line == "Nichtamtliches Inhaltsverzeichnis":
                break
            selected.append(line)

        text = "\n".join(selected).strip()
        if not text:
            raise OfficialSourceNotFound("Official section text was empty")

        structure: list[str] = []
        for match in re.finditer(r"(?:^|\n)\((\d+[a-z]?)\)", text, flags=re.IGNORECASE):
            label = f"Abs. {match.group(1)}"
            if label not in structure:
                structure.append(label)

        heading = selected[0]
        title = f"{entry.title} ({entry.abbreviation})"
        canonical_url = entry.section_url(section)
        return ParsedNorm(
            title=title,
            heading=heading,
            text=text,
            structure=structure,
            canonical_url=canonical_url,
            content_hash=sha256_text(text),
        )

    async def get_current_norm(self, entry: LawEntry, section: str) -> ParsedNorm:
        url = entry.section_url(section)
        html = await self._fetch(url)
        return self.parse_norm_html(html, entry, section)

    async def get_law_landing_text(self, entry: LawEntry) -> tuple[str, str]:
        html = await self._fetch(entry.landing_url)
        text = self._visible_text(html)
        return text, entry.landing_url

    @staticmethod
    def extract_whole_statute_last_amended(text: str) -> str | None:
        # This is deliberately only a discovery lead, never provision-specific evidence.
        patterns = [
            r"zuletzt geändert durch\s+([^\n]+)",
            r"zuletzt geaendert durch\s+([^\n]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip(" ;")
        return None

    def source_object(self, entry: LawEntry, canonical_url: str, content_hash: str, as_of_date: str, verification_level: str) -> dict:
        source_id = stable_id("src", canonical_url, content_hash)
        return {
            "source_id": source_id,
            "source_type": "legislation",
            "authority": entry.authority,
            "title": f"{entry.title} ({entry.abbreviation})",
            "official_reference": None,
            "document_date": None,
            "canonical_url": canonical_url,
            "as_of_date": as_of_date,
            "verification_level": verification_level,
            "content_hash": content_hash,
        }
