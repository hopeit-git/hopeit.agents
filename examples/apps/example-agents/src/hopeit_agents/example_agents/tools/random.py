"""Random-number operation exposed directly to the expert agent."""

import random
from collections.abc import Callable
from dataclasses import dataclass

from pydantic_ai import RunContext

RandomNumberSource = Callable[[int, int], int]


@dataclass(frozen=True)
class ExpertAgentDeps:
    """Request-scoped dependencies used by expert-agent tools."""

    random_number: RandomNumberSource = random.randint


def random_integer(
    minimum: int = 0,
    maximum: int = 100,
    *,
    source: RandomNumberSource = random.randint,
) -> int:
    """Generate one random integer in an inclusive, normalized range."""
    lower, upper = sorted((minimum, maximum))
    return source(lower, upper)


def generate_random(
    ctx: RunContext[ExpertAgentDeps],
    minimum: int = 0,
    maximum: int = 100,
) -> int:
    """Generate one random integer in the inclusive range."""
    return random_integer(minimum, maximum, source=ctx.deps.random_number)
