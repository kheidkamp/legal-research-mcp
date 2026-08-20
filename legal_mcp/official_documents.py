from __future__ import annotations

import io
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from . import __version__
from .models import sha256_text


class UnsafeOfficialDocumentUrl(ValueError):
    pass


class OfficialDocumentNotFound(RuntimeError):
    pass


class OfficialDocumentUnavailable(RuntimeError):
    pass


class OfficialDocumentTooLarge(RuntimeError):
    pass


class UnsupportedOfficialDocument(RuntimeError):
    pass


OFFICIAL_HOSTS = {
    "dserver.bundestag.de",
    "dip.bundestag.de",
    "www.bundestag.de",
    "bundestag.de",
    "www.bundesrat.de",
    "bundesrat.de",
    "www.recht.bund.de",
    "recht.bund.de",
    "www.gesetze-im-internet.de",
    "gesetze-im-internet.de",
    "www.bundesfinanzministerium.de",
    "bundesfinanzministerium.de",
}


@dataclass(frozen=True)
class ParsedOfficialDocument:
    final_url: str
    media_type: str
    title: str
    pages: list[str]
    content_hash: str

    @property
    def page_count(self) -> int:
        return len(self.pages)


class OfficialDocumentAdapter:
    """Open read-only official German legal documents from a strict host allowlist.

    The adapter is intentionally URL constrained to reduce SSRF risk. Redirects are
    followed manually and every hop is revalidated against the allowlist.
    """

    def __init__(self, timeout_seconds: float = 20.0, max_bytes: int = 20 * 1024 * 1024):
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    @staticmethod
    def validate_official_url(url: str) -> str:
        candidate = (url or "").strip()
        parsed = urlparse(candidate)
        if parsed.scheme.lower() != "https":
            raise UnsafeOfficialDocumentUrl("Only HTTPS official-document URLs are allowed.")
        host = (parsed.hostname or "").lower().rstrip(".")
        if host not in OFFICIAL_HOSTS:
            raise UnsafeOfficialDocumentUrl("URL host is not in the official-document allowlist.")
        if parsed.username or parsed.password:
            raise UnsafeOfficialDocumentUrl("Credentials in URLs are not allowed.")
        if parsed.port not in (None, 443):
            raise UnsafeOfficialDocumentUrl("Non-standard HTTPS ports are not allowed.")
        return candidate

    @staticmethod
    def resolve_document_id(document_id: str) -> str:
        """Resolve a small set of stable official document identifiers to canonical URLs."""
        value = re.sub(r"\s+", " ", (document_id or "").strip())
        if not value:
            raise ValueError("document_id must not be empty")

        br = re.search(
            r"(?i)(?:\bBR\b|BR[- ]?Drs\.?|Bundesrat(?:s)?drucksache)\s*[:.]?\s*(\d{1,4})\s*/\s*(\d{2,4})",
            value,
        )
        if br:
            number = int(br.group(1))
            raw_year = br.group(2)
            year = int(raw_year)
            if len(raw_year) == 2:
                year += 2000
            if year < 2000 or year > 2099:
                raise ValueError("Bundesrat document year is outside the supported range 2000-2099")
            return f"https://dserver.bundestag.de/brd/{year}/{number:04d}-{year % 100:02d}.pdf"

        bt = re.search(
            r"(?i)(?:\bBT\b|BT[- ]?Drs\.?|Bundestagsdrucksache)\s*[:.]?\s*(\d{1,2})\s*/\s*(\d{1,5})",
            value,
        )
        if bt:
            legislature = int(bt.group(1))
            number = int(bt.group(2))
            padded = f"{number:05d}"
            directory = padded[:3]
            return f"https://dserver.bundestag.de/btd/{legislature:02d}/{directory}/{legislature:02d}{padded}.pdf"

        bgbl = re.search(
            r"(?i)BGBl\.?\s*(\d{4})\s*I\s*(?:Nr\.?\s*)?(\d+)",
            value,
        )
        if bgbl:
            year = int(bgbl.group(1))
            number = int(bgbl.group(2))
            return f"https://www.recht.bund.de/bgbl/1/{year}/{number}/VO.html"

        raise ValueError("Unsupported document_id. Use an official HTTPS URL, BR-Drs. n/yy, BT-Drs. wp/n, or BGBl. yyyy I Nr. n.")

    async def _fetch_bytes(self, url: str) -> tuple[bytes, str, str]:
        current = self.validate_official_url(url)
        headers = {
            "User-Agent": f"LegalResearchMCP/{__version__} (+read-only official document retrieval)",
            "Accept": "application/pdf,text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
        }
        timeout = httpx.Timeout(self.timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers=headers) as client:
                for _ in range(6):
                    async with client.stream("GET", current) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                raise OfficialDocumentUnavailable("Official source returned a redirect without Location header.")
                            current = self.validate_official_url(urljoin(current, location))
                            continue
                        if response.status_code == 404:
                            raise OfficialDocumentNotFound("Official document returned HTTP 404.")
                        if response.status_code >= 500:
                            raise OfficialDocumentUnavailable(f"Official document returned HTTP {response.status_code}.")
                        response.raise_for_status()

                        content_length = response.headers.get("content-length")
                        if content_length and content_length.isdigit() and int(content_length) > self.max_bytes:
                            raise OfficialDocumentTooLarge("Official document exceeds the configured download size limit.")

                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > self.max_bytes:
                                raise OfficialDocumentTooLarge("Official document exceeds the configured download size limit.")

                        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                        return bytes(data), media_type, str(response.url)
                raise OfficialDocumentUnavailable("Official source exceeded the redirect limit.")
        except (OfficialDocumentNotFound, OfficialDocumentUnavailable, OfficialDocumentTooLarge, UnsafeOfficialDocumentUrl):
            raise
        except httpx.HTTPError as exc:
            raise OfficialDocumentUnavailable(f"Official source unavailable: {type(exc).__name__}") from exc

    @staticmethod
    def _clean_page_text(text: str) -> str:
        value = (text or "").replace("\x00", "").replace("\u00ad", "")
        # Repair common PDF line-wrap hyphenation before flattening whitespace.
        value = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @staticmethod
    def _visible_html_text(data: bytes) -> tuple[str, str]:
        html = data.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else "Official document"
        for node in soup(["script", "style", "noscript", "svg"]):
            node.decompose()
        root = soup.select_one("main") or soup.select_one("#content") or soup.body or soup
        text = OfficialDocumentAdapter._clean_page_text(root.get_text("\n", strip=True))
        return title, text

    @staticmethod
    def parse_pdf(data: bytes, final_url: str) -> ParsedOfficialDocument:
        try:
            reader = PdfReader(io.BytesIO(data))
        except Exception as exc:
            raise UnsupportedOfficialDocument("PDF could not be parsed.") from exc
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise UnsupportedOfficialDocument("Encrypted PDF cannot be read.") from exc

        pages: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages.append(OfficialDocumentAdapter._clean_page_text(text))
        if not any(pages):
            raise UnsupportedOfficialDocument("PDF contains no extractable text layer.")

        title = None
        try:
            title = getattr(reader.metadata, "title", None)
        except Exception:
            title = None
        if not title:
            title = final_url.rsplit("/", 1)[-1] or "Official PDF"
        joined = "\n\f\n".join(pages)
        return ParsedOfficialDocument(
            final_url=final_url,
            media_type="application/pdf",
            title=str(title),
            pages=pages,
            content_hash=sha256_text(joined),
        )

    @staticmethod
    def parse_html(data: bytes, final_url: str, media_type: str) -> ParsedOfficialDocument:
        title, text = OfficialDocumentAdapter._visible_html_text(data)
        if not text:
            raise UnsupportedOfficialDocument("Official HTML page contains no readable text.")
        return ParsedOfficialDocument(
            final_url=final_url,
            media_type=media_type or "text/html",
            title=title,
            pages=[text],
            content_hash=sha256_text(text),
        )

    async def open_document(self, url: str) -> ParsedOfficialDocument:
        data, media_type, final_url = await self._fetch_bytes(url)
        if media_type == "application/pdf" or data.startswith(b"%PDF-"):
            return self.parse_pdf(data, final_url)
        if media_type in {"text/html", "application/xhtml+xml", "text/plain", ""}:
            return self.parse_html(data, final_url, media_type)
        raise UnsupportedOfficialDocument(f"Unsupported official document media type: {media_type or 'unknown'}")

    @staticmethod
    def _norm(value: str | None) -> str:
        return re.sub(r"\s+", " ", (value or "").replace("\u00ad", "")).strip().casefold()

    @staticmethod
    def _snippet(text: str, start: int, length: int, context_chars: int) -> str:
        left = max(0, start - context_chars // 2)
        right = min(len(text), start + max(length, 1) + context_chars // 2)
        snippet = text[left:right].strip()
        if left > 0:
            snippet = "… " + snippet
        if right < len(text):
            snippet += " …"
        return snippet

    def find_passages(
        self,
        document: ParsedOfficialDocument,
        locator: str | None,
        query: str | None,
        max_passages: int = 3,
        context_chars: int = 1400,
    ) -> tuple[list[dict], bool, bool]:
        max_passages = min(max(int(max_passages), 1), 5)
        context_chars = min(max(int(context_chars), 400), 4000)
        locator_norm = self._norm(locator)
        query_norm = self._norm(query)

        locator_pages: list[int] = []
        if locator_norm:
            for i, page in enumerate(document.pages):
                if locator_norm in self._norm(page):
                    locator_pages.append(i)

        if locator_pages:
            scope: list[int] = []
            seen = set()
            for index in locator_pages:
                for candidate in range(max(0, index - 1), min(len(document.pages), index + 3)):
                    if candidate not in seen:
                        scope.append(candidate)
                        seen.add(candidate)
        else:
            scope = list(range(len(document.pages)))

        matches: list[dict] = []
        query_found = False
        for index in scope:
            page = document.pages[index]
            page_norm = self._norm(page)
            if query_norm:
                pos = page_norm.find(query_norm)
                if pos < 0:
                    continue
                query_found = True
                passage = self._snippet(page, pos, len(query_norm), context_chars)
                matches.append(
                    {
                        "page": index + 1 if document.media_type == "application/pdf" else None,
                        "locator": locator,
                        "query": query,
                        "match_type": "exact_normalized_query",
                        "passage": passage,
                        "passage_hash": sha256_text(passage),
                    }
                )
            elif locator_norm:
                pos = page_norm.find(locator_norm)
                if pos < 0:
                    continue
                passage = self._snippet(page, pos, len(locator_norm), context_chars)
                matches.append(
                    {
                        "page": index + 1 if document.media_type == "application/pdf" else None,
                        "locator": locator,
                        "query": None,
                        "match_type": "exact_normalized_locator",
                        "passage": passage,
                        "passage_hash": sha256_text(passage),
                    }
                )
            else:
                passage = page[:context_chars].strip()
                if passage:
                    matches.append(
                        {
                            "page": index + 1 if document.media_type == "application/pdf" else None,
                            "locator": None,
                            "query": None,
                            "match_type": "document_open",
                            "passage": passage,
                            "passage_hash": sha256_text(passage),
                        }
                    )
            if len(matches) >= max_passages:
                break

        locator_found = bool(locator_pages) if locator_norm else True
        # If the query was not found, return the locator context as non-verifying navigation evidence.
        if query_norm and not matches and locator_pages:
            for index in locator_pages[:max_passages]:
                page = document.pages[index]
                pos = self._norm(page).find(locator_norm)
                passage = self._snippet(page, max(pos, 0), len(locator_norm), context_chars)
                matches.append(
                    {
                        "page": index + 1 if document.media_type == "application/pdf" else None,
                        "locator": locator,
                        "query": query,
                        "match_type": "locator_only_query_not_found",
                        "passage": passage,
                        "passage_hash": sha256_text(passage),
                    }
                )
        return matches, locator_found, query_found if query_norm else bool(matches)
