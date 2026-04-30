from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.server import runtime

from hopeit_agents.skills import registry
from hopeit_agents.skills.api import extract_app_skill_specs

__steps__ = ["init_skills"]


logger, extra = app_extra_logger()


async def init_skills(payload: None, context: EventContext) -> None:
    """
    This method initializes skill files.
    """
    # config = context.settings(key="agent_skills", datatype=SkillsSettings)
    app_engine = runtime.server.app_engines[context.app_key]
    app_config = app_engine.app_config
    # if context.plugin_key:
    #     plugin_engine = runtime.server.app_engines[context.plugin_key]
    #     plugin_config = plugin_engine.app_config
    # else:
    #     plugin_config = None

    specs = extract_app_skill_specs(app_config, plugin=None)
    for spec in specs:
        registry.register_skill(spec)
