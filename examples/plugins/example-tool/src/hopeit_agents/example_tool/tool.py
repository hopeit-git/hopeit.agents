"""Helpers to expose the random number tool as an MCP descriptor."""

from mcp import types


def to_mcp_tool() -> types.Tool:
    """Return an MCP tool descriptor for the random number generator."""
    input_schema = {
        "type": "object",
        "properties": {
            "minimum": {
                "type": "integer",
                "description": "Lower bound (inclusive)",
                "default": 0,
            },
            "maximum": {
                "type": "integer",
                "description": "Upper bound (inclusive)",
                "default": 100,
            },
        },
        "required": [],
    }

    output_schema = {
        "type": "object",
        "properties": {
            "value": {
                "type": "integer",
                "description": "Generated random integer",
            },
        },
        "required": ["value"],
    }

    return types.Tool(
        name="generate-random",
        description="Return a random integer between optional bounds.",
        inputSchema=input_schema,
        outputSchema=output_schema,
        annotations=types.ToolAnnotations(title="Generate Random Number", readOnlyHint=True),
    )
