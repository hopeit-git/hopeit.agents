# hopeit-agents

Shared Hopeit integration for agentic APIs built with `hopeit.engine` and Pydantic AI.

The initial package provides a configuration-driven model factory for OpenAI and an Ollama
server. Application code selects the provider with `AgentModelSettings`; agents and tools remain
provider-independent.

This project intentionally does not provide another agent loop, message hierarchy, tool
registry, or tracing format. Those responsibilities remain with Pydantic AI.
