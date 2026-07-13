# Legacy Project Deprecations

The following projects are retained unchanged for a deprecation period but are no longer used by
the active example or default dependency set:

- `plugins/agents/agent-toolkit`
- `plugins/agents/model-client`
- `plugins/agents/skills`
- `plugins/mcp/mcp-client`
- `plugins/mcp/mcp-server`
- `examples/plugins/example-tool`
- `examples/plugins/example-skills`
- `docker/mcp`

New applications should use `hopeit.engine` for API and application execution, Pydantic AI for
agent runs and tools, and the new `hopeit-agents` project for shared Hopeit-specific integration.

No removal date is set by this migration. Publishing, compatibility support, and eventual source
removal remain separate maintenance decisions.
