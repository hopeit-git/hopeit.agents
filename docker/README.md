# hopeit.agents Docker Quickstart

Build the image from the project root:
1. `docker compose build`

Import the catalog definition with the Docker MCP CLI:
1. `docker mcp catalog import docker/mcp/catalogs/custom.yaml`
   - The catalog registers under the alias `hopeit-agents` (from the YAML file).

Enable and run the server shipped with the image:
- `docker mcp server enable hopeit-agents-mcp`
- `docker mcp server ls`
- `docker mcp gateway run`

The server may not appear in GUI lists, but it is active once enabled and available to MCP clients.
