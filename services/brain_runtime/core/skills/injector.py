"""Progressive skill injection into chat context."""

import logging
import sys
from pathlib import Path
from typing import Optional

# Add services to path
services_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(services_path))

from skills.models import SkillMetadata  # noqa: E402
from skills.scanner import SkillScanner  # noqa: E402

from .matcher import SkillMatcher, SkillMatch  # noqa: E402

logger = logging.getLogger(__name__)


class SkillInjector:
    """
    Handles progressive skill injection into conversations.

    Implements three-level loading:
    - Level 1: Metadata always available for matching
    - Level 2: Instructions loaded when skill triggered
    - Level 3: Resources accessed via tools when needed
    """

    # Default skill roots
    DEFAULT_SKILL_ROOTS = ["~/.claude/skills"]

    def __init__(self, skill_roots: list[str] | None = None):
        """
        Initialize skill injector.

        Args:
            skill_roots: List of paths to scan for skills
        """
        self.skill_roots = skill_roots or self.DEFAULT_SKILL_ROOTS
        self.scanner = SkillScanner(skill_roots=self.skill_roots)
        self._metadata_cache: list[SkillMetadata] | None = None
        self._content_cache: dict[str, str] = {}

    @property
    def metadata(self) -> list[SkillMetadata]:
        """Get Level 1: All skill metadata (cached)."""
        if self._metadata_cache is None:
            self._metadata_cache = self.scanner.scan_metadata()
        return self._metadata_cache

    def get_content(self, skill_id: str) -> Optional[str]:
        """Get Level 2: Skill content (lazy loaded)."""
        if skill_id not in self._content_cache:
            skill = self.scanner.get_skill(skill_id)
            if skill:
                self._content_cache[skill_id] = skill.content
        return self._content_cache.get(skill_id)

    def invalidate_cache(self):
        """Clear caches when skills change."""
        self._metadata_cache = None
        self._content_cache.clear()

    def build_skill_aware_prompt(
        self,
        base_prompt: str,
        messages: list[dict],
        already_injected: list[str] | None = None,
        mode: str = "tools",
    ) -> tuple[str, list[str]]:
        """
        Build system prompt with automatically matched skills.

        Args:
            base_prompt: The base system prompt
            messages: Conversation history
            already_injected: Skill IDs already injected in this session
            mode: Chat mode (quick, tools, agent)

        Returns:
            tuple of (enhanced_prompt, list of injected skill IDs)
        """
        if mode == "quick":
            # Quick mode: no skills
            return base_prompt, []

        # Match skills to conversation
        matcher = SkillMatcher(self.metadata)
        matches = matcher.match(messages, already_injected=already_injected)

        if not matches:
            return base_prompt, []

        # Build skill context section
        skill_section = self._build_skill_section(matches)

        # Inject into prompt
        enhanced = f"{base_prompt}\n\n{skill_section}"
        injected_ids = [m.skill.id for m in matches]

        logger.info(f"Auto-injected {len(injected_ids)} skills: {injected_ids}")

        return enhanced, injected_ids

    def _build_skill_section(self, matches: list[SkillMatch]) -> str:
        """Build the skills section for the system prompt."""
        lines = [
            "# Automatically Matched Skills",
            "",
            "The following skills have been matched to this conversation. "
            "Use them as appropriate frameworks for your response.",
            "",
        ]

        for match in matches:
            content = self.get_content(match.skill.id)
            if content:
                lines.append(f"## {match.skill.name}")
                lines.append(f"*Matched because: {match.match_reason}*")
                lines.append("")
                lines.append(content)
                lines.append("")

        return "\n".join(lines)

    def get_available_skills_summary(self) -> str:
        """
        Get a brief summary of available skills for the LLM.

        This is included at Level 1 so the LLM knows what's available.
        """
        categories: dict[str, list[str]] = {}
        for skill in self.metadata:
            cat = skill.category.value
            if cat not in categories:
                categories[cat] = []
            desc = skill.description[:50] + "..." if len(skill.description) > 50 else skill.description
            categories[cat].append(f"- {skill.name}: {desc}")

        lines = ["# Available Skills (request by name if needed)", ""]
        for cat, skills in sorted(categories.items()):
            lines.append(f"## {cat.title()}")
            lines.extend(skills[:5])  # Limit per category
            if len(skills) > 5:
                lines.append(f"- ... and {len(skills) - 5} more")
            lines.append("")

        return "\n".join(lines)

    def inject_manual_skills(
        self,
        base_prompt: str,
        skill_ids: list[str],
    ) -> str:
        """
        Inject manually selected skills into the prompt.

        Args:
            base_prompt: The base system prompt
            skill_ids: List of skill IDs to inject

        Returns:
            Enhanced prompt with skills injected
        """
        if not skill_ids:
            return base_prompt

        lines = [
            base_prompt,
            "",
            "# Attached Skills",
            "",
            "The following skills have been manually attached to this conversation:",
            "",
        ]

        for skill_id in skill_ids:
            content = self.get_content(skill_id)
            if content:
                # Get skill metadata for name
                skill_meta = next(
                    (s for s in self.metadata if s.id == skill_id), None
                )
                name = skill_meta.name if skill_meta else skill_id
                lines.append(f"## {name}")
                lines.append("")
                lines.append(content)
                lines.append("")
                logger.info(f"Manually injected skill: {name}")

        return "\n".join(lines)
