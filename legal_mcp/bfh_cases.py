from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from . import __version__
from .models import sha256_text, stable_id, today_iso
from .official_documents import (
    OfficialDocumentAdapter,
    OfficialDocumentNotFound,
    OfficialDocumentUnavailable,
    ParsedOfficialDocument,
)


class UnsupportedCourt(ValueError):
    pass


class CaseSourceUnavailable(RuntimeError):
    pass


class CaseSourceNotFound(RuntimeError):
    pass


_BFH_HOST = "www.bundesfinanzhof.de"
_BFH_BASE = f"https://{_BFH_HOST}"
_BFH_SEARCH_URL = f"{_BFH_BASE}/de/entscheidungen/entscheidungen-online/"
_BFH_COVERAGE_START = date(2010, 1, 1)

_CASE_NUMBER_RE = re.compile(
    r"^(?P<senate>(?:[IVX]+|GrS))\s+"
    r"(?P<kind>[A-ZÄÖÜ-]+(?:\s*[A-ZÄÖÜ-]+)?)\s+"
    r"(?P<number>\d{1,4})\s*/\s*(?P<year>\d{2,4})$",
    re.IGNORECASE,
)


def normalize_case_number(value: str) -> str:
    compact = re.sub(r"\s+", " ", (value or "").strip())
    match = _CASE_NUMBER_RE.fullmatch(compact)
    if not match:
        raise ValueError("case_number must look like 'VIII R 10/96' or 'I B 102/09'")
    senate = match.group("senate").upper()
    kind = re.sub(r"\s+", " ", match.group("kind").upper())
    number = str(int(match.group("number")))
    raw_year = match.group("year")
    year = raw_year[-2:] if len(raw_year) == 4 else raw_year.zfill(2)
    return f"{senate} {kind} {number}/{year}"


def validate_court(value: str) -> str:
    court = re.sub(r"\s+", " ", (value or "").strip()).upper()
    aliases = {"BFH", "BUNDESFINANZHOF"}
    if court not in aliases:
        raise UnsupportedCourt("Only BFH is supported by the current case-law adapter.")
    return "BFH"


def parse_iso_date_or_blank(value: str) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("decision_date must be ISO YYYY-MM-DD or an empty string") from exc


@dataclass(frozen=True)
class CaseSearchHit:
    court: str
    case_number: str
    decision_date: str | None
    decision_type: str | None
    title: str
    canonical_url: str
    source_id: str


@dataclass(frozen=True)
class RetrievedCase:
    court: str
    case_number: str
    decision_date: str | None
    decision_type: str | None
    title: str
    ecli: str | None
    canonical_url: str
    content_hash: str
    text: str
    passages: list[dict]


