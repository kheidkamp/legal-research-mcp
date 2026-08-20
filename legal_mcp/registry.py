from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LawEntry:
    abbreviation: str
    title: str
    slug: str
    authority: str = "Bundesministerium der Justiz / Bundesamt fuer Justiz"

    @property
    def landing_url(self) -> str:
        return f"https://www.gesetze-im-internet.de/{self.slug}/"

    def section_url(self, section: str) -> str:
        return f"https://www.gesetze-im-internet.de/{self.slug}/__{section}.html"


# Connectivity MVP: intentionally small, controlled registry.
# Extend only after validating the official canonical path for each law.
LAW_REGISTRY: dict[str, LawEntry] = {
    "KSTG": LawEntry("KStG", "Koerperschaftsteuergesetz", "kstg_1977"),
    "ESTG": LawEntry("EStG", "Einkommensteuergesetz", "estg"),
    "AO": LawEntry("AO", "Abgabenordnung", "ao_1977"),
    "GEWSTG": LawEntry("GewStG", "Gewerbesteuergesetz", "gewstg"),
}


def resolve_law(law: str) -> LawEntry | None:
    normalized = "".join(ch for ch in law.upper().strip() if ch.isalnum())
    return LAW_REGISTRY.get(normalized)
