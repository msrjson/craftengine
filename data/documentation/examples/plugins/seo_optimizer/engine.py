"""Pure Python SEO optimization and slugification engine."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
import unicodedata

from .schemas import SeoAnalysisResult


class SeoOptimizerEngine:
    """Provides URL slugification, meta tag generation, and content SEO analysis."""

    @classmethod
    def slugify(cls, text: str) -> str:
        """Convert a title or phrase into a clean URL-friendly slug."""
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
        text = re.sub(r"[^\w\s-]", "", text).strip().lower()
        return re.sub(r"[-\s]+", "-", text)

    @classmethod
    def analyze_content(cls, title: str, body: str) -> SeoAnalysisResult:
        """Analyze text content for SEO quality metrics and suggestions."""
        slug = cls.slugify(title)
        words = body.split() if body else []
        word_count = len(words)

        suggestions = []
        if len(title) < 20:
            suggestions.append("Title is too short; consider expanding for better search visibility.")
        elif len(title) > 60:
            suggestions.append("Title exceeds 60 characters and may be truncated on search engines.")

        if word_count < 300:
            suggestions.append("Content length is below recommended 300 words for deep topic coverage.")

        # Excerpt meta description
        meta_desc = body[:155].strip() + ("..." if len(body) > 155 else "")
        score = min(100.0, max(0.0, round(60.0 + (word_count / 10.0) - (len(suggestions) * 10), 1)))

        return SeoAnalysisResult(
            slug=slug,
            meta_title=title,
            meta_description=meta_desc,
            word_count=word_count,
            readability_score=score,
            suggestions=suggestions,
        )