class BFHCaseAdapter:
    """Read-only adapter for BFH decisions.

    The official BFH online research explicitly covers V/NV decisions since 2010.
    For a target decision before 2010 this adapter fails closed: it records the
    official online coverage limitation and does not reconstruct case content.
    """

    coverage_start = _BFH_COVERAGE_START
    search_url = _BFH_SEARCH_URL

    def __init__(
        self,
        timeout_seconds: float = 20.0,
        document_adapter: OfficialDocumentAdapter | None = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.document_adapter = document_adapter or OfficialDocumentAdapter()

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "User-Agent": f"LegalResearchMCP/{__version__} (+read-only BFH case retrieval)",
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.5",
        }

    @staticmethod
    def coverage_object(decision_date: date | None) -> dict:
        before_online_coverage = bool(decision_date and decision_date < _BFH_COVERAGE_START)
        return {
            "authority": "Bundesfinanzhof",
            "official_online_coverage_start": _BFH_COVERAGE_START.isoformat(),
            "target_date_before_online_coverage": before_online_coverage,
            "coverage_note": (
                "The BFH online decision research states that V/NV decisions since 2010 are available online. "
                "For decisions before 2010 the BFH directs users to its decision-dispatch service."
            ),
            "coverage_url": _BFH_SEARCH_URL,
        }

    @staticmethod
    def _search_params(case_number: str, decision_date: date | None = None, fulltext_term: str | None = None) -> dict[str, str]:
        params: dict[str, str] = {
            "tx_eossearch_eossearch[searchTerms][aktenzeichen]": case_number,
        }
        if fulltext_term:
            params["tx_eossearch_eossearch[searchTerms][searchTerm]"] = fulltext_term
        if decision_date:
            german = decision_date.strftime("%d.%m.%Y")
            params["tx_eossearch_eossearch[dateRange][start]"] = german
            params["tx_eossearch_eossearch[dateRange][end]"] = german
        return params

    @staticmethod
    def _validate_bfh_url(url: str) -> str:
        candidate = (url or "").strip()
        parsed = urlparse(candidate)
        if parsed.scheme.lower() != "https":
            raise CaseSourceUnavailable("Only HTTPS BFH URLs are allowed.")
        host = (parsed.hostname or "").lower().rstrip(".")
        if host not in {_BFH_HOST, "bundesfinanzhof.de"}:
            raise CaseSourceUnavailable("BFH request URL left the official BFH host allowlist.")
        if parsed.username or parsed.password:
            raise CaseSourceUnavailable("Credentials in BFH URLs are not allowed.")
        if parsed.port not in (None, 443):
            raise CaseSourceUnavailable("Non-standard HTTPS ports are not allowed for BFH retrieval.")
        return candidate

    async def _fetch_html(self, url: str, params: dict[str, str] | None = None) -> tuple[str, str]:
        timeout = httpx.Timeout(self.timeout_seconds)
        current = self._validate_bfh_url(url)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers=self._headers()) as client:
                first = True
                for _ in range(6):
                    response = await client.get(current, params=params if first else None)
                    first = False
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise CaseSourceUnavailable("BFH source returned a redirect without Location header.")
                        current = self._validate_bfh_url(urljoin(current, location))
                        continue
                    if response.status_code == 404:
                        raise CaseSourceNotFound("BFH source returned HTTP 404.")
                    if response.status_code >= 500:
                        raise CaseSourceUnavailable(f"BFH source returned HTTP {response.status_code}.")
                    response.raise_for_status()
                    final_url = self._validate_bfh_url(str(response.url))
                    return response.text, final_url
                raise CaseSourceUnavailable("BFH source exceeded the redirect limit.")
        except (CaseSourceNotFound, CaseSourceUnavailable):
            raise
        except httpx.HTTPError as exc:
            raise CaseSourceUnavailable(f"BFH source unavailable: {type(exc).__name__}") from exc

    @staticmethod
    def parse_search_results(html: str, case_number: str, base_url: str = _BFH_SEARCH_URL) -> list[CaseSearchHit]:
        target = normalize_case_number(case_number)
        target_fold = target.casefold()
        soup = BeautifulSoup(html, "html.parser")
        hits: list[CaseSearchHit] = []
        seen_urls: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href") or ""
            if "/entscheidung/entscheidungen-online/detail/" not in href:
                continue
            container = anchor.find_parent("tr") or anchor.find_parent("article") or anchor.find_parent("li") or anchor.parent
            text = re.sub(r"\s+", " ", container.get_text(" ", strip=True) if container else anchor.get_text(" ", strip=True))
            if target_fold not in text.casefold():
                continue
            url = urljoin(base_url, href)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            date_matches = re.findall(r"(?:vom\s+)?(\d{2}\.\d{2}\.\d{4})", text)
            decision_date = None
            if date_matches:
                # BFH result rows normally contain publication date first and decision date second.
                # Prefer the last date in the row so publication metadata is not mistaken for
                # the decision date.
                try:
                    decision_date = datetime.strptime(date_matches[-1], "%d.%m.%Y").date().isoformat()
                except ValueError:
                    decision_date = None
            dtype_match = re.search(r"\b(Urteil|Beschluss|Gerichtsbescheid)\b", text, re.IGNORECASE)
            decision_type = dtype_match.group(1).capitalize() if dtype_match else None
            title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)) or text
            hits.append(
                CaseSearchHit(
                    court="BFH",
                    case_number=target,
                    decision_date=decision_date,
                    decision_type=decision_type,
                    title=title,
                    canonical_url=url,
                    source_id=stable_id("src", url, target),
                )
            )
        return hits

    async def search_exact_case(self, case_number: str, decision_date: date | None = None) -> list[CaseSearchHit]:
        case_number = normalize_case_number(case_number)
        if decision_date and decision_date < _BFH_COVERAGE_START:
            return []
        html, final_url = await self._fetch_html(self.search_url, params=self._search_params(case_number, decision_date))
        hits = self.parse_search_results(html, case_number, final_url)
        if not hits and decision_date:
            # One controlled fallback: exact case number without date filter.
            html, final_url = await self._fetch_html(self.search_url, params=self._search_params(case_number, None))
            hits = self.parse_search_results(html, case_number, final_url)
        return hits

    @staticmethod
    def _extract_case_metadata(text: str, fallback_date: date | None = None) -> tuple[str | None, str | None, str | None]:
        dtype_match = re.search(r"\b(Urteil|Beschluss|Gerichtsbescheid)\s+vom\b", text, re.IGNORECASE)
        decision_type = dtype_match.group(1).capitalize() if dtype_match else None
        date_match = re.search(r"\bvom\s+(\d{1,2})\.\s*([A-Za-zÄÖÜäöü]+)\s+(\d{4})", text)
        decision_date = fallback_date.isoformat() if fallback_date else None
        if date_match:
            months = {
                "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
                "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
                "oktober": 10, "november": 11, "dezember": 12,
            }
            month = months.get(date_match.group(2).casefold())
            if month:
                try:
                    decision_date = date(int(date_match.group(3)), month, int(date_match.group(1))).isoformat()
                except ValueError:
                    pass
        ecli_match = re.search(r"\bECLI:DE:BFH:[A-Z0-9:.]+\b", text, re.IGNORECASE)
        ecli = ecli_match.group(0).upper() if ecli_match else None
        return decision_type, decision_date, ecli

    @staticmethod
    def _focus_tokens(focus: str) -> list[str]:
        words = re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", focus or "")
        stop = {
            "der", "die", "das", "den", "dem", "des", "und", "oder", "von", "zur", "zum",
            "eine", "einer", "eines", "einem", "einen", "mit", "bei", "für", "aus", "auf",
            "rechtlich", "steuerlich", "frage", "entscheidung", "bfh",
        }
        unique: list[str] = []
        for word in words:
            folded = word.casefold()
            if len(folded) < 4 or folded in stop or folded in unique:
                continue
            unique.append(folded)
        return unique[:12]

    @classmethod
    def select_passages(cls, document: ParsedOfficialDocument, focus: str, max_passages: int = 3) -> list[dict]:
        text = "\n".join(document.pages)
        if not text:
            return []
        tokens = cls._focus_tokens(focus)
        window = 1800
        step = 900
        candidates: list[tuple[int, int, str]] = []
        lower = text.casefold()
        for start in range(0, max(len(text), 1), step):
            snippet = text[start:start + window].strip()
            if not snippet:
                continue
            folded = snippet.casefold()
            score = sum(1 for token in tokens if token in folded)
            if tokens and score == 0:
                continue
            candidates.append((score, start, snippet))
        if not candidates:
            candidates = [(0, 0, text[:window].strip())]
        candidates.sort(key=lambda item: (-item[0], item[1]))

        passages: list[dict] = []
        used_starts: list[int] = []
        for score, start, snippet in candidates:
            if any(abs(start - previous) < step for previous in used_starts):
                continue
            used_starts.append(start)
            passages.append(
                {
                    "locator": "BFH official decision text",
                    "page": None,
                    "passage": snippet,
                    "passage_hash": sha256_text(snippet),
                    "match_type": "focus_token_window" if tokens else "document_open",
                    "focus_token_hits": score,
                }
            )
            if len(passages) >= max_passages:
                break
        return passages

    async def retrieve_case(
        self,
        court: str,
        case_number: str,
        decision_date: date | None,
        focus: str,
    ) -> RetrievedCase | None:
        validate_court(court)
        case_number = normalize_case_number(case_number)
        if decision_date and decision_date < _BFH_COVERAGE_START:
            return None
        hits = await self.search_exact_case(case_number, decision_date)
        if not hits:
            return None
        hit = hits[0]
        try:
            document = await self.document_adapter.open_document(hit.canonical_url)
        except (OfficialDocumentNotFound, OfficialDocumentUnavailable) as exc:
            raise CaseSourceUnavailable(str(exc)) from exc
        decision_type, parsed_date, ecli = self._extract_case_metadata(document.pages[0] if document.pages else "", decision_date)
        return RetrievedCase(
            court="BFH",
            case_number=case_number,
            decision_date=parsed_date or hit.decision_date,
            decision_type=decision_type or hit.decision_type,
            title=document.title or hit.title,
            ecli=ecli,
            canonical_url=document.final_url,
            content_hash=document.content_hash,
            text="\n".join(document.pages),
            passages=self.select_passages(document, focus),
        )

    @staticmethod
    def input_metadata(court: str, case_number: str, decision_date: date | None) -> dict:
        return {
            "court": court,
            "case_number": case_number,
            "decision_date": decision_date.isoformat() if decision_date else None,
            "verification_level": "user_supplied_or_parsed_input",
        }

    @staticmethod
    def blocked_gate(reason_code: str, coverage: dict, retryable: bool = False) -> dict:
        return {
            "gate_version": "1",
            "gate_state": "closed",
            "must_stop_target_case_content": True,
            "target_case_content_allowed": False,
            "target_case_primary_text_verified": False,
            "later_judicial_description_verified": False,
            "reason_code": reason_code,
            "retryable": retryable,
            "allowed_claim_classes": [
                "input_bibliographic_metadata_with_explicit_input_attribution",
                "official_source_coverage_limit",
                "technical_retrieval_status",
            ],
            "forbidden_claim_classes": [
                "target_case_facts",
                "target_case_holding",
                "target_case_reasons",
                "target_case_headnotes",
                "target_case_quotes",
                "target_case_paraphrases",
                "target_case_attributed_legal_propositions",
            ],
            "output_directive": (
                "STOP target-case content generation. Do not describe, reconstruct, paraphrase, summarize, quote, "
                "or attribute any facts, holding, reasons, headnotes, or legal propositions to the target case. "
                "Do not use model memory, search snippets, secondary sources, later cases, or the user prompt to fill the gap."
            ),
            "coverage": coverage,
        }

    @staticmethod
    def open_gate(source_id: str, evidence_ids: list[str]) -> dict:
        return {
            "gate_version": "1",
            "gate_state": "open",
            "must_stop_target_case_content": False,
            "target_case_content_allowed": True,
            "target_case_primary_text_verified": True,
            "later_judicial_description_verified": False,
            "reason_code": "OFFICIAL_TARGET_CASE_OPENED",
            "retryable": False,
            "allowed_claim_classes": [
                "bibliographic_metadata",
                "target_case_facts_supported_by_returned_evidence",
                "target_case_holding_supported_by_returned_evidence",
                "target_case_reasons_supported_by_returned_evidence",
                "target_case_quotes_or_paraphrases_supported_by_returned_evidence",
            ],
            "forbidden_claim_classes": [
                "claims_not_supported_by_returned_target_case_evidence",
            ],
            "source_id": source_id,
            "evidence_ids": evidence_ids,
            "output_directive": "Target-case content may be stated only to the extent supported by the returned official evidence.",
        }
