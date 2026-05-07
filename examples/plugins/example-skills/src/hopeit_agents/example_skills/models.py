"""Data objects for the example skills."""

from hopeit.dataobjects import dataclass, dataobject


@dataobject
@dataclass
class MinMaxRange:
    """Specify a minimun and maximun integer"""

    min: int = 0
    max: int = 100


@dataobject
@dataclass
class RandomNumberRequest:
    """Request payload for the random number skill."""

    range: MinMaxRange


@dataobject
@dataclass
class RandomNumberResult:
    """Generated random number result"""

    value: int


@dataobject
@dataclass
class RandomNumberResponse:
    """Skill response containing the generated value."""

    result: RandomNumberResult


@dataobject
@dataclass
class SumTwoNumberRequest:
    """Request payload for the sum two numbers skill."""

    a: int
    b: int


@dataobject
@dataclass
class SumTwoNumberResponse:
    """Response for the sum two numbers skill."""

    result: int
