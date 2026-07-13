# Removed Legacy Projects

The migration removed the following superseded projects after the active example stopped using
them:

- `plugins/agents/agent-toolkit`
- `plugins/agents/model-client`
- `plugins/agents/skills`
- `plugins/mcp/mcp-client`
- `plugins/mcp/mcp-server`
- `examples/plugins/example-tool`
- `examples/plugins/example-skills`
- `docker/mcp`

New applications should use `hopeit.engine` for API and application execution, Pydantic AI for
agent runs and tools, and `hopeit-agents` for shared Hopeit-specific integration.
