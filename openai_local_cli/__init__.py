"""OpenAI-compatible local AI interactive CLI with TPS telemetry."""

__version__ = "0.1.0"
__all__ = ["compute_metrics", "format_metrics", "stream_chat", "fetch_models"]

from openai_local_cli.metrics import compute_metrics, format_metrics
from openai_local_cli.chat import stream_chat, fetch_models
