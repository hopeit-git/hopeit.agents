# hopeit.agents

Hopeit integration and examples for building agentic HTTP APIs with `hopeit.engine` and
Pydantic AI.

The active example is a single Hopeit application with two cooperating agents:

```text
client -> Hopeit main-agent event -> main agent
                                      -> solve_expression tool
                                         -> expert agent
                                            -> generate_random tool
                                            -> sum_two_numbers tool
```

Agent delegation and tool calls happen in process. The example does not require an MCP server,
custom model client, custom agent loop, or skills registry.

## Active projects

- [`plugins/agents`](plugins/agents) is the `hopeit-agents` Python project. It currently provides
  the shared, configuration-driven OpenAI/Ollama model factory.
- [`examples/apps/example-agents`](examples/apps/example-agents) is the runnable Hopeit example
  and documents both agents, every tool, configuration, commands, and request format.

## Development

Install the default environment and run the active checks:

```bash
make env
make lint
make test
```

The deterministic tests use Pydantic AI test models and do not contact OpenAI, Ollama, or the
network.

For the OpenAI and Ollama launch commands, see the
[`example-agents` README](examples/apps/example-agents/README.md).

## Migration documentation

The custom agent toolkit, model client, skills registry, MCP projects, and their old examples were
removed after the active application migrated. See [`docs/DEPRECATIONS.md`](docs/DEPRECATIONS.md)
for the removed scope and replacement guidance.
