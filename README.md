# openai-local-cli

An interactive command-line interface for OpenAI-compatible local AI endpoints (`llama.cpp`, `vLLM`, `Ollama`, `LocalAI`) with real-time streaming, reasoning display, and precise tokens-per-second (TPS) telemetry.

Also packaged as an [Agent Skill](https://agentskills.io) compatible with `gh skill`.

## Features

- **Real-Time Streaming**: Live streaming of assistant responses via Server-Sent Events (SSE).
- **Reasoning / Chain-of-Thought Support**: Streams and formats `delta.reasoning_content` (thinking tokens) with toggleable styling.
- **Accurate TPS Telemetry**:
  - Time-To-First-Token (TTFT) latency in milliseconds.
  - Generation throughput in tokens per second (server-reported timings and client wall-clock calculation).
  - Prompt processing throughput (Prompt TPS).
  - Draft model acceptance rate in speculative decoding environments.
- **Interactive Multi-Turn REPL**:
  - Full history navigation and line editing via `readline`.
  - In-session slash commands (`/clear`, `/system`, `/think`, `/model`, `/history`, `/help`, `/exit`).
- **Zero Third-Party Dependencies**: Written entirely in pure Python standard library (`urllib.request`, `json`, `readline`, `time`).

## Installation

### From Source

```bash
git clone https://github.com/khoipm06/openai-local-cli.git
cd openai-local-cli
chmod +x openai-local-cli
```

### Via GitHub CLI Agent Skills

```bash
gh skill install khoipm06/openai-local-cli openai-local-cli
```

## Quick Start

```bash
# Launch interactive chat (auto-detects model from http://localhost:8080/v1)
./openai-local-cli

# Target a custom endpoint or model
./openai-local-cli --url http://127.0.0.1:8000/v1 --model my-model --temperature 0.7
```

### Options

```text
Usage: openai-local-cli [options]

Options:
  --url URL             Base URL for the OpenAI-compatible API (default: http://localhost:8080/v1)
  --model MODEL         Model ID to use (auto-detected if omitted)
  --api-key KEY         API key (default: 'local')
  --temperature TEMP    Sampling temperature (default: 0.7)
  --system TEXT         Initial system prompt
  --no-think            Hide chain-of-thought/reasoning tokens
  --no-color            Disable ANSI color styling
```

### In-Session Commands

- `/clear`: Clear conversation turns while keeping system prompt.
- `/system <prompt>`: Update system prompt and reset context.
- `/think [on|off]`: Toggle display of reasoning/thinking tokens.
- `/model [name]`: Switch model or query endpoint for available models.
- `/history`: View active conversation turns.
- `/help`: Display available commands.
- `/exit` or `/quit`: Exit the session.

### Telemetry Output Example

```text
────────────────────────────────────────────────────────────
Tokens: 61 generated (36 prompt) | Speed: 27.08 t/s (server) | wall-clock: 29.78 t/s
TTFT: 234.1ms | Gen Time: 2.05s | Total: 2.28s | Prompt TPS: 68.1 t/s | Draft: 40.2% (47/117)
────────────────────────────────────────────────────────────
```

## License

[MIT](LICENSE)
