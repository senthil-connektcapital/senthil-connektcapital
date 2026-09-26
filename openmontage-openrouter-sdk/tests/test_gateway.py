"""OpenRouter gateway unit tests (no paid generation)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gateway.openrouter import VideoJob, submit_video


class GatewayTests(unittest.TestCase):
    def test_submit_video_parses_job(self) -> None:
        payload = {
            "id": "abc123",
            "polling_url": "https://openrouter.ai/api/v1/videos/abc123",
            "status": "pending",
        }
        with patch("gateway.openrouter.request", return_value=payload) as mocked:
            job = submit_video(model="google/veo-3.1-lite", prompt="test", duration=4, api_key="sk-or-test")
        self.assertIsInstance(job, VideoJob)
        self.assertEqual(job.id, "abc123")
        self.assertEqual(job.status, "pending")
        mocked.assert_called_once()
        kwargs = mocked.call_args
        self.assertEqual(kwargs.args[0], "/videos")
        self.assertEqual(kwargs.kwargs["payload"]["model"], "google/veo-3.1-lite")


if __name__ == "__main__":
    unittest.main()
