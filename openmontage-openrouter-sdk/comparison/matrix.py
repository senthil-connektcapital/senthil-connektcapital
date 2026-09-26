"""Static map of OpenMontage production capabilities vs OpenRouter coverage.

OpenMontage is AGPL-3.0 and lives at https://github.com/calesthio/OpenMontage.
This matrix is an independently written capability inventory used for comparison.
It is not a copy of OpenMontage source.
"""

from __future__ import annotations

from typing import Literal

Coverage = Literal["yes", "partial", "no", "bonus", "local_only"]


CAPABILITIES: list[dict] = [
    # --- Video generation ---
    {
        "capability": "video.text_to_video.veo",
        "openmontage": "veo_video (FAL_KEY or GOOGLE_API_KEY)",
        "openrouter_models": [
            "google/veo-3.1",
            "google/veo-3.1-fast",
            "google/veo-3.1-lite",
        ],
        "coverage": "yes",
        "notes": "Same family via one OpenRouter key. Native audio flags still differ per model.",
    },
    {
        "capability": "video.text_to_video.kling",
        "openmontage": "kling_video (FAL_KEY) + kling_official_video (KLING_API_KEY)",
        "openrouter_models": [
            "kwaivgi/kling-v3.0-pro",
            "kwaivgi/kling-v3.0-std",
            "kwaivgi/kling-video-o1",
        ],
        "coverage": "yes",
        "notes": "Generation yes. Official Kling Elements, account usage, and first-party avatar/lip-sync APIs are not on OpenRouter.",
    },
    {
        "capability": "video.text_to_video.seedance",
        "openmontage": "seedance_video (FAL_KEY), seedance_ark (ARK_API_KEY), seedance_replicate",
        "openrouter_models": [
            "bytedance/seedance-2.5",
            "bytedance/seedance-2.0",
            "bytedance/seedance-2.0-fast",
            "bytedance/seedance-2.0-mini",
            "bytedance/seedance-1-5-pro",
        ],
        "coverage": "yes",
        "notes": "Best OpenRouter replacement for OpenMontage's preferred premium default.",
    },
    {
        "capability": "video.text_to_video.wan",
        "openmontage": "wan_video local GPU (VIDEO_GEN_LOCAL_ENABLED)",
        "openrouter_models": [
            "alibaba/wan-3.0-prime",
            "alibaba/wan-3.0",
            "alibaba/wan-2.7",
            "alibaba/wan-2.6",
        ],
        "coverage": "yes",
        "notes": "Cloud Wan instead of local checkpoints. Offline/privacy path is lost.",
    },
    {
        "capability": "video.text_to_video.minimax",
        "openmontage": "minimax_video (MINIMAX_API_KEY) + minimax_fal_video (FAL_KEY)",
        "openrouter_models": ["minimax/hailuo-3", "minimax/hailuo-2.3"],
        "coverage": "yes",
        "notes": "H3 is on OpenRouter (2K, audio). Direct MiniMax CN region routing is not.",
    },
    {
        "capability": "video.text_to_video.runway",
        "openmontage": "runway_video (RUNWAY_API_KEY)",
        "openrouter_models": ["runway/gen-4.5", "runway/aleph-2"],
        "coverage": "yes",
        "notes": "Aleph 2 is video-to-video / edit oriented; Gen-4.5 is the closer T2V match.",
    },
    {
        "capability": "video.text_to_video.grok",
        "openmontage": "grok_video (XAI_API_KEY)",
        "openrouter_models": [
            "x-ai/grok-imagine-video",
            "x-ai/grok-imagine-video-1.5",
        ],
        "coverage": "yes",
        "notes": "",
    },
    {
        "capability": "video.text_to_video.sora",
        "openmontage": "sora_video (OPENAI_API_KEY)",
        "openrouter_models": ["openai/sora-2-pro"],
        "coverage": "yes",
        "notes": "OpenRouter lists Sora 2 Pro only; availability still depends on OpenRouter routing.",
    },
    {
        "capability": "video.heygen_gateway",
        "openmontage": "heygen_video (HEYGEN_API_KEY) — workflow gateway to Veo/Sora/Kling/Runway/Seedance",
        "openrouter_models": ["heygen/avatar-iv"],
        "coverage": "partial",
        "notes": (
            "Different product. OpenRouter HeyGen is Avatar IV talking-head generation "
            "(text+image+audio → video). It is NOT HeyGen's multi-model GenerateVideoNode "
            "workflow that OpenMontage uses as a one-key Veo/Sora/Kling router."
        ),
    },
    {
        "capability": "video.avatar.talking_head",
        "openmontage": "talking_head local (SadTalker/MuseTalk) + kling_avatar + heygen avatars",
        "openrouter_models": ["heygen/avatar-iv"],
        "coverage": "partial",
        "notes": "Cloud avatar yes. Local lip-sync (Wav2Lip/SadTalker) and Kling Official avatar/lip-sync stay off OpenRouter.",
    },
    {
        "capability": "video.higgsfield",
        "openmontage": "higgsfield_video (HIGGSFIELD_API_KEY + SECRET)",
        "openrouter_models": [],
        "coverage": "no",
        "notes": "No Higgsfield models on OpenRouter.",
    },
    {
        "capability": "video.hunyuan",
        "openmontage": "hunyuan_video local + hunyuan_cloud_video (TENCENT_TOKENHUB_API_KEY)",
        "openrouter_models": [],
        "coverage": "no",
        "notes": "Hunyuan on OpenRouter is text LLM only, not HunyuanVideo.",
    },
    {
        "capability": "video.ltx_cogvideo_local",
        "openmontage": "ltx_video_local, ltx_video_modal, cogvideo_video",
        "openrouter_models": [],
        "coverage": "no",
        "notes": "Local/self-hosted GPU paths have no OpenRouter equivalent.",
    },
    {
        "capability": "video.jimeng",
        "openmontage": "jimeng_video (VOLC_ACCESSKEY/SECRETKEY)",
        "openrouter_models": [],
        "coverage": "no",
        "notes": "Volcengine Jimeng is first-party only.",
    },
    {
        "capability": "video.gemini_omni_edit",
        "openmontage": "gemini_omni_video conversational video editing",
        "openrouter_models": [],
        "coverage": "no",
        "notes": "OpenRouter has Veo generation, not Gemini Omni's timecoded conversational editor.",
    },
    {
        "capability": "video.atlas_gateway",
        "openmontage": "atlas_video (ATLASCLOUD_API_KEY) — already a one-key multi-model gateway",
        "openrouter_models": [],
        "coverage": "partial",
        "notes": "Atlas Cloud is the closest existing OpenMontage analogue to OpenRouter. Overlapping models; different catalog and request shapes.",
    },
    {
        "capability": "video.comfyui",
        "openmontage": "comfyui_video local server",
        "openrouter_models": [],
        "coverage": "no",
        "notes": "Node graphs stay local.",
    },
    {
        "capability": "video.stock",
        "openmontage": "pexels_video, pixabay_video, NASA/ESA/NARA/archive.org corpus builder",
        "openrouter_models": [],
        "coverage": "no",
        "notes": "Stock and public-archive retrieval is not a generative API. Keep Pexels/Pixabay keys or use free archives.",
    },
    {
        "capability": "video.flux3_bonus",
        "openmontage": "not a first-class OpenMontage video tool",
        "openrouter_models": [
            "black-forest-labs/flux-3-video",
            "black-forest-labs/flux-video-upscale",
            "alibaba/happyhorse-1.1",
            "alibaba/happyhorse-1.0",
        ],
        "coverage": "bonus",
        "notes": "OpenRouter-only extras OpenMontage does not wrap today.",
    },
    # --- Images ---
    {
        "capability": "image.flux",
        "openmontage": "flux_image (FAL_KEY)",
        "openrouter_models": [
            "black-forest-labs/flux.2-pro",
            "black-forest-labs/flux.2-max",
            "black-forest-labs/flux.2-flex",
            "black-forest-labs/flux.2-klein-4b",
        ],
        "coverage": "yes",
        "notes": "",
    },
    {
        "capability": "image.recraft",
        "openmontage": "recraft_image (FAL_KEY)",
        "openrouter_models": [
            "recraft/recraft-v4.1",
            "recraft/recraft-v4.1-pro",
            "recraft/recraft-v4",
            "recraft/recraft-v3",
        ],
        "coverage": "yes",
        "notes": "Vector/style variants also exist on OpenRouter.",
    },
    {
        "capability": "image.openai",
        "openmontage": "openai_image (OPENAI_API_KEY)",
        "openrouter_models": [
            "openai/gpt-image-2",
            "openai/gpt-image-1",
            "openai/gpt-image-1-mini",
            "openai/gpt-5-image",
        ],
        "coverage": "yes",
        "notes": "",
    },
    {
        "capability": "image.grok",
        "openmontage": "grok_image (XAI_API_KEY)",
        "openrouter_models": [
            "x-ai/grok-imagine-image-2.0",
            "x-ai/grok-imagine-image-quality",
        ],
        "coverage": "yes",
        "notes": "",
    },
    {
        "capability": "image.google",
        "openmontage": "google_imagen (GOOGLE_API_KEY)",
        "openrouter_models": [
            "google/gemini-3.1-flash-image",
            "google/gemini-3-pro-image",
            "google/gemini-2.5-flash-image",
        ],
        "coverage": "yes",
        "notes": "Gemini image models, not necessarily Vertex Imagen SKUs.",
    },
    {
        "capability": "image.seedream_qwen",
        "openmontage": "seedream_image (FAL_KEY), dashscope_image (DASHSCOPE_API_KEY)",
        "openrouter_models": [
            "bytedance-seed/seedream-5-0-pro",
            "bytedance-seed/seedream-5-0-lite",
            "bytedance-seed/seedream-4.5",
            "qwen/qwen-image-3",
            "qwen/qwen-image-3-pro",
        ],
        "coverage": "yes",
        "notes": "",
    },
    {
        "capability": "image.local_stock",
        "openmontage": "local_diffusion, pexels_image, pixabay_image",
        "openrouter_models": [],
        "coverage": "no",
        "notes": "Offline diffusion and stock search stay outside OpenRouter.",
    },
    # --- Speech / music / STT ---
    {
        "capability": "tts.elevenlabs",
        "openmontage": "elevenlabs_tts + fal_elevenlabs_tts (ELEVENLABS_API_KEY / FAL_KEY)",
        "openrouter_models": [],
        "coverage": "no",
        "notes": "No ElevenLabs on OpenRouter. Closest paid substitutes: Fish Audio, MiniMax Speech, Grok Voice, Gemini TTS.",
    },
    {
        "capability": "tts.fish_audio",
        "openmontage": "fish_audio_tts (FISH_AUDIO_API_KEY)",
        "openrouter_models": [
            "fish-audio/s1",
            "fish-audio/s2-pro",
            "fish-audio/s2.1-pro",
        ],
        "coverage": "yes",
        "notes": "Voice cloning via OpenRouter still depends on Fish Audio reference_id passthrough.",
    },
    {
        "capability": "tts.google_openai_minimax_qwen_grok",
        "openmontage": "google_tts, openai_tts, dashscope_tts, plus MiniMax/Grok if keyed",
        "openrouter_models": [
            "google/gemini-3.1-flash-tts-preview",
            "openai/gpt-audio",
            "openai/gpt-audio-mini",
            "minimax/speech-2.8-hd",
            "minimax/speech-2.8-turbo",
            "qwen/qwen-audio-3.0-tts-plus",
            "x-ai/grok-voice-tts-1.0",
        ],
        "coverage": "partial",
        "notes": "Narration exists, but OpenMontage's 700-voice Google Cloud TTS catalog and SSML styles do not map 1:1.",
    },
    {
        "capability": "tts.local_azure_kling_doubao",
        "openmontage": "piper_tts, azure_tts, kling_tts, doubao_tts",
        "openrouter_models": ["hexgrad/kokoro-82m"],
        "coverage": "partial",
        "notes": "Kokoro is a small local-style voice. Azure neural SSML, Kling TTS, and Doubao stay first-party.",
    },
    {
        "capability": "music.elevenlabs_suno",
        "openmontage": "music_gen / fal_elevenlabs_music, suno_music",
        "openrouter_models": [
            "google/lyria-3-pro-preview",
            "google/lyria-3-clip-preview",
        ],
        "coverage": "partial",
        "notes": "Lyria is a music bonus. Suno and ElevenLabs music are absent. Pixabay/Freesound libraries still need their own keys.",
    },
    {
        "capability": "stt.whisperx_azure_dashscope",
        "openmontage": "transcriber (WhisperX local), azure_stt, dashscope_asr",
        "openrouter_models": [
            "openai/whisper-large-v3",
            "openai/gpt-4o-transcribe",
            "google/chirp-3",
            "qwen/qwen3-asr-flash-2026-02-10",
            "fish-audio/transcribe-1",
            "x-ai/grok-stt-1.0",
        ],
        "coverage": "partial",
        "notes": "Cloud STT yes. WhisperX word-level timestamps + diarization (HF_TOKEN) are local and better for caption burn-in.",
    },
    # --- Studio / orchestration that is never an LLM API ---
    {
        "capability": "studio.ffmpeg_remotion_hyperframes",
        "openmontage": "video_compose, hyperframes_compose, remotion-composer",
        "openrouter_models": [],
        "coverage": "local_only",
        "notes": "Composition runtimes are local Node/FFmpeg. OpenRouter cannot replace them.",
    },
    {
        "capability": "studio.enhancement",
        "openmontage": "upscale, bg_remove, face_restore, color_grade",
        "openrouter_models": ["black-forest-labs/flux-video-upscale"],
        "coverage": "partial",
        "notes": "One video upscaler. No rembg/U2Net, CodeFormer, or LUT grading on OpenRouter.",
    },
    {
        "capability": "studio.character_3d_manim",
        "openmontage": "character-animation, threejs/blender worlds, manim, diagrams",
        "openrouter_models": [],
        "coverage": "local_only",
        "notes": "These pipelines are code + local renderers, not video-model calls.",
    },
    {
        "capability": "studio.skills_and_pipelines",
        "openmontage": "12 pipelines, 700+ skill files, checkpoint/budget/reviewer protocol",
        "openrouter_models": [],
        "coverage": "local_only",
        "notes": "Skills are markdown instructions. An Agent SDK can read them; OpenRouter does not host them.",
    },
]


