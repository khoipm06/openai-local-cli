---
name: openai-local-cli
description: Interact with OpenAI-compatible local AI endpoints (llama.cpp, vLLM, Ollama) and measure real-time tokens-per-second (TPS) and latency.
license: MIT
---

# OpenAI Local AI Endpoint CLI & TPS Benchmark

Use this skill to interact with OpenAI-compatible inference servers running locally (such as `llama.cpp` server, `vLLM`, or `Ollama`) on `http://localhost:8080/v1` or custom endpoints, with real-time token streaming and precise generation throughput metrics.

## When to Use

- Interacting with locally hosted Large Language Models via OpenAI-compatible REST endpoints.
- Measuring model inference performance:
  - Tokens per second (TPS) for text generation.
  - Time-To-First-Token (TTFT) latency in milliseconds.
  - Prompt evaluation throughput (Prompt TPS).
  - Draft acceptance rate in speculative decoding setups.
- Inspecting model reasoning tokens (`delta.reasoning_content`) separately from final content.

## Commands & Usage

### 1. Interactive Chat Session

Start an interactive multi-turn session with live streaming and auto-detected model:

```bash
./openai-local-cli --url http://localhost:8080/v1
```

### 2. Flags

- `--url <URL>`: API base URL (default: `http://localhost:8080/v1` or `$OPENAI_BASE_URL`).
- `--model <ID>`: Target model ID (auto-detected from `/v1/models` if omitted).
- `--temperature <FLOAT>`: Sampling temperature (default: `0.7`).
- `--no-think`: Suppress display of reasoning / chain-of-thought tokens.
- `--no-color`: Disable ANSI color formatting.

### 3. In-Session Commands

- `/clear`: Reset conversation history.
- `/system <prompt>`: Update system prompt and reset context.
- `/think on|off`: Toggle display of internal reasoning tokens.
- `/model [id]`: Inspect loaded models or switch active model.
- `/history`: Review conversation turns.
- `/exit` or `/quit`: Terminate session.

## Python API Usage

To use programmatically inside custom scripts:

```python
from openai_local_cli import stream_chat, compute_metrics, format_metrics

messages = [{"role": "user", "content": "Hello!"}]
content, reasoning, metrics = stream_chat(
    base_url="http://localhost:8080/v1",
    messages=messages,
    model="LiquidAI/LFM2.5-8B-A1B-GGUF",
)
print(format_metrics(metrics))
```
