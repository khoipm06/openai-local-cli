"""Unit tests for Server-Sent Events (SSE) parsing."""

import unittest
from openai_local_cli.chat import parse_sse_line


class TestStreamParsing(unittest.TestCase):
    def test_parse_done(self):
        line = "data: [DONE]\n"
        result = parse_sse_line(line)
        self.assertEqual(result, {"_done": True})

    def test_parse_content_chunk(self):
        line = 'data: {"choices":[{"index":0,"delta":{"content":"hello"}}]}\n'
        result = parse_sse_line(line)
        self.assertIsNotNone(result)
        self.assertEqual(result["choices"][0]["delta"]["content"], "hello")

    def test_parse_reasoning_chunk(self):
        line = 'data: {"choices":[{"index":0,"delta":{"reasoning_content":"thinking"}}]}\n'
        result = parse_sse_line(line)
        self.assertIsNotNone(result)
        self.assertEqual(result["choices"][0]["delta"]["reasoning_content"], "thinking")

    def test_parse_empty_or_corrupt(self):
        self.assertIsNone(parse_sse_line("\n"))
        self.assertIsNone(parse_sse_line(": keepalive\n"))
        self.assertIsNone(parse_sse_line("data: not-json\n"))


if __name__ == "__main__":
    unittest.main()
