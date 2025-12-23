"""Automatic skill matching based on conversation context."""

import re
import logging
from dataclasses import dataclass

import sys
from pathlib import Path

# Add services to path
services_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(services_path))

from skills.models import SkillMetadata, SkillCategory  # noqa: E402

logger = logging.getLogger(__name__)


@dataclass
class SkillMatch:
    """A matched skill with relevance score."""

    skill: SkillMetadata
    score: float
    matched_keywords: list[str]
    match_reason: str


class SkillMatcher:
    """Matches skills to conversation context automatically."""

    # Minimum score to trigger skill injection
    THRESHOLD = 0.3

    # Maximum skills to inject per turn
    MAX_SKILLS = 3

    # Category boost weights (some categories more likely needed)
    CATEGORY_WEIGHTS = {
        SkillCategory.WORKFLOW: 1.2,  # Checklists are often needed
        SkillCategory.ANALYSIS: 1.1,  # Analysis skills useful
        SkillCategory.KNOWLEDGE: 1.0,  # Standard weight
        SkillCategory.CREATION: 1.0,
        SkillCategory.INTEGRATION: 0.9,  # Less common
        SkillCategory.TRAINING: 0.8,  # Very specific
        SkillCategory.PRODUCTIVITY: 1.1,
        SkillCategory.UNCATEGORIZED: 0.7,
    }

    def __init__(self, skills_metadata: list[SkillMetadata]):
        """
        Initialize matcher with skill metadata.

        Args:
            skills_metadata: List of skill metadata for matching
        """
        self.skills = skills_metadata
        self._build_keyword_index()

    def _build_keyword_index(self):
        """Build inverted index of keywords to skills."""
        self.keyword_index: dict[str, list[SkillMetadata]] = {}

        for skill in self.skills:
            for keyword in skill.trigger_keywords:
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = []
                self.keyword_index[keyword].append(skill)

    def match(
        self,
        messages: list[dict],
        context_window: int = 3,
        already_injected: list[str] | None = None,
    ) -> list[SkillMatch]:
        """
        Find skills that match the conversation context.

        Args:
            messages: Conversation history
            context_window: Number of recent messages to analyze
            already_injected: Skill IDs already in this session

        Returns:
            List of matched skills, sorted by relevance
        """
        already_injected = already_injected or []

        # Extract context from recent messages
        recent = (
            messages[-context_window:] if len(messages) > context_window else messages
        )
        context_text = " ".join(
            msg.get("content", "")
            for msg in recent
            if isinstance(msg.get("content"), str)
        ).lower()

        # Find matching skills
        matches: list[SkillMatch] = []

        for skill in self.skills:
            # Skip already injected skills
            if skill.id in already_injected:
                continue

            score, keywords, reason = self._calculate_score(skill, context_text)

            if score >= self.THRESHOLD:
                matches.append(
                    SkillMatch(
                        skill=skill,
                        score=score,
                        matched_keywords=keywords,
                        match_reason=reason,
                    )
                )

        # Sort by score descending, limit to MAX_SKILLS
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[: self.MAX_SKILLS]

    def _calculate_score(
        self,
        skill: SkillMetadata,
        context: str,
    ) -> tuple[float, list[str], str]:
        """Calculate relevance score for a skill."""
        score = 0.0
        matched_keywords = []
        reasons = []

        # 1. Keyword matching (primary signal)
        for keyword in skill.trigger_keywords:
            if keyword in context:
                score += 0.15
                matched_keywords.append(keyword)

        if matched_keywords:
            reasons.append(f"keywords: {', '.join(matched_keywords[:3])}")

        # 2. when_to_use pattern matching
        when_patterns = self._extract_patterns(skill.when_to_use)
        for pattern in when_patterns:
            try:
                if re.search(pattern, context):
                    score += 0.25
                    reasons.append(f"trigger: {pattern[:30]}")
                    break
            except re.error:
                continue

        # 3. Category weight adjustment
        category_weight = self.CATEGORY_WEIGHTS.get(skill.category, 1.0)
        score *= category_weight

        # 4. Tag matching boost
        for tag in skill.tags:
            if tag.lower() in context:
                score += 0.1
                reasons.append(f"tag: {tag}")

        # Cap score at 1.0
        score = min(score, 1.0)

        reason = "; ".join(reasons) if reasons else "no specific match"
        return score, matched_keywords, reason

    def _extract_patterns(self, when_to_use: str) -> list[str]:
        """Extract regex patterns from when_to_use text."""
        patterns = []

        # "when X" patterns
        when_matches = re.findall(r"when\s+([^,\.]+)", when_to_use.lower())
        for match in when_matches:
            # Convert to loose regex
            pattern = re.escape(match.strip())
            pattern = pattern.replace(r"\ ", r"\s+")
            patterns.append(pattern)

        # "for X" patterns
        for_matches = re.findall(r"for\s+([^,\.]+)", when_to_use.lower())
        for match in for_matches:
            pattern = re.escape(match.strip())
            pattern = pattern.replace(r"\ ", r"\s+")
            patterns.append(pattern)

        return patterns[:5]  # Limit patterns
