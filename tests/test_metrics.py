"""Unit tests for metric computation and telemetry formatting."""

import unittest
from openai_local_cli.metrics import compute_metrics, format_metrics


class TestMetrics(unittest.TestCase):
    def test_compute_metrics_basic(self):
        # 100 tokens generated over 2 seconds, TTFT = 0.5s
        t_start = 1000.0
        t_first_token = 1000.5
        t_end = 1002.5

        metrics = compute_metrics(
            t_start=t_start,
            t_first_token=t_first_token,
            t_end=t_end,
            streamed_token_count=100,
            server_usage={"completion_tokens": 100, "prompt_tokens": 25},
        )

        self.assertAlmostEqual(metrics["ttft_sec"], 0.5)
        self.assertAlmostEqual(metrics["gen_time_sec"], 2.0)
        self.assertAlmostEqual(metrics["total_time_sec"], 2.5)
        self.assertEqual(metrics["gen_tokens"], 100)
        self.assertEqual(metrics["prompt_tokens"], 25)
        # TPS = 100 tokens / 2.0 sec = 50.0 t/s
        self.assertAlmostEqual(metrics["client_gen_tps"], 50.0)

    def test_compute_metrics_zero_tokens(self):
        metrics = compute_metrics(
            t_start=100.0,
            t_first_token=None,
            t_end=100.2,
            streamed_token_count=0,
        )
        self.assertEqual(metrics["gen_tokens"], 0)
        self.assertEqual(metrics["client_gen_tps"], 0.0)
        self.assertGreaterEqual(metrics["total_time_sec"], 0.0)

    def test_compute_metrics_server_timings(self):
        timings = {
            "predicted_per_second": 45.2,
            "prompt_per_second": 120.0,
            "draft_n": 50,
            "draft_n_accepted": 30,
        }
        metrics = compute_metrics(
            t_start=10.0,
            t_first_token=10.1,
            t_end=11.1,
            streamed_token_count=45,
            server_timings=timings,
        )
        self.assertEqual(metrics["server_timings"]["predicted_per_second"], 45.2)

        formatted = format_metrics(metrics, use_color=False)
        self.assertIn("45.20 t/s (server)", formatted)
        self.assertIn("Prompt TPS: 120.0 t/s", formatted)
        self.assertIn("Draft: 60.0% (30/50)", formatted)


if __name__ == "__main__":
    unittest.main()
