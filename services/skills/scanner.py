"""Skills directory scanner and parser with category extraction."""

import re
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

from .models import SkillInfo, SkillMetadata, SkillCategory


# Category detection patterns
CATEGORY_PATTERNS = {
    SkillCategory.KNOWLEDGE: [
        r"mental model",
        r"framework",
        r"concept",
        r"theory",
        r"understanding",
        r"principle",
    ],
    SkillCategory.WORKFLOW: [
        r"checklist",
        r"step-by-step",
        r"workflow",
        r"process",
        r"procedure",
        r"automation",
    ],
    SkillCategory.ANALYSIS: [
        r"analyze",
        r"pattern",
        r"data",
        r"research",
        r"investigate",
        r"diagnose",
    ],
    SkillCategory.CREATION: [
        r"create",
        r"write",
        r"generate",
        r"compose",
        r"design",
        r"build",
    ],
    SkillCategory.INTEGRATION: [
        r"api",
        r"integration",
        r"sync",
        r"connect",
        r"external",
        r"service",
    ],
    SkillCategory.TRAINING: [
        r"training",
        r"exercise",
        r"workout",
        r"mobility",
        r"strength",
        r"physical",
    ],
    SkillCategory.PRODUCTIVITY: [
        r"task",
        r"priority",
        r"time",
        r"schedule",
        r"planning",
        r"organize",
    ],
}

# Stop words for keyword extraction
STOP_WORDS = {
    "when",
    "the",
    "a",
    "an",
    "is",
    "are",
    "to",
    "for",
    "of",
    "and",
    "or",
    "in",
    "on",
    "at",
    "by",
    "with",
    "from",
    "as",
    "be",
    "this",
    "that",
    "it",
    "you",
    "your",
    "use",
    "using",
    "used",
    "need",
    "needs",
    "want",
    "wants",
}


def extract_category_from_content(content: str, tags: List[str]) -> SkillCategory:
    """Infer category from skill content and tags."""
    content_lower = content.lower()
    tags_lower = [t.lower() for t in tags]

    # Calculate scores for each category
    scores = {cat: 0 for cat in SkillCategory}

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, content_lower):
                scores[category] += 1
            if any(pattern in tag for tag in tags_lower):
                scores[category] += 2  # Tags are more indicative

    # Return highest scoring category
    best = max(scores.items(), key=lambda x: x[1])
    if best[1] > 0:
        return best[0]
    return SkillCategory.UNCATEGORIZED


def extract_trigger_keywords(when_to_use: str, description: str) -> List[str]:
    """Extract keywords that trigger this skill."""
    text = f"{when_to_use} {description}".lower()

    # Extract significant words (4+ chars, not stop words)
    words = re.findall(r"\b[a-z]{4,}\b", text)
    keywords = [w for w in words if w not in STOP_WORDS]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return unique[:20]  # Limit to top 20 keywords


