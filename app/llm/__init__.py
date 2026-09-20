"""Optional provider adapters kept outside the core evaluation pipeline."""

from .openai_compatible import OpenAICompatibleChat

__all__ = ["OpenAICompatibleChat"]
