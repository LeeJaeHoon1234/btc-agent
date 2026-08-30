from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.settings import PROJECT_ROOT


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    title: str
    mission: str
    path: str
    content: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "mission": self.mission,
            "path": self.path,
        }


class SkillRegistry:
    def __init__(self, root: Path | None = None):
        self.root = root or (PROJECT_ROOT / "skills")
        self._skills = self._load()

    @staticmethod
    def _section(content: str, heading: str) -> str:
        marker = f"## {heading}"
        if marker not in content:
            return ""
        tail = content.split(marker, 1)[1]
        for next_heading in ["\n## ", "\n# "]:
            if next_heading in tail:
                tail = tail.split(next_heading, 1)[0]
        return " ".join(line.strip(" -*") for line in tail.strip().splitlines() if line.strip())

    def _load(self) -> dict[str, SkillDefinition]:
        skills: dict[str, SkillDefinition] = {}
        if not self.root.exists():
            return skills
        for path in sorted(self.root.glob("*/SKILL.md")):
            content = path.read_text(encoding="utf-8")
            title = next((line[2:].strip() for line in content.splitlines() if line.startswith("# ")), path.parent.name)
            mission = self._section(content, "Mission")
            name = path.parent.name
            skills[name] = SkillDefinition(name, title, mission, str(path.relative_to(PROJECT_ROOT)), content)
        return skills

    def names(self) -> list[str]:
        return list(self._skills)

    def get(self, name: str) -> SkillDefinition:
        return self._skills[name]

    def describe(self) -> list[dict]:
        return [skill.to_dict() for skill in self._skills.values()]

    def prompt_catalog(self) -> str:
        return "\n\n".join(
            f"SKILL={s.name}\nTITLE={s.title}\nMISSION={s.mission}"
            for s in self._skills.values()
        )


skill_registry = SkillRegistry()
