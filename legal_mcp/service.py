from __future__ import annotations

import re
from datetime import date

from .gesetze_im_internet import GesetzeImInternetAdapter, OfficialSourceNotFound, UpstreamUnavailable
from .official_documents import (
    OfficialDocumentAdapter,
    OfficialDocumentNotFound,
    OfficialDocumentTooLarge,
    OfficialDocumentUnavailable,
    UnsafeOfficialDocumentUrl,
    UnsupportedOfficialDocument,
)
from .models import envelope, now_iso, sha256_text, stable_id, today_iso
from .registry import LAW_REGISTRY, resolve_law


_SECTION_RE = re.compile(r"^(?:§\s*)?(\d+[a-z]?)$", re.IGNORECASE)


def normalize_section(section: str) -> str:
    match = _SECTION_RE.fullmatch(section.strip())
    if not match:
        raise ValueError("section must look like '8b' or '§ 8b'")
    return match.group(1).lower()


def validate_iso_date(value: str) -> str:
    date.fromisoformat(value)
    return value


class LegalResearchService:
    def __init__(
        self,
        adapter: GesetzeImInternetAdapter | None = None,
        document_adapter: OfficialDocumentAdapter | None = None,
    ):
        self.adapter = adapter or GesetzeImInternetAdapter()
        self.document_adapter = document_adapter or OfficialDocumentAdapter()

    async def search_primary_sources(
        self,
        query: str,
        source_types: list[str] | None = None,
        jurisdiction: str = "DE",
        as_of_date: str | None = None,
        max_results: int = 10,
    ) -> dict:
        if jurisdiction.upper() != "DE":
            return envelope("not_found", {"results": []}, ["MVP registry currently supports jurisdiction DE only."])
        if as_of_date:
            validate_iso_date(as_of_date)
        as_of_date = as_of_date or today_iso()
        max_results = min(max(max_results, 1), 20)
        allowed = set(source_types or ["legislation"])
        if "legislation" not in allowed:
            return envelope("not_found", {"results": []}, ["Connectivity MVP currently discovers legislation only."])

        q = query.lower()
        results = []
        section_match = re.search(r"§\s*(\d+[a-z]?)", query, flags=re.IGNORECASE)
        section = section_match.group(1).lower() if section_match else None
        for entry in LAW_REGISTRY.values():
            needles = [entry.abbreviation.lower(), entry.title.lower()]
            if not any(n in q for n in needles):
                continue
            url = entry.section_url(section) if section else entry.landing_url
            title = f"{entry.title} ({entry.abbreviation})" + (f" § {section}" if section else "")
            source_id = stable_id("src", url, title)
            results.append(
                {
                    "source_id": source_id,
                    "source_type": "legislation",
                    "authority": entry.authority,
                    "title": title,
                    "official_reference": None,
                    "document_date": None,
                    "canonical_url": url,
                    "match_summary": "Registry discovery only; open the official source before relying on its content.",
                    "verification_level": "identified",
                }
            )
            if len(results) >= max_results:
                break
        warnings = []
        status = "ok" if results else "not_found"
        if not results:
            warnings.append("No match in the controlled MVP law registry. This is not a negative legal finding.")
        return envelope(status, {"results": results, "as_of_date": as_of_date}, warnings)

    async def get_norm(
        self,
        law: str,
        section: str,
        as_of_date: str | None = None,
        include_structure: bool = True,
        include_application_rules: bool = False,
    ) -> dict:
        entry = resolve_law(law)
        if not entry:
            return envelope("not_found", {"norm": None, "coverage_status": "unknown", "coverage_notes": []}, ["Law is not in the validated MVP registry."])
        try:
            section = normalize_section(section)
            as_of_date = validate_iso_date(as_of_date) if as_of_date else today_iso()
        except ValueError as exc:
            return envelope("error", {"norm": None, "coverage_status": "unknown", "coverage_notes": []}, [str(exc)])

        try:
            parsed = await self.adapter.get_current_norm(entry, section)
        except OfficialSourceNotFound as exc:
            return envelope("not_found", {"norm": None, "coverage_status": "unknown", "coverage_notes": []}, [str(exc)])
        except (UpstreamUnavailable, Exception) as exc:
            if not isinstance(exc, UpstreamUnavailable):
                # Do not leak implementation details.
                exc = UpstreamUnavailable(type(exc).__name__)
            return envelope("unavailable", {"norm": None, "coverage_status": "unknown", "coverage_notes": []}, [str(exc)])

        current_date = today_iso()
        is_current_request = as_of_date == current_date
        coverage_status = "complete" if is_current_request else "partial"
        notes = []
        warnings = []
        if not is_current_request:
            notes.append(
                "The official source retrieved is the current consolidated text. The MVP does not yet prove that this text was valid on the requested historical date."
            )
            warnings.append("Historical-version verification is not implemented in the connectivity MVP.")

        source = self.adapter.source_object(entry, parsed.canonical_url, parsed.content_hash, as_of_date, "full_checked")
        evidence_id = stable_id("ev", source["source_id"], section, parsed.content_hash)
        evidence = {
            "evidence_id": evidence_id,
            "source_id": source["source_id"],
            "locator": f"§ {section}",
            "passage": parsed.text,
            "verification_level": "full_checked",
            "retrieved_at": now_iso(),
            "content_hash": parsed.content_hash,
        }
        norm = {
            "law": entry.abbreviation,
            "section": section,
            "as_of_date": as_of_date,
            "valid_from": None,
            "valid_to": None,
            "text": parsed.text,
            "structure": parsed.structure if include_structure else [],
            "source": source,
            "evidence": [evidence],
            "application_rules": [] if include_application_rules else None,
        }
        return envelope("ok" if coverage_status == "complete" else "partial", {"norm": norm, "coverage_status": coverage_status, "coverage_notes": notes}, warnings)

    async def trace_norm_amendments(
        self,
        law: str,
        section: str,
        from_date: str,
        to_date: str,
        include_non_changes: bool = True,
    ) -> dict:
        entry = resolve_law(law)
        if not entry:
            return envelope("not_found", {"law": law, "section": section, "coverage_status": "unknown"}, ["Law is not in the validated MVP registry."])
        try:
            section = normalize_section(section)
            validate_iso_date(from_date)
            validate_iso_date(to_date)
            if date.fromisoformat(from_date) > date.fromisoformat(to_date):
                raise ValueError("from_date must not be later than to_date")
        except ValueError as exc:
            return envelope("error", {"law": law, "section": section, "coverage_status": "unknown"}, [str(exc)])

        try:
            landing_text, landing_url = await self.adapter.get_law_landing_text(entry)
        except OfficialSourceNotFound as exc:
            return envelope("not_found", {"law": entry.abbreviation, "section": section, "coverage_status": "unknown"}, [str(exc)])
        except (UpstreamUnavailable, Exception) as exc:
            if not isinstance(exc, UpstreamUnavailable):
                exc = UpstreamUnavailable(type(exc).__name__)
            return envelope("unavailable", {"law": entry.abbreviation, "section": section, "coverage_status": "unknown"}, [str(exc)])

        lead = self.adapter.extract_whole_statute_last_amended(landing_text)
        landing_hash = sha256_text(landing_text)
        source = self.adapter.source_object(entry, landing_url, landing_hash, to_date, "opened")

        checked_later_acts = []
        if lead:
            checked_later_acts.append(
                {
                    "kind": "whole_statute_last_amended_lead",
                    "description": lead,
                    "source": source,
                    "provision_specific_effect_verified": False,
                }
            )

        # Contract-safe connectivity behavior: do not pretend the amendment chain is complete.
        data = {
            "law": entry.abbreviation,
            "section": section,
            "coverage_status": "partial" if lead else "unknown",
            "coverage_from": from_date,
            "coverage_to": to_date,
            "verified_amendments": [],
            "checked_later_acts": checked_later_acts if include_non_changes else [],
            "coverage_gaps": [
                "Provision-specific amending articles and promulgation records are not yet resolved by this connectivity MVP."
            ],
            "newest_verified_change": None,
            "latest_verified_amendment": None,
        }
        warnings = [
            "Whole-statute 'last amended by' metadata is only a discovery lead and is not evidence that the requested section was or was not amended.",
            "Do not make a definitive latest-amendment assertion from this result.",
        ]
        return envelope("partial" if lead else "unavailable", data, warnings)

    async def get_official_document_text(
        self,
        url: str | None = None,
        document_id: str | None = None,
        locator: str | None = None,
        query: str | None = None,
        max_passages: int = 3,
        context_chars: int = 1400,
    ) -> dict:
        if bool(url) == bool(document_id):
            return envelope(
                "error",
                {"document": None, "matches": [], "coverage_status": "unknown"},
                ["Provide exactly one of url or document_id."],
            )
        if not locator and not query:
            return envelope(
                "error",
                {"document": None, "matches": [], "coverage_status": "unknown"},
                ["Provide locator and/or query so the retrieval remains targeted."],
            )

        try:
            requested_url = url or self.document_adapter.resolve_document_id(document_id or "")
            requested_url = self.document_adapter.validate_official_url(requested_url)
            parsed = await self.document_adapter.open_document(requested_url)
        except UnsafeOfficialDocumentUrl as exc:
            return envelope(
                "blocked",
                {"document": None, "matches": [], "coverage_status": "unknown"},
                [str(exc)],
            )
        except ValueError as exc:
            return envelope(
                "error",
                {"document": None, "matches": [], "coverage_status": "unknown"},
                [str(exc)],
            )
        except OfficialDocumentNotFound as exc:
            return envelope(
                "not_found",
                {"document": None, "matches": [], "coverage_status": "unknown"},
                [str(exc)],
            )
        except (OfficialDocumentUnavailable, OfficialDocumentTooLarge, UnsupportedOfficialDocument) as exc:
            return envelope(
                "unavailable",
                {"document": None, "matches": [], "coverage_status": "unknown"},
                [str(exc)],
            )
        except Exception as exc:
            return envelope(
                "unavailable",
                {"document": None, "matches": [], "coverage_status": "unknown"},
                [f"Official document retrieval failed: {type(exc).__name__}"],
            )

        matches, locator_found, query_found = self.document_adapter.find_passages(
            parsed,
            locator,
            query,
            max_passages=max_passages,
            context_chars=context_chars,
        )

        if parsed.final_url.startswith("https://dserver.bundestag.de/"):
            authority = "Deutscher Bundestag / Bundesrat (amtlicher Dokumentenserver)"
            source_type = "legislative_document"
        elif "recht.bund.de" in parsed.final_url:
            authority = "Bundesgesetzblatt / recht.bund.de"
            source_type = "promulgation"
        elif "bundesfinanzministerium.de" in parsed.final_url:
            authority = "Bundesministerium der Finanzen"
            source_type = "administrative_guidance"
        elif "gesetze-im-internet.de" in parsed.final_url:
            authority = "Bundesministerium der Justiz / Bundesamt fuer Justiz"
            source_type = "legislation"
        else:
            authority = "Amtliche deutsche Quelle"
            source_type = "official_document"

        target_verified = bool(query_found and (locator_found or not locator)) if query else bool(matches and (locator_found or not locator))
        verification_level = "full_checked" if target_verified else "opened"
        source_id = stable_id("src", parsed.final_url, parsed.content_hash)
        source = {
            "source_id": source_id,
            "source_type": source_type,
            "authority": authority,
            "title": parsed.title,
            "official_reference": document_id,
            "document_date": None,
            "canonical_url": parsed.final_url,
            "as_of_date": today_iso(),
            "verification_level": verification_level,
            "content_hash": parsed.content_hash,
            "media_type": parsed.media_type,
            "page_count": parsed.page_count,
        }

        evidence = []
        for match in matches:
            evidence.append(
                {
                    "evidence_id": stable_id(
                        "ev",
                        source_id,
                        str(match.get("page")),
                        match.get("passage_hash") or "",
                    ),
                    "source_id": source_id,
                    "locator": locator,
                    "page": match.get("page"),
                    "passage": match.get("passage"),
                    "verification_level": "full_checked" if (target_verified and match.get("match_type") == "exact_normalized_query") else "opened",
                    "retrieved_at": now_iso(),
                    "content_hash": match.get("passage_hash"),
                    "match_type": match.get("match_type"),
                }
            )

        coverage_status = "complete" if target_verified else "partial"
        warnings = []
        if locator and not locator_found:
            warnings.append("The requested locator was not found in the opened official document.")
        if query and not query_found:
            warnings.append("The exact normalized query was not found. Any locator-only passage is navigation evidence, not proof of the requested phrase.")

        data = {
            "document": {
                "requested_url": requested_url,
                "document_id": document_id,
                "title": parsed.title,
                "canonical_url": parsed.final_url,
                "media_type": parsed.media_type,
                "page_count": parsed.page_count,
                "content_hash": parsed.content_hash,
                "source": source,
            },
            "locator": locator,
            "query": query,
            "locator_found": locator_found,
            "query_found": query_found,
            "matches": matches,
            "evidence": evidence,
            "coverage_status": coverage_status,
        }
        status = "ok" if coverage_status == "complete" else "partial"
        return envelope(status, data, warnings)

