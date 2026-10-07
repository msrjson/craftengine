"""Seo — slugification, metadata and a content audit, all server-side.

No method touches a cookie: a slug, a canonical URL, a meta description and a
robots directive are derived from the page itself, not from a visitor.
Suggestions come back as message keys, never as sentences, so the copy lives
with the application's translations.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional

TITLE_MIN = 20
TITLE_MAX = 60
META_DESCRIPTION_MAX = 155
MIN_WORDS = 300

_WORD = re.compile(r"\s+")
_DROP = re.compile(r"[^\w\s-]")
_BREAKS = re.compile(r"[-\s]+")


@dataclass(frozen=True, slots=True)
class SeoAudit:
    """The result of auditing one page's title and body."""

    slug: str
    meta_title: str
    meta_description: str
    word_count: int
    score: float
    suggestions: List[str] = field(default_factory=list)


class Seo:
    """Stateless SEO helpers. Pure functions of their arguments."""

    @staticmethod
    def slugify(text: str) -> str:
        """Turn a title into a lowercase, accent-free, hyphenated slug."""
        folded = unicodedata.normalize("NFKD", str(text or ""))
        ascii_only = folded.encode("ascii", "ignore").decode("utf-8")
        return _BREAKS.sub("-", _DROP.sub("", ascii_only).strip().lower())

    @staticmethod
    def meta_description(body: str, limit: int = META_DESCRIPTION_MAX) -> str:
        """A one-line summary of `body`, trimmed on a word boundary."""
        collapsed = _WORD.sub(" ", str(body or "").strip())
        if len(collapsed) <= limit:
            return collapsed
        cut = collapsed[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
        return f"{cut}…"

    @staticmethod
    def canonical(url: str, base: Optional[str] = None) -> str:
        """The absolute canonical URL for `url`, given an optional site base."""
        value = str(url or "").strip()
        if not value:
            return str(base or "").rstrip("/")
        if value.startswith(("http://", "https://")) or not base:
            return value
        return f"{str(base).rstrip('/')}/{value.lstrip('/')}"

    @staticmethod
    def robots(index: bool = True, follow: bool = True) -> str:
        """A robots directive for a public or private page."""
        return f"{'index' if index else 'noindex'}, {'follow' if follow else 'nofollow'}"

    @staticmethod
    def head(
        title: str,
        body: str,
        url: Optional[str] = None,
        base: Optional[str] = None,
        index: bool = True,
    ) -> Dict[str, str]:
        """The `<head>` metadata for one page, as plain key/value tags."""
        meta: Dict[str, str] = {
            "description": Seo.meta_description(body),
            "robots": Seo.robots(index=index),
            "og:title": str(title or "").strip(),
            "og:description": Seo.meta_description(body),
        }
        if url or base:
            meta["canonical"] = Seo.canonical(url or "", base)
            meta["og:url"] = meta["canonical"]
        return meta

    @staticmethod
    def audit(title: str, body: str) -> SeoAudit:
        """Score a page and list its improvement keys."""
        text_title = str(title or "").strip()
        text_body = str(body or "")
        words = text_body.split()
        word_count = len(words)

        suggestions: List[str] = []
        if len(text_title) < TITLE_MIN:
            suggestions.append("seo.suggestion.title_too_short")
        elif len(text_title) > TITLE_MAX:
            suggestions.append("seo.suggestion.title_too_long")
        if word_count < MIN_WORDS:
            suggestions.append("seo.suggestion.content_thin")

        score = min(100.0, max(0.0, round(60.0 + (word_count / 10.0) - (len(suggestions) * 10.0), 1)))
        return SeoAudit(
            slug=Seo.slugify(text_title),
            meta_title=text_title,
            meta_description=Seo.meta_description(text_body),
            word_count=word_count,
            score=score,
            suggestions=suggestions,
        )


__all__ = ["Seo", "SeoAudit", "TITLE_MIN", "TITLE_MAX", "META_DESCRIPTION_MAX", "MIN_WORDS"]
