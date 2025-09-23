# hopeit.agents
hopeit.engine async GenAI multi-agent framework

## Running the MCP Example Stack

### Setup dev environment
```bash
make install-dev
```

### Launch MCP server with example tools
```bash
uv run --no-sync hopeit_mcp_server run \
  --host 127.0.0.1 \
  --port 8765 \
  --config-files plugins/mcp/mcp-server/config/dev-noauth.json,plugins/mcp/mcp-server/config/plugin-config.json,examples/plugins/example-tool/config/plugin-config.json
```
The MCP server exposes the Model Context Protocol endpoint at `http://127.0.0.1:8765/mcp`.

### Launch MCP client (hopeit app)
```bash
uv run --no-sync hopeit_server run \
  --host 127.0.0.1 \
  --port 8766 \
  --config-files plugins/mcp/mcp-server/config/dev-noauth.json,plugins/mcp/mcp-client/config/plugin-config.json \
  --api-auto "mcp_client;mcp_client;1.0"
```
Once running, the client application provides OpenAPI documentation at `http://localhost:8766/api/docs`.
