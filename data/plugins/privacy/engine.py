"""Privacy kit — data portability and the legal-page contract.

Two capabilities a privacy-shaped application needs and should not each
reinvent:

- **Portability.** `portability_bundle()` turns the rows a controller collected
  for one data subject into a single, deterministic JSON document: the subject,
  a timestamp, every section with its record count, and a stable order — what a
  "download my data" request hands back.
- **Legal pages.** `legal_pages()` declares the privacy, terms and cookie pages
  as a contract (slug, route and a `title_key`), never as copy: an application
  or theme renders the text, which is a translation and a legal decision.

The kit carries no user-facing sentence and no personal data of its own; it
only shapes what the caller already collected.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping

#: Version tag of the portability document, so a consumer can branch on it.
PORTABILITY_FORMAT = "craft.privacy.portability/1"


@dataclass(frozen=True, slots=True)
class LegalPage:
    """One legal page: its route and the key of its title."""

    slug: str
    route: str
    title_key: str


#: The legal pages every privacy-shaped application ships. Copy is the
#: application's; this is only the contract.
LEGAL_PAGES = (
    LegalPage("privacy", "/privacy", "legal.privacy.title"),
    LegalPage("terms", "/terms", "legal.terms.title"),
    LegalPage("cookies", "/cookies", "legal.cookies.title"),
)


class Privacy:
    """Stateless privacy helpers. Pure functions of their arguments."""

    @staticmethod
    def portability_bundle(
        subject: str,
        sections: Mapping[str, Iterable[Mapping[str, Any]]],
        generated_at: str | None = None,
    ) -> Dict[str, Any]:
        """Build a subject's portability document from named row sections.

        Args:
            subject: A stable identifier of the data subject.
            sections: Section name to its rows. Rows are copied, never aliased.
            generated_at: ISO 8601 timestamp; the current UTC time when omitted.

        Returns:
            A JSON-serializable document with a stable section order.
        """
        stamp = generated_at or datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        ordered: List[Dict[str, Any]] = []
        total = 0
        for name in sorted(sections):
            records = [dict(row) for row in sections[name]]
            ordered.append({"name": name, "count": len(records), "records": records})
            total += len(records)
        return {
            "format": PORTABILITY_FORMAT,
            "subject": str(subject),
            "generated_at": stamp,
            "total_records": total,
            "sections": ordered,
        }

    @staticmethod
    def legal_pages() -> List[Dict[str, str]]:
        """Return the legal-page contract as plain dictionaries."""
        return [
            {"slug": page.slug, "route": page.route, "title_key": page.title_key}
            for page in LEGAL_PAGES
        ]


__all__ = ["Privacy", "LegalPage", "LEGAL_PAGES", "PORTABILITY_FORMAT"]
