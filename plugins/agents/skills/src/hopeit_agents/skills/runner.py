from typing import Any

from hopeit.app.context import EventContext
from hopeit.dataobjects.payload import Payload
from hopeit.server import runtime
from hopeit.server.engine import AppEngine
from hopeit.server.steps import find_datatype_handler

from hopeit_agents.skills.api import SkillEventInfo


async def execute_skill(
    skill_info: SkillEventInfo, payload: dict[str, Any], context: EventContext
) -> dict[str, Any] | list[Any] | set[Any]:
    app_engine: AppEngine = runtime.server.app_engines[skill_info.app_key]
    datatype = find_datatype_handler(
        app_config=app_engine.app_config,
        event_name=skill_info.event_name,
        event_info=skill_info.event_info,
    )
    skill_context = EventContext(
        app_config=app_engine.app_config,
        plugin_config=app_engine.app_config,
        event_name=skill_info.event_name,
        settings=context.settings,
        track_ids=context.track_ids,
        auth_info=context.auth_info,
    )
    result = await app_engine.execute(
        context=skill_context, query_args=None, payload=Payload.from_obj(payload, datatype=datatype)
    )
    return Payload.to_obj(result)
