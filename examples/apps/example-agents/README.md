# Example Agents

This application combines Hopeit Engine workflows with Pydantic AI agents and typed Python tools.
It does not use MCP or the deprecated agent libraries.

```text
main-agent HTTP request
  -> prepare_agent
  -> plan_expression       (main agent)
  -> call_expert_agent     (Hopeit app_call over HTTP)
       -> expert-agent HTTP workflow
            -> prepare_agent
            -> execute_agent
                 -> generate_random  (tool)
                 -> sum_two_numbers  (tool)
            -> build_response
  -> build_response
```

## Workflows

`agents.main_agent` demonstrates agent-to-agent hand-off through sequential Hopeit steps. Its
`__steps__` list names four functions. Each function receives the previous function's typed output
and returns the input for the next one:

- `prepare_agent` resolves the main agent's model configuration, prompt, and limits.
- `plan_expression` asks the main agent for a typed `ExpressionPlan`.
- `call_expert_agent` sends that expression to the independent expert event with
  `hopeit.app.client.app_call`.
- `build_response` converts the typed result into the public response.

`agents.expert_agent` exposes the specialist independently with its own three-step workflow:
`prepare_agent`, `execute_agent`, and `build_response`. Its `ExpertAgentResults` output is validated
before it crosses the HTTP boundary.

Intermediate workflow objects are Hopeit dataobjects, so the engine can copy and route each step's
payload. The main module never imports or creates the expert agent. The apps client serializes an
`AgentRequest`, invokes the expert event through its configured HTTP route, and deserializes an
`ExpertAgentResponse`.

The former skills agent was removed because it duplicated the main/expert tool-call behavior
without teaching a distinct application pattern.

## Tools

`call_expert_agent` is the explicit agent-to-agent boundary. It uses the Hopeit apps client instead
of importing the expert implementation, so both agents retain independent event workflows.

`generate_random(minimum, maximum)` is registered on the expert agent. Its random-number source
is supplied through request-scoped dependencies, which makes tests deterministic.

`sum_two_numbers(a, b)` is a plain typed Python function registered directly as an expert-agent
tool. Pydantic AI derives both tool schemas from their signatures and docstrings.

## Model configuration

Agent and tool code does not contain provider branches. Both configurations use the shared
`agent_model` setting and `hopeit_agents.agent_model.build_agent_model()`.

Each agent also has independent `request_limit`, `tool_calls_limit`, `tool_retries`, and
`output_retries` settings. Retry budgets are passed to Pydantic AI by category; output retries let
the model correct an invalid structured response without weakening the declared output type.

For OpenAI:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL_NAME="your-openai-model"

uv run --no-sync hopeit_server run \
  --host 127.0.0.1 \
  --port 8020 \
  --config-files examples/apps/example-agents/config/dev-noauth.json,examples/apps/example-agents/config/app-config.json \
  --api-auto "0.1;Hopeit Agents Example API;Cooperating Hopeit Engine and Pydantic AI agents"
```

For a local Ollama server:

```bash
export OLLAMA_MODEL_NAME="your-installed-ollama-model"

uv run --no-sync hopeit_server run \
  --host 127.0.0.1 \
  --port 8020 \
  --config-files examples/apps/example-agents/config/dev-noauth.json,examples/apps/example-agents/config/app-config-ollama.json \
  --api-auto "0.1;Hopeit Agents Example API;Cooperating Hopeit Engine and Pydantic AI agents"
```

The Ollama configuration expects its OpenAI-compatible endpoint at
`http://localhost:11434/v1`. No Ollama API key is required by default.

Both app configurations define the `expert-agent` connection as
`http://127.0.0.1:8020`. Change its `connection_str` when the expert event is deployed on another
Hopeit server. The example uses unsecured HTTP to match `dev-noauth.json`; production deployments
should configure the apps-client authentication and TLS settings appropriately.

OpenAPI documentation is available at `http://127.0.0.1:8020/api/docs`. A main-agent request is:

```bash
curl -X POST \
  "http://127.0.0.1:8020/api/hopeit-agents-example-agents/0x1/agents/main-agent" \
  -H "content-type: application/json" \
  -d '{"user_message":"Add 10 to a random integer between 1 and 20"}'
```

The response contains a conversation ID, deterministic output built from the expert's typed result,
the combined native histories as JSON, and aggregate usage from both agent steps. The expert
endpoint uses the same request shape and returns structured expression results.

## Tests

The default suite uses Pydantic AI test models and never calls OpenAI, Ollama, or the network:

```bash
make lint
make test
```
