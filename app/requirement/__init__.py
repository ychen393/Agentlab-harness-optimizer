"""Natural-language requirement parsing."""

from .parser import RequirementParseError, parse_requirement

__all__ = ["RequirementParseError", "parse_requirement"]