KEYS_OPENMONTAGE_REPLACES_WITH_OPENROUTER = [
    "FAL_KEY / FAL_AI_API_KEY (for FLUX, Veo, Kling, MiniMax, Recraft, Seedance, Seedream)",
    "GOOGLE_API_KEY / GEMINI_API_KEY (Veo + Gemini image + some TTS)",
    "XAI_API_KEY (Grok image/video)",
    "OPENAI_API_KEY (Sora + GPT Image + OpenAI TTS, if routed)",
    "RUNWAY_API_KEY",
    "MINIMAX_API_KEY (Hailuo video + Speech 2.8)",
    "KLING_API_KEY (generation only, not Elements/avatar/lip-sync)",
    "ARK_API_KEY / REPLICATE_API_TOKEN (Seedance)",
    "DASHSCOPE_API_KEY (Qwen image/TTS/ASR)",
    "FISH_AUDIO_API_KEY",
    "ATLASCLOUD_API_KEY (overlapping video/image gateway)",
]

KEYS_STILL_REQUIRED = [
    "ELEVENLABS_API_KEY — no ElevenLabs on OpenRouter",
    "HEYGEN_API_KEY — only if you need HeyGen workflow gateway or Avatar IV outside OpenRouter's subset",
    "HIGGSFIELD_API_KEY + SECRET",
    "PEXELS_API_KEY / PIXABAY_API_KEY / UNSPLASH_ACCESS_KEY — stock",
    "SUNO_API_KEY",
    "AZURE_SPEECH_KEY — neural SSML + Fast Transcription",
    "TENCENT_TOKENHUB_API_KEY — Hunyuan image/video",
    "VOLC_ACCESSKEY/SECRETKEY — Jimeng",
    "HF_TOKEN — WhisperX diarization",
    "Local GPU / ComfyUI / Modal LTX — offline generation",
]


def by_coverage() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in CAPABILITIES:
        grouped.setdefault(row["coverage"], []).append(row)
    return grouped
