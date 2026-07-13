# Example Agents

This Hopeit application demonstrates two Pydantic AI composition patterns without MCP or the
deprecated agent libraries:

```text
HTTP request -> main agent -> solve_expression tool -> expert agent
                                                  -> generate_random tool
                                                  -> sum_two_numbers tool
```

## Agents

`agents.main_agent` is the public orchestration example. It translates a natural-language task
into an integer sum expression and calls one tool, `solve_expression`. That tool runs the expert
agent in the same process and returns its typed result. The delegated run shares the parent's
usage accounting and limits.

`agents.expert_agent` demonstrates a reusable specialist. It is used by the main agent and is
also exposed as a standalone Hopeit event. Its `ExpertAgentResults` output type is validated by
Pydantic AI before it crosses the HTTP boundary.

The former skills agent was removed because it duplicated the main/expert tool-call behavior
without teaching a distinct application pattern.

## Tools

`solve_expression(expression)` is registered only on the main agent. It is an agent-to-agent
delegation tool: there is no HTTP or MCP round trip between the two agents.

`generate_random(minimum, maximum)` is registered on the expert agent. Its random-number source
is supplied through request-scoped dependencies, which makes tests deterministic.

`sum_two_numbers(a, b)` is a plain typed Python function registered directly as an expert-agent
tool. Pydantic AI derives both tool schemas from their signatures and docstrings.

## Model configuration

Agent and tool code does not contain provider branches. Both configurations use the shared
`agent_model` setting and `hopeit_agents.agent_model.build_agent_model()`.

For OpenAI:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL_NAME="your-openai-model"

uv run --no-sync hopeit_server run \
  --host 127.0.0.1 \
  --port 8020 \
  --config-files examples/apps/example-agents/config/dev-noauth.json,examples/apps/example-agents/config/app-config.json
```

For a local Ollama server:

```bash
export OLLAMA_MODEL_NAME="your-installed-ollama-model"

uv run --no-sync hopeit_server run \
  --host 127.0.0.1 \
  --port 8020 \
  --config-files examples/apps/example-agents/config/dev-noauth.json,examples/apps/example-agents/config/app-config-ollama.json
```

The Ollama configuration expects its OpenAI-compatible endpoint at
`http://localhost:11434/v1`. No Ollama API key is required by default.

OpenAPI documentation is available at `http://127.0.0.1:8020/api/docs`. A main-agent request is:

```bash
curl -X POST \
  "http://127.0.0.1:8020/api/hopeit-agents-example-agents/0x1/agents/main-agent" \
  -H "content-type: application/json" \
  -d '{"user_message":"Add 10 to a random integer between 1 and 20"}'
```

The response contains a conversation ID, the main agent's answer, native message history as JSON,
and aggregate usage. The expert endpoint uses the same request shape and returns structured
expression results.

## Tests

The default suite uses Pydantic AI test models and never calls OpenAI, Ollama, or the network:

```bash
make lint
make test
```
