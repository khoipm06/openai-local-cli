"""Interactive CLI and streaming client for OpenAI-compatible local AI endpoints."""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.error
from typing import List, Dict, Tuple, Optional, Any

from openai_local_cli.metrics import compute_metrics, format_metrics

try:
    import readline  # Terminal input history and line editing
except ImportError:
    pass

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RED = "\033[31m"
RESET = "\033[0m"


def fetch_models(base_url: str, api_key: str = "local") -> List[str]:
    """Fetch available models from the endpoint."""
    url = f"{base_url.rstrip('/')}/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                return [m["id"] for m in data["data"] if "id" in m]
            if "models" in data and isinstance(data["models"], list) and len(data["models"]) > 0:
                return [m.get("name") or m.get("model") for m in data["models"] if m.get("name") or m.get("model")]
    except Exception:
        pass
    return []


def parse_sse_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single SSE data line into a JSON object."""
    trimmed = line.strip()
    if not trimmed or not trimmed.startswith("data: "):
        return None
    data_str = trimmed[6:].strip()
    if data_str == "[DONE]":
        return {"_done": True}
    try:
        return json.loads(data_str)
    except json.JSONDecodeError:
        return None


def stream_chat(
    base_url: str,
    messages: List[Dict[str, str]],
    model: str,
    api_key: str = "local",
    temperature: float = 0.7,
    show_thinking: bool = True,
    stdout_stream=sys.stdout,
) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Stream completion from /v1/chat/completions while printing chunks and recording TPS telemetry.
    Returns: (full_content, full_reasoning, metrics_dict)
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    t_start = time.perf_counter()
    t_first_token: Optional[float] = None
    t_end: Optional[float] = None

    token_count = 0
    full_content: List[str] = []
    full_reasoning: List[str] = []
    server_usage: Optional[Dict[str, Any]] = None
    server_timings: Optional[Dict[str, Any]] = None
    in_reasoning_mode = False
    assistant_header_printed = False

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace")
                chunk = parse_sse_line(line)
                if not chunk:
                    continue
                if chunk.get("_done"):
                    break

                if "usage" in chunk and chunk["usage"]:
                    server_usage = chunk["usage"]
                if "timings" in chunk and chunk["timings"]:
                    server_timings = chunk["timings"]

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                reasoning_chunk = delta.get("reasoning_content")
                content_chunk = delta.get("content")

                if reasoning_chunk:
                    if t_first_token is None:
                        t_first_token = time.perf_counter()
                    token_count += 1
                    full_reasoning.append(reasoning_chunk)

                    if show_thinking:
                        if not in_reasoning_mode:
                            stdout_stream.write(f"\n{DIM}{MAGENTA}[Thinking...]{RESET}\n{DIM}")
                            stdout_stream.flush()
                            in_reasoning_mode = True
                        stdout_stream.write(reasoning_chunk)
                        stdout_stream.flush()

                if content_chunk:
                    if t_first_token is None:
                        t_first_token = time.perf_counter()
                    token_count += 1
                    full_content.append(content_chunk)

                    if in_reasoning_mode:
                        if show_thinking:
                            stdout_stream.write(f"{RESET}\n\n{BOLD}{CYAN}Assistant:{RESET}\n")
                        in_reasoning_mode = False
                        assistant_header_printed = True
                    elif not assistant_header_printed:
                        stdout_stream.write(f"\n{BOLD}{CYAN}Assistant:{RESET}\n")
                        assistant_header_printed = True

                    stdout_stream.write(content_chunk)
                    stdout_stream.flush()

            t_end = time.perf_counter()
            if in_reasoning_mode:
                stdout_stream.write(RESET)
                stdout_stream.flush()

    except urllib.error.URLError as e:
        sys.stderr.write(f"\n{RED}Network/Endpoint error: {e}{RESET}\n")
        return None, None, None
    except KeyboardInterrupt:
        t_end = time.perf_counter()
        stdout_stream.write(f"\n{YELLOW}[Generation interrupted by user]{RESET}\n")

    if t_first_token is None:
        t_first_token = t_end if t_end else time.perf_counter()
    if t_end is None:
        t_end = time.perf_counter()

    metrics = compute_metrics(
        t_start=t_start,
        t_first_token=t_first_token,
        t_end=t_end,
        streamed_token_count=token_count,
        server_usage=server_usage,
        server_timings=server_timings,
    )

    return "".join(full_content), "".join(full_reasoning), metrics


def print_help():
    print(f"""
{BOLD}Interactive Commands:{RESET}
  {CYAN}/help{RESET}          Show this help message
  {CYAN}/clear{RESET}         Clear conversation history (retains system prompt)
  {CYAN}/system <txt>{RESET}  Set a new system prompt and reset conversation
  {CYAN}/think [on|off]{RESET} Toggle or view display of reasoning/thinking tokens
  {CYAN}/model [name]{RESET}   Switch model or query endpoint for available models
  {CYAN}/history{RESET}       Display current conversation messages
  {CYAN}/exit{RESET}, {CYAN}/quit{RESET}    Exit the interactive chat
