"""
Centralized logging configuration.

Rule: never log secrets, buyer hidden state, or full LLM prompts at
INFO level or above (see ARCHITECTURE.md security boundaries). Debug-level
logging of prompts is acceptable locally but must never be enabled in
a shared/deployed environment.
"""
import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
