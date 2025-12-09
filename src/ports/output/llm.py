"""LLM Port - Interface for Language Model adapters."""

from typing import Protocol


class LLMPort(Protocol):
    """Port for Language Model implementations."""

    def invoke(self, inputs) -> object:
        """
        Invoke the language model with given inputs.

        Args:
            inputs: Input to the language model (prompt, messages, etc.)

        Returns:
            Model response object
        """
        ...
