from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from . import __version__
from .models import sha256_text, stable_id
from .registry import LawEntry


class UpstreamUnavailable(RuntimeError):
    pass


class OfficialSourceNotFound(RuntimeError):
    pass


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
    infer historical validity from the current page.
    """

    def __init__(self, timeout_seconds: float = 15.0):
        self.timeout_seconds = timeout_seconds

    async def _fetch(self, url: str) -> str:
        headers = {
            "User-Agent": f"LegalResearchMCP/{__version__} (+read-only legal research)",
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True, headers=headers) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            raise UpstreamUnavailable(f"Official source unavailable: {type(exc).__name__}") from exc
        if response.status_code == 404:
            raise OfficialSourceNotFound("Official source returned HTTP 404")
        if response.status_code >= 500:
            raise UpstreamUnavailable(f"Official source returned HTTP {response.status_code}")
        response.raise_for_status()
        return response.text

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