class SkillScanner:
    """
    Scans multiple skill roots and parses SKILL.md files.

    Supports:
    - User skills (~/.claude/skills/)
    - Vault skills (vault/.claude/agents/)
    - Custom skill roots
    """

    SKILL_FILENAME = "SKILL.md"

    def __init__(self, skill_roots: Optional[List[str]] = None):
        """
        Initialize scanner with skill roots.

        Args:
            skill_roots: List of paths to scan for skills.
                        Defaults to ~/.claude/skills/
        """
        self.logger = logging.getLogger(__name__)

        if skill_roots is None:
            skill_roots = [os.path.expanduser("~/.claude/skills")]

        self.skill_roots = []
        for root in skill_roots:
            expanded = os.path.expanduser(root)
            if os.path.exists(expanded):
                self.skill_roots.append(Path(expanded))
            else:
                self.logger.warning(f"Skill root not found: {root}")

    def scan_all(self, include_content: bool = False) -> List[SkillInfo]:
        """
        Scan all skill roots and return all skills.

        Args:
            include_content: Whether to include full SKILL.md content

        Returns:
            List of SkillInfo objects
        """
        all_skills = []

        for root in self.skill_roots:
            source = self._determine_source(root)
            skills = self._scan_root(root, source, include_content)
            all_skills.extend(skills)

        # Sort by name
        all_skills.sort(key=lambda s: s.name.lower())
        return all_skills

    def scan_metadata(self) -> List[SkillMetadata]:
        """
        Scan all skill roots and return metadata only (no content).

        Returns:
            List of SkillMetadata objects for efficient matching
        """
        skills = self.scan_all(include_content=False)
        return [
            SkillMetadata(
                id=s.id,
                name=s.name,
                description=s.description,
                when_to_use=s.when_to_use,
                category=s.category,
                tags=s.tags,
                version=s.version,
                source=s.source,
                has_checklist=s.has_checklist,
                last_modified=s.last_modified,
                trigger_keywords=s.trigger_keywords,
            )
            for s in skills
        ]

    def get_skill(self, skill_id: str) -> Optional[SkillInfo]:
        """
        Get a specific skill by ID.

        Args:
            skill_id: The skill directory name

        Returns:
            SkillInfo with full content, or None if not found
        """
        for root in self.skill_roots:
            skill_path = root / skill_id / self.SKILL_FILENAME
            if skill_path.exists():
                return self._parse_skill(
                    skill_path.parent, self._determine_source(root), include_content=True
                )
        return None

    def search(self, query: str) -> List[SkillInfo]:
        """
        Search skills by name, description, or when_to_use.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching SkillInfo objects
        """
        query_lower = query.lower()
        all_skills = self.scan_all(include_content=False)

        matches = []
        for skill in all_skills:
            if (
                query_lower in skill.name.lower()
                or query_lower in skill.description.lower()
                or query_lower in skill.when_to_use.lower()
            ):
                matches.append(skill)

        return matches

    def _scan_root(
        self, root: Path, source: str, include_content: bool
    ) -> List[SkillInfo]:
        """Scan a single skill root directory."""
        skills = []

        for item in root.iterdir():
            if not item.is_dir():
                continue
            if item.name.startswith("."):
                continue

            skill_file = item / self.SKILL_FILENAME
            if skill_file.exists():
                skill = self._parse_skill(item, source, include_content)
                if skill:
                    skills.append(skill)

        return skills

    def _parse_skill(
        self, skill_dir: Path, source: str, include_content: bool
    ) -> Optional[SkillInfo]:
        """Parse a SKILL.md file."""
        skill_file = skill_dir / self.SKILL_FILENAME

        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Failed to read {skill_file}: {e}")
            return None

        # Parse YAML frontmatter
        frontmatter = self._parse_frontmatter(content)
        if not frontmatter:
            self.logger.warning(f"No frontmatter in {skill_file}")
            return None

        # Extract required fields
        name = frontmatter.get("name", skill_dir.name)
        description = frontmatter.get("description", "")
        when_to_use = frontmatter.get("when_to_use", "")
        tags = frontmatter.get("tags", [])

        # Check for checklist
        has_checklist = bool(re.search(r"^\s*[-*]\s*\[ \]", content, re.MULTILINE))

        # Get modification time
        try:
            mtime = datetime.fromtimestamp(skill_file.stat().st_mtime)
        except Exception:
            mtime = None

        # Extract category (from frontmatter or infer from content)
        category_str = frontmatter.get("category", "").lower()
        try:
            category = SkillCategory(category_str) if category_str else None
        except ValueError:
            category = None

        if not category:
            category = extract_category_from_content(content, tags)

        # Extract trigger keywords
        trigger_keywords = extract_trigger_keywords(when_to_use, description)

        return SkillInfo(
            id=skill_dir.name,
            name=name,
            description=description,
            when_to_use=when_to_use,
            category=category,
            tags=tags,
            version=frontmatter.get("version"),
            source=source,
            has_checklist=has_checklist,
            last_modified=mtime,
            trigger_keywords=trigger_keywords,
            path=str(skill_dir),
            content=content if include_content else "",
        )

    def _parse_frontmatter(self, content: str) -> Optional[Dict]:
        """Parse YAML frontmatter from content."""
        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            import yaml

            return yaml.safe_load(parts[1]) or {}
        except Exception as e:
            self.logger.error(f"Failed to parse YAML frontmatter: {e}")
            return {}

    def _determine_source(self, root: Path) -> str:
        """Determine the source type of a skill root."""
        root_str = str(root).lower()
        if ".claude/skills" in root_str:
            return "user"
        elif "obsidian" in root_str or "vault" in root_str:
            return "vault"
        else:
            return "system"

    def update_skill(
        self,
        skill_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        when_to_use: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        content: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Optional[SkillInfo]:
        """
        Update a filesystem skill's SKILL.md file.

        Args:
            skill_id: The skill directory name
            name, description, etc.: Fields to update (None = keep existing)

        Returns:
            Updated SkillInfo, or None if skill not found
        """
        # Find the skill
        skill = self.get_skill(skill_id)
        if not skill:
            return None

        skill_file = Path(skill.path) / self.SKILL_FILENAME

        # Build updated frontmatter
        frontmatter = {
            "name": name if name is not None else skill.name,
            "description": description if description is not None else skill.description,
            "when_to_use": when_to_use if when_to_use is not None else skill.when_to_use,
        }

        # Optional fields
        new_version = version if version is not None else skill.version
        if new_version:
            frontmatter["version"] = new_version

        new_category = category if category is not None else skill.category.value
        if new_category and new_category != "uncategorized":
            frontmatter["category"] = new_category

        new_tags = tags if tags is not None else skill.tags
        if new_tags:
            frontmatter["tags"] = new_tags

        # Build new file content
        import yaml
        yaml_content = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

        # Use provided content or existing (without frontmatter)
        new_content = content if content is not None else self._strip_frontmatter(skill.content)

        # Combine frontmatter and content
        full_content = f"---\n{yaml_content}---\n\n{new_content}"

        # Write back to file
        try:
            skill_file.write_text(full_content, encoding="utf-8")
            self.logger.info(f"Updated skill: {skill_id}")
        except Exception as e:
            self.logger.error(f"Failed to update {skill_file}: {e}")
            return None

        # Return updated skill
        return self.get_skill(skill_id)

    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from content."""
        if not content.startswith("---"):
            return content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return content
        return parts[2].strip()

    def get_stats(self) -> Dict:
        """Get statistics about available skills."""
        all_skills = self.scan_all()

        by_source = {}
        by_category = {}
        for skill in all_skills:
            by_source[skill.source] = by_source.get(skill.source, 0) + 1
            by_category[skill.category.value] = (
                by_category.get(skill.category.value, 0) + 1
            )

        with_checklist = sum(1 for s in all_skills if s.has_checklist)

        return {
            "total_skills": len(all_skills),
            "by_source": by_source,
            "by_category": by_category,
            "with_checklist": with_checklist,
            "skill_roots": [str(r) for r in self.skill_roots],
        }
