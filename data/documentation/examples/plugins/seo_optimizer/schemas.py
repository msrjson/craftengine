"""SEO analysis and optimization result DTOs."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class SeoAnalysisResult:
    """SEO audit and optimization metrics."""

    slug: str
    meta_title: str
    meta_description: str
    word_count: int
    readability_score: float
    suggestions: List[str] = field(default_factory=list)
