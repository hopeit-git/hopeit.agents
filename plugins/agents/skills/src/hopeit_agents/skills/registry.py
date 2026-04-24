from hopeit_agents.skills.api import SkillEventInfo

_skills: dict[str, SkillEventInfo] = {}


def register_skill(skill_info: SkillEventInfo) -> None:
    _skills[skill_info.skill_name] = skill_info
    print(_skills)


def list_skills() -> list[SkillEventInfo]:
    return list(_skills.values())


def find_skill(skill_name: str) -> SkillEventInfo | None:
    return _skills.get(skill_name)
