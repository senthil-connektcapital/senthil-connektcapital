"""SDK wiring tests that do not require Claude/Codex packages."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdk.claude_driver import claude_options, openrouter_orchestrator_env
from sdk.codex_driver import production_input, skill_mentions, thread_config


class ClaudeDriverTests(unittest.TestCase):
    def test_options_point_at_montage_and_enable_skills(self) -> None:
        options = claude_options(Path("/tmp/OpenMontage"))
        self.assertEqual(options["cwd"], "/tmp/OpenMontage")
        self.assertEqual(options["skills"], "all")
        self.assertIn("Skill", options["allowed_tools"])
        self.assertIn("Bash", options["allowed_tools"])
        self.assertNotIn("cli", str(options).lower())

    def test_openrouter_orchestrator_env_blanks_anthropic_key(self) -> None:
        env = openrouter_orchestrator_env("sk-or-test")
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "https://openrouter.ai/api")
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "sk-or-test")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "")


class CodexDriverTests(unittest.TestCase):
    def test_thread_config_is_library_not_cli_invocation(self) -> None:
        config = thread_config(Path("/tmp/OpenMontage"), model="openai/gpt-5.4", base_url="https://openrouter.ai/api/v1")
        self.assertEqual(config["working_directory"], "/tmp/OpenMontage")
        self.assertEqual(config["base_url"], "https://openrouter.ai/api/v1")
        self.assertNotIn("argv", config)

    def test_skill_mentions_from_real_clone(self) -> None:
        clone = Path("/tmp/OpenMontage")
        if not clone.exists():
            self.skipTest("OpenMontage clone not present")
        mentions = skill_mentions(clone)
        names = {m["name"] for m in mentions}
        self.assertIn("AGENT_GUIDE", names)

    def test_production_input_routes_to_openrouter_tools(self) -> None:
        text = production_input("Make a 20s trailer about salt")
        self.assertIn("AGENT_GUIDE.md", text)
        self.assertIn("OPENROUTER_API_KEY", text)


if __name__ == "__main__":
    unittest.main()
