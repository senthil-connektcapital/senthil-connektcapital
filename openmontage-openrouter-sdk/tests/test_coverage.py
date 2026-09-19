"""Live OpenRouter catalog vs the OpenMontage capability matrix."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from comparison.catalog import run_comparison
from comparison.report import render_markdown


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_comparison()

    def test_openrouter_lists_a_real_video_catalog(self) -> None:
        self.assertGreaterEqual(self.report.video_model_count, 15)
        joined = " ".join(self.report.video_ids)
        for needle in ("google/veo", "kwaivgi/kling", "bytedance/seedance", "runway/", "minimax/hailuo"):
            self.assertIn(needle, joined)

    def test_heygen_on_openrouter_is_avatar_not_workflow_gateway(self) -> None:
        heygen = self.report.extras["heygen_on_openrouter"]
        self.assertTrue(heygen, "expected HeyGen models on OpenRouter")
        self.assertTrue(all(item.startswith("heygen/avatar-iv") for item in heygen), heygen)
        row = next(r for r in self.report.results if r.capability == "video.heygen_gateway")
        self.assertEqual(row.coverage, "partial")
        self.assertIn("heygen/avatar-iv", row.found_models)

    def test_higgsfield_and_elevenlabs_and_suno_are_absent(self) -> None:
        self.assertEqual(self.report.extras["higgsfield_on_openrouter"], [])
        self.assertEqual(self.report.extras["elevenlabs_on_openrouter"], [])
        self.assertEqual(self.report.extras["suno_on_openrouter"], [])

    def test_declared_yes_rows_are_live(self) -> None:
        failures = [r.capability for r in self.report.results if r.coverage == "yes" and not r.live_ok]
        self.assertEqual(failures, [])

    def test_local_studio_rows_are_not_claimed_as_openrouter(self) -> None:
        local = [r for r in self.report.results if r.coverage == "local_only"]
        self.assertTrue(local)
        for row in local:
            self.assertEqual(row.expected_models, [])

    def test_markdown_report_renders(self) -> None:
        markdown = render_markdown(self.report)
        self.assertIn("OpenMontage × Agent SDK × OpenRouter", markdown)
        self.assertIn("heygen/avatar-iv", markdown)


if __name__ == "__main__":
    unittest.main()
