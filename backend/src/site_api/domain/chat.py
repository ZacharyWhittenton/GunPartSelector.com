from dataclasses import dataclass
from typing import Literal

ChatRole = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class ChatTurn:
    role: ChatRole
    content: str


class ChatNotConfiguredError(Exception):
    """Raised when the assistant is used before an Anthropic API key is configured."""
