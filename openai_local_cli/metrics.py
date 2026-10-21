"""Performance telemetry and token-per-second (TPS) metrics calculation."""

from typing import Dict, Any, Optional

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RESET = "\033[0m"


def compute_metrics(
    t_start: float,
    t_first_token: Optional[float],
    t_end: float,
    streamed_token_count: int,
    server_usage: Optional[Dict[str, Any]] = None,
    server_timings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculate latency, generation time, throughput (TPS), and server metrics."""
    if t_first_token is None:
        t_first_token = t_end

    total_time = max(t_end - t_start, 1e-6)
    ttft = max(t_first_token - t_start, 0.0)
    gen_time = max(t_end - t_first_token, 1e-6)

    gen_tokens = streamed_token_count
    prompt_tokens = 0
    if server_usage and isinstance(server_usage, dict):
        gen_tokens = server_usage.get("completion_tokens", streamed_token_count)
        prompt_tokens = server_usage.get("prompt_tokens", 0)

    client_gen_tps = (gen_tokens / gen_time) if gen_time > 0 and gen_tokens > 0 else 0.0

    return {
        "ttft_sec": ttft,
        "gen_time_sec": gen_time,
        "total_time_sec": total_time,
        "gen_tokens": gen_tokens,
        "prompt_tokens": prompt_tokens,
        "client_gen_tps": client_gen_tps,
        "server_usage": server_usage,
        "server_timings": server_timings,
    }


def format_metrics(metrics: Dict[str, Any], use_color: bool = True) -> str:
    """Format metrics dictionary into a readable report string."""
    if not metrics:
        return ""

    bold = BOLD if use_color else ""
    dim = DIM if use_color else ""
    green = GREEN if use_color else ""
    reset = RESET if use_color else ""

    ttft_ms = metrics["ttft_sec"] * 1000.0
    gen_time = metrics["gen_time_sec"]
    total_time = metrics["total_time_sec"]
    gen_tokens = metrics["gen_tokens"]
    prompt_tokens = metrics["prompt_tokens"]
    client_tps = metrics["client_gen_tps"]
    server_timings = metrics.get("server_timings") or {}

    server_gen_tps = server_timings.get("predicted_per_second")
    server_prompt_tps = server_timings.get("prompt_per_second")
    server_draft_accepted = server_timings.get("draft_n_accepted")
    server_draft_total = server_timings.get("draft_n")

    tps_display = f"{green}{client_tps:.2f} t/s{reset}"
    if server_gen_tps is not None:
        tps_display = (
            f"{green}{server_gen_tps:.2f} t/s (server){reset} | "
            f"{dim}wall-clock: {client_tps:.2f} t/s{reset}"
        )

    sep = ("─" * 60) if not use_color else f"{dim}{'─' * 60}{reset}"
    stats_line = (
        f"{bold}Tokens:{reset} {gen_tokens} generated"
        + (f" ({prompt_tokens} prompt)" if prompt_tokens else "")
        + f" | {bold}Speed:{reset} {tps_display}"
    )
    time_line = (
        f"{bold}TTFT:{reset} {ttft_ms:.1f}ms | "
        f"{bold}Gen Time:{reset} {gen_time:.2f}s | "
        f"{bold}Total:{reset} {total_time:.2f}s"
    )
    if server_prompt_tps is not None:
        time_line += f" | {bold}Prompt TPS:{reset} {server_prompt_tps:.1f} t/s"

    if server_draft_total and server_draft_total > 0:
        accept_pct = (server_draft_accepted / server_draft_total) * 100.0
        time_line += f" | {bold}Draft:{reset} {accept_pct:.1f}% ({server_draft_accepted}/{server_draft_total})"

    return f"\n{sep}\n{stats_line}\n{time_line}\n{sep}\n"
