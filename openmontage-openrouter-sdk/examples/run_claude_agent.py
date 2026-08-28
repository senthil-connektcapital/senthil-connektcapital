#!/usr/bin/env python3
"""Example: drive OpenMontage from Claude Agent SDK (not the CLI).

Requires:
  pip install claude-agent-sdk
  a local OpenMontage clone
  OPENROUTER_API_KEY
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sdk.claude_driver import can_embed_openmontage, run_production


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--montage-root", type=Path, required=True)
    parser.add_argument("prompt")
    args = parser.parse_args()
    preflight = can_embed_openmontage(args.montage_root)
    missing = [name for name, ok in preflight.items() if not ok]
    if missing:
        raise SystemExit(f"OpenMontage checkout looks incomplete: {missing}")
    async for message in run_production(args.prompt, args.montage_root):
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
