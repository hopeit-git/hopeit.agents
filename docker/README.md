# Example Agents Container

The default image runs the migrated Hopeit example application on port `8020` with the OpenAI
configuration.

```bash
docker build -f docker/Dockerfile -t hopeit-agents .
docker run --rm -p 8020:8020 \
  -e OPENAI_API_KEY \
  -e OPENAI_MODEL_NAME \
  hopeit-agents
```

To use Ollama, make the Ollama server reachable from the container and override the final config
argument with `examples/apps/example-agents/config/app-config-ollama.json`. Update its base URL for
your Docker networking setup if Ollama is not available at `localhost` inside the container.