""")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive OpenAI-compatible CLI with live streaming and TPS telemetry."
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("OPENAI_BASE_URL", "http://localhost:8080/v1"),
        help="Base URL for the OpenAI-compatible API (default: http://localhost:8080/v1)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", None),
        help="Model ID to use (auto-detected if omitted)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY", "local"),
        help="API Key (default: 'local')",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (default: 0.7)",
    )
    parser.add_argument(
        "--system",
        default="You are a helpful, concise AI assistant.",
        help="Initial system prompt",
    )
    parser.add_argument(
        "--no-think",
        action="store_true",
        help="Hide chain-of-thought/reasoning tokens",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors",
    )

    args = parser.parse_args()
    base_url = args.url.rstrip("/")
    show_thinking = not args.no_think
    use_color = not args.no_color and sys.stdout.isatty()

    print(f"{BOLD}{BLUE}============================================================{RESET}")
    print(f"{BOLD}{BLUE}  OpenAI-Compatible Local Endpoint Interactive Chat{RESET}")
    print(f"{BOLD}{BLUE}============================================================{RESET}")
    print(f"Connecting to: {CYAN}{base_url}{RESET}")

    models = fetch_models(base_url, args.api_key)
    current_model = args.model
    if not current_model:
        if models:
            current_model = models[0]
            print(f"Auto-selected model: {GREEN}{current_model}{RESET}")
        else:
            current_model = "default"
            print(f"{YELLOW}Warning: Could not auto-detect model from /models. Using '{current_model}'.{RESET}")
    else:
        print(f"Selected model: {GREEN}{current_model}{RESET}")

    print(f"Temperature: {args.temperature} | Reasoning output: {'enabled' if show_thinking else 'hidden'}")
    print(f"Type {CYAN}/help{RESET} for commands or {CYAN}/exit{RESET} to quit.\n")

    conversation: List[Dict[str, str]] = []
    if args.system:
        conversation.append({"role": "system", "content": args.system})

    while True:
        try:
            user_input = input(f"{BOLD}{GREEN}You > {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{BLUE}Goodbye!{RESET}")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ("/exit", "/quit"):
                print(f"{BLUE}Goodbye!{RESET}")
                break
            elif cmd == "/help":
                print_help()
                continue
            elif cmd == "/clear":
                conversation = [m for m in conversation if m["role"] == "system"]
                print(f"{YELLOW}Conversation history cleared.{RESET}\n")
                continue
            elif cmd == "/system":
                if arg:
                    conversation = [{"role": "system", "content": arg}]
                    print(f"{YELLOW}System prompt updated and conversation reset.{RESET}\n")
                else:
                    curr = next((m["content"] for m in conversation if m["role"] == "system"), "(None)")
                    print(f"Current system prompt: {curr}\n")
                continue
            elif cmd == "/think":
                if arg.lower() in ("on", "true", "1"):
                    show_thinking = True
                    print(f"Reasoning output: {GREEN}enabled{RESET}\n")
                elif arg.lower() in ("off", "false", "0"):
                    show_thinking = False
                    print(f"Reasoning output: {YELLOW}hidden{RESET}\n")
                else:
                    show_thinking = not show_thinking
                    state = f"{GREEN}enabled{RESET}" if show_thinking else f"{YELLOW}hidden{RESET}"
                    print(f"Reasoning output toggled to: {state}\n")
                continue
            elif cmd == "/model":
                if arg:
                    current_model = arg
                    print(f"Active model set to: {GREEN}{current_model}{RESET}\n")
                else:
                    live_models = fetch_models(base_url, args.api_key)
                    print(f"Current model: {GREEN}{current_model}{RESET}")
                    if live_models:
                        print(f"Available models at endpoint: {', '.join(live_models)}\n")
                    else:
                        print(f"No additional models listed by endpoint.\n")
                continue
            elif cmd == "/history":
                print(f"{BOLD}--- Current Conversation ({len(conversation)} messages) ---{RESET}")
                for m in conversation:
                    role_color = YELLOW if m["role"] == "system" else (GREEN if m["role"] == "user" else CYAN)
                    preview = m["content"][:120] + ("..." if len(m["content"]) > 120 else "")
                    print(f"{role_color}{m['role'].capitalize()}:{RESET} {preview}")
                print()
                continue
            else:
                print(f"{RED}Unknown command: {cmd}. Type /help for available commands.{RESET}\n")
                continue

        conversation.append({"role": "user", "content": user_input})

        content, reasoning, metrics = stream_chat(
            base_url=base_url,
            messages=conversation,
            model=current_model,
            api_key=args.api_key,
            temperature=args.temperature,
            show_thinking=show_thinking,
        )

        if content is not None:
            conversation.append({"role": "assistant", "content": content})
            if metrics:
                report = format_metrics(metrics, use_color=use_color)
                sys.stdout.write(report)
                sys.stdout.flush()
        else:
            conversation.pop()
            sys.stdout.write("\n")


if __name__ == "__main__":
    main()
