# OpenMontage in Agent SDKs, with OpenRouter instead of a keychain

This repo answers three questions about [OpenMontage](https://github.com/calesthio/OpenMontage):

1. Can the 12-pipeline / 700-skill video studio run from **Claude Agent SDK or Codex SDK** instead of the interactive CLI?
2. Can **one OpenRouter key** replace FAL, HeyGen, Kling, Runway, xAI, Google, MiniMax, and friends?
3. What still **cannot** move?

A live catalog comparison ran against OpenRouter on 2026-08-28. Re-run it anytime:

```bash
python3 openmontage-openrouter-sdk/comparison/run.py
python3 -m unittest discover -s openmontage-openrouter-sdk/tests -v
```

OpenMontage itself is AGPL-3.0. This tree is an independent adapter + comparison; it does not vendor OpenMontage source.

---

## Short answers

| Question | Answer |
|---|---|
| Agent SDK instead of CLI? | **Yes, as the control plane.** Point the SDK `cwd` / `working_directory` at an OpenMontage checkout. The agent still *is* the orchestrator (YAML pipelines + markdown skills + Python tools). You call it from Python/TypeScript, not a human-driven terminal. |
| One OpenRouter key for video models + HeyGen? | **Mostly for generation, not for the whole studio.** OpenRouter currently lists HeyGen **Avatar IV**, Kling, Veo, Seedance, Wan, MiniMax Hailuo, Runway, Grok Imagine, Sora 2 Pro, FLUX.3 Video. That is a real one-key video menu. |
| Replace every OpenMontage key? | **No.** ElevenLabs, Higgsfield, stock (Pexels/Pixabay), Suno, HunyuanVideo, Jimeng, local GPU (LTX/CogVideo), FFmpeg/Remotion/HyperFrames, and HeyGen's *workflow gateway* (Veo/Sora/Kling via HeyGen, not Avatar IV) stay outside OpenRouter. |

---

## What OpenMontage actually is

OpenMontage is not a Python supervisor that calls Claude. The coding agent **is** the control plane:

```
user prompt
    → agent reads pipeline_defs/*.yaml
    → each stage: read skills/pipelines/<pipe>/<stage>-director.md
    → call tools/ via the registry (FFmpeg, Remotion, Veo, TTS, …)
    → checkpoint JSON + budget + human approval gates
    → final mp4
```

Three knowledge layers:

| Layer | Where | Role |
|---|---|---|
| 1 | `tools/` + `pipeline_defs/` | Executable tools and stage graphs |
| 2 | `skills/` | OpenMontage conventions, directors, quality gates |
| 3 | `.agents/skills/` and `.claude/skills/` | Vendor playbooks (FFmpeg, Remotion, HeyGen, Seedance, …) |

That design is why “put it in an Agent SDK” works: SDKs already know how to read files, run shell, and load skills. You do **not** need to rewrite 700 markdown files as function tools.

---

## Agent SDK vs CLI (what you asked for)

| | Claude Code / Codex **CLI** | **Claude Agent SDK** | **Codex SDK** | OpenAI **Agents SDK** |
|---|---|---|---|---|
| How you start it | Human in a terminal | `query()` / `ClaudeSDKClient` in your app | `thread.run()` in your app | `Runner.run(agent, …)` |
| Same file/shell harness as the product CLI | yes | yes (Claude Code runtime) | yes (spawns Codex app-server) | no — you build tools |
| Loads OpenMontage skills | `AGENTS.md`, `.claude/`, `.agents/skills/` | `cwd` + `skills="all"` + project settings | working directory + `SkillInput` | you must implement skill loading |
| Orchestrator LLM via OpenRouter | Claude: `ANTHROPIC_BASE_URL`; Codex: `baseUrl` | same env as Claude Code | `base_url` / `openai_base_url` | native OpenAI-compatible |
| Fits “not the command line” | no | **yes for your app API** | **yes for your app API** | yes, but you lose OpenMontage’s harness |

Honest caveat: both official coding-agent SDKs still boot their CLI/runtime **as a library**. You never type `claude` or `codex`. You also cannot delete that runtime and keep the skill/file loop for free.

### Claude Agent SDK (recommended fit)

```python
from pathlib import Path
from sdk.claude_driver import run_production
import asyncio

async def main():
    async for message in run_production(
        "Produce a 45s cinematic trailer about salt trade, vertical 9:16",
        Path("/path/to/OpenMontage"),
        use_openrouter_orchestrator=True,
    ):
        print(message)

asyncio.run(main())
```

Env for a **single OpenRouter key** on the orchestrator:

```bash
export OPENROUTER_API_KEY=sk-or-...
export ANTHROPIC_BASE_URL=https://openrouter.ai/api
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"
export ANTHROPIC_API_KEY=   # explicitly empty
```

Keep the orchestrator on a tool-using model (Claude Sonnet/Opus via OpenRouter is the safe default). Random chat models break the agent loop.

### Codex SDK

```python
from sdk.codex_driver import thread_config, production_input

config = thread_config(
    Path("/path/to/OpenMontage"),
    model="openai/gpt-5.4",
    base_url="https://openrouter.ai/api/v1",
)
# Codex(config).start_thread().run(production_input("..."))
```

Codex is a good specialist for the *code* parts of OpenMontage (Remotion, HyperFrames, FFmpeg graphs). It is a weaker default executive producer than Claude for long skill-following production.

---

## OpenRouter vs OpenMontage’s keychain

OpenMontage’s `.env.example` is a vendor zoo: `FAL_KEY`, `HEYGEN_API_KEY`, `KLING_API_KEY`, `RUNWAY_API_KEY`, `XAI_API_KEY`, `GOOGLE_API_KEY`, `MINIMAX_API_KEY`, `ELEVENLABS_API_KEY`, Atlas, Ark, Replicate, Higgsfield, DashScope, stock, …

OpenRouter already does what Atlas Cloud does inside OpenMontage: **one key, many models**, including video (`POST /api/v1/videos`).

### Can do with OpenRouter today

- **Video:** Veo 3.1 / Fast / Lite, Kling v3 Pro/Std/O1, Seedance 2.5 + 2.0 family, Wan 2.6/2.7/3.0, MiniMax Hailuo 3 + 2.3, Runway Gen-4.5 + Aleph 2, Grok Imagine Video, Sora 2 Pro, FLUX.3 Video, HappyHorse
- **HeyGen:** `heygen/avatar-iv` talking-head avatars (text + image + audio → video)
- **Image:** FLUX.2, Recraft v4/v4.1, GPT Image, Grok Imagine Image, Gemini image, Seedream, Qwen Image
- **Speech:** Fish Audio S1/S2, MiniMax Speech 2.8, Grok Voice, Gemini TTS preview, Qwen TTS, Kokoro
- **STT:** Whisper, Chirp 3, Grok STT, Qwen ASR, Fish Transcribe
- **Music (bonus):** Google Lyria 3 previews

### Cannot do / must keep other keys or local runtimes

| Gap | Why |
|---|---|
| HeyGen **workflow gateway** (Veo/Sora/Kling/Runway via HeyGen) | OpenRouter’s HeyGen SKU is Avatar IV, not `GenerateVideoNode` |
| Higgsfield | not in the catalog |
| ElevenLabs TTS / music / SFX | not in the catalog |
| Suno | not in the catalog |
| HunyuanVideo, LTX-2, CogVideo, local Wan | GPU / Tencent TokenHub / Modal |
| Jimeng (Volcengine) | first-party HMAC API |
| Gemini Omni conversational video edit | Veo ≠ Omni editor |
| Kling Official Elements, avatar, lip-sync, TTS | generation-only on OpenRouter |
| Pexels / Pixabay / Unsplash / public archives | retrieval, not generation — this is OpenMontage’s “real video video” path |
| Remotion, HyperFrames, FFmpeg compose/stitch/grade | local studio |
| Character animation, 3D worlds, Manim, screen capture | local |
| WhisperX diarization + word-level captions | local + `HF_TOKEN` |

Full live matrix: [`artifacts/comparison-report.md`](artifacts/comparison-report.md).

---

## Recommended architecture

```
Your app
  └─ Claude Agent SDK  (cwd = OpenMontage clone)
        ├─ reads skills + pipeline_defs
        ├─ Bash: python tools  (registry, FFmpeg, Remotion, HyperFrames)
        └─ generation calls
              └─ OpenRouter  (one key: video / image / TTS / STT / orchestrator LLM)
                    optional leftovers: ElevenLabs, Pexels, Higgsfield, local GPU
```

That is the smallest change that matches the request:

- **SDK, not CLI**, for the producer
- **OpenRouter, not a keychain**, for most video models including HeyGen Avatar IV, Kling, Veo, Seedance, Wan, MiniMax, Runway, Grok, Sora
- **Keep OpenMontage skills** instead of rewriting them

OpenMontage already has a similar one-key idea (`atlas_video`). OpenRouter is the broader public catalog; Atlas remains a parallel gateway, not a blocker.

---

## What we ran

`python3 -m unittest discover -s openmontage-openrouter-sdk/tests -v` hits the live OpenRouter catalog (no generation spend) and asserts:

- Veo, Kling, Seedance, Runway, MiniMax Hailuo are listed
- HeyGen is `heygen/avatar-iv` only
- Higgsfield, ElevenLabs, and Suno are absent
- Every matrix row marked `yes` still resolves in the live catalog
- Claude/Codex SDK helpers are library configs, not CLI argv

Paid `POST /api/v1/videos` is implemented in `gateway/openrouter.py` but not executed in CI (it costs money and needs `OPENROUTER_API_KEY`).
