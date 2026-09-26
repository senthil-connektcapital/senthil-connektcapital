# OpenMontage × Agent SDK × OpenRouter — live comparison

- Video models on OpenRouter: **54**
- Image-output models: **50**
- Speech/audio-output models: **22**
- Transcription models: **19**
- Capability rows: **36** (yes=15, partial=8, no=9, bonus=1, local_only=3)

## Verdict

You can drive OpenMontage **from Claude Agent SDK or Codex SDK** (not the interactive CLI) because those SDKs are the same file/shell agent loop with a Python/TypeScript API. You can replace **most generation API keys** with one `OPENROUTER_API_KEY`. You cannot collapse the whole studio into OpenRouter: composition, stock, local GPU, ElevenLabs, Higgsfield, and HeyGen's multi-model workflow stay outside it.

## Capability matrix (live catalog)

| Capability | Coverage | Live match | OpenMontage today | OpenRouter models found |
|---|---|---|---|---|
| `video.text_to_video.veo` | covered | ok | veo_video (FAL_KEY or GOOGLE_API_KEY) | `google/veo-3.1`, `google/veo-3.1-fast`, `google/veo-3.1-lite` |
| `video.text_to_video.kling` | covered | ok | kling_video (FAL_KEY) + kling_official_video (KLING_API_KEY) | `kwaivgi/kling-v3.0-pro`, `kwaivgi/kling-v3.0-std`, `kwaivgi/kling-video-o1` |
| `video.text_to_video.seedance` | covered | ok | seedance_video (FAL_KEY), seedance_ark (ARK_API_KEY), seedance_replicate | `bytedance/seedance-2.5`, `bytedance/seedance-2.0`, `bytedance/seedance-2.0-fast`, `bytedance/seedance-2.0-mini`, `bytedance/seedance-1-5-pro` |
| `video.text_to_video.wan` | covered | ok | wan_video local GPU (VIDEO_GEN_LOCAL_ENABLED) | `alibaba/wan-3.0-prime`, `alibaba/wan-3.0`, `alibaba/wan-2.7`, `alibaba/wan-2.6` |
| `video.text_to_video.minimax` | covered | ok | minimax_video (MINIMAX_API_KEY) + minimax_fal_video (FAL_KEY) | `minimax/hailuo-3`, `minimax/hailuo-2.3` |
| `video.text_to_video.runway` | covered | ok | runway_video (RUNWAY_API_KEY) | `runway/gen-4.5`, `runway/aleph-2` |
| `video.text_to_video.grok` | covered | ok | grok_video (XAI_API_KEY) | `x-ai/grok-imagine-video`, `x-ai/grok-imagine-video-1.5` |
| `video.text_to_video.sora` | covered | ok | sora_video (OPENAI_API_KEY) | `openai/sora-2-pro` |
| `video.heygen_gateway` | partial | ok | heygen_video (HEYGEN_API_KEY) — workflow gateway to Veo/Sora/Kling/Runway/Seedance | `heygen/avatar-iv` |
| `video.avatar.talking_head` | partial | ok | talking_head local (SadTalker/MuseTalk) + kling_avatar + heygen avatars | `heygen/avatar-iv` |
| `video.higgsfield` | not on OpenRouter | ok | higgsfield_video (HIGGSFIELD_API_KEY + SECRET) | — |
| `video.hunyuan` | not on OpenRouter | ok | hunyuan_video local + hunyuan_cloud_video (TENCENT_TOKENHUB_API_KEY) | — |
| `video.ltx_cogvideo_local` | not on OpenRouter | ok | ltx_video_local, ltx_video_modal, cogvideo_video | — |
| `video.jimeng` | not on OpenRouter | ok | jimeng_video (VOLC_ACCESSKEY/SECRETKEY) | — |
| `video.gemini_omni_edit` | not on OpenRouter | ok | gemini_omni_video conversational video editing | — |
| `video.atlas_gateway` | partial | ok | atlas_video (ATLASCLOUD_API_KEY) — already a one-key multi-model gateway | — |
| `video.comfyui` | not on OpenRouter | ok | comfyui_video local server | — |
| `video.stock` | not on OpenRouter | ok | pexels_video, pixabay_video, NASA/ESA/NARA/archive.org corpus builder | — |
| `video.flux3_bonus` | OpenRouter extra | ok | not a first-class OpenMontage video tool | `black-forest-labs/flux-3-video`, `black-forest-labs/flux-video-upscale`, `alibaba/happyhorse-1.1`, `alibaba/happyhorse-1.0` |
| `image.flux` | covered | ok | flux_image (FAL_KEY) | `black-forest-labs/flux.2-pro`, `black-forest-labs/flux.2-max`, `black-forest-labs/flux.2-flex`, `black-forest-labs/flux.2-klein-4b` |
| `image.recraft` | covered | ok | recraft_image (FAL_KEY) | `recraft/recraft-v4.1`, `recraft/recraft-v4.1-pro`, `recraft/recraft-v4`, `recraft/recraft-v3` |
| `image.openai` | covered | ok | openai_image (OPENAI_API_KEY) | `openai/gpt-image-2`, `openai/gpt-image-1`, `openai/gpt-image-1-mini`, `openai/gpt-5-image` |
| `image.grok` | covered | ok | grok_image (XAI_API_KEY) | `x-ai/grok-imagine-image-2.0`, `x-ai/grok-imagine-image-quality` |
| `image.google` | covered | ok | google_imagen (GOOGLE_API_KEY) | `google/gemini-3.1-flash-image`, `google/gemini-3-pro-image`, `google/gemini-2.5-flash-image` |
| `image.seedream_qwen` | covered | ok | seedream_image (FAL_KEY), dashscope_image (DASHSCOPE_API_KEY) | `bytedance-seed/seedream-5-0-pro`, `bytedance-seed/seedream-5-0-lite`, `bytedance-seed/seedream-4.5`, `qwen/qwen-image-3`, `qwen/qwen-image-3-pro` |
| `image.local_stock` | not on OpenRouter | ok | local_diffusion, pexels_image, pixabay_image | — |
| `tts.elevenlabs` | not on OpenRouter | ok | elevenlabs_tts + fal_elevenlabs_tts (ELEVENLABS_API_KEY / FAL_KEY) | — |
| `tts.fish_audio` | covered | ok | fish_audio_tts (FISH_AUDIO_API_KEY) | `fish-audio/s1`, `fish-audio/s2-pro`, `fish-audio/s2.1-pro` |
| `tts.google_openai_minimax_qwen_grok` | partial | ok | google_tts, openai_tts, dashscope_tts, plus MiniMax/Grok if keyed | `google/gemini-3.1-flash-tts-preview`, `openai/gpt-audio`, `openai/gpt-audio-mini`, `minimax/speech-2.8-hd`, `minimax/speech-2.8-turbo`, `qwen/qwen-audio-3.0-tts-plus`, `x-ai/grok-voice-tts-1.0` |
| `tts.local_azure_kling_doubao` | partial | ok | piper_tts, azure_tts, kling_tts, doubao_tts | `hexgrad/kokoro-82m` |
| `music.elevenlabs_suno` | partial | ok | music_gen / fal_elevenlabs_music, suno_music | `google/lyria-3-pro-preview`, `google/lyria-3-clip-preview` |
| `stt.whisperx_azure_dashscope` | partial | ok | transcriber (WhisperX local), azure_stt, dashscope_asr | `openai/whisper-large-v3`, `openai/gpt-4o-transcribe`, `google/chirp-3`, `qwen/qwen3-asr-flash-2026-02-10`, `fish-audio/transcribe-1`, `x-ai/grok-stt-1.0` |
| `studio.ffmpeg_remotion_hyperframes` | local studio (not an API) | ok | video_compose, hyperframes_compose, remotion-composer | — |
| `studio.enhancement` | partial | ok | upscale, bg_remove, face_restore, color_grade | `black-forest-labs/flux-video-upscale` |
| `studio.character_3d_manim` | local studio (not an API) | ok | character-animation, threejs/blender worlds, manim, diagrams | — |
| `studio.skills_and_pipelines` | local studio (not an API) | ok | 12 pipelines, 700+ skill files, checkpoint/budget/reviewer protocol | — |

## Keys one OpenRouter credential can replace

- FAL_KEY / FAL_AI_API_KEY (for FLUX, Veo, Kling, MiniMax, Recraft, Seedance, Seedream)
- GOOGLE_API_KEY / GEMINI_API_KEY (Veo + Gemini image + some TTS)
- XAI_API_KEY (Grok image/video)
- OPENAI_API_KEY (Sora + GPT Image + OpenAI TTS, if routed)
- RUNWAY_API_KEY
- MINIMAX_API_KEY (Hailuo video + Speech 2.8)
- KLING_API_KEY (generation only, not Elements/avatar/lip-sync)
- ARK_API_KEY / REPLICATE_API_TOKEN (Seedance)
- DASHSCOPE_API_KEY (Qwen image/TTS/ASR)
- FISH_AUDIO_API_KEY
- ATLASCLOUD_API_KEY (overlapping video/image gateway)

## Keys / runtimes you still need

- ELEVENLABS_API_KEY — no ElevenLabs on OpenRouter
- HEYGEN_API_KEY — only if you need HeyGen workflow gateway or Avatar IV outside OpenRouter's subset
- HIGGSFIELD_API_KEY + SECRET
- PEXELS_API_KEY / PIXABAY_API_KEY / UNSPLASH_ACCESS_KEY — stock
- SUNO_API_KEY
- AZURE_SPEECH_KEY — neural SSML + Fast Transcription
- TENCENT_TOKENHUB_API_KEY — Hunyuan image/video
- VOLC_ACCESSKEY/SECRETKEY — Jimeng
- HF_TOKEN — WhisperX diarization
- Local GPU / ComfyUI / Modal LTX — offline generation

## Live catalog probes

- HeyGen on OpenRouter: ['heygen/avatar-iv', 'heygen/avatar-iv-20260625']
- Kling on OpenRouter: ['kwaivgi/kling-v3.0-pro', 'kwaivgi/kling-v3.0-pro-20260429', 'kwaivgi/kling-v3.0-std', 'kwaivgi/kling-v3.0-std-20260429', 'kwaivgi/kling-video-o1', 'kwaivgi/kling-video-o1-20260420']
- Higgsfield on OpenRouter: none
- ElevenLabs on OpenRouter: none
- Suno on OpenRouter: none
- Live matrix failures: none

## Video models currently listed

- `alibaba/happyhorse-1.0`
- `alibaba/happyhorse-1.0-20260624`
- `alibaba/happyhorse-1.1`
- `alibaba/happyhorse-1.1-20260624`
- `alibaba/wan-2.6`
- `alibaba/wan-2.6-20260327`
- `alibaba/wan-2.7`
- `alibaba/wan-2.7-20260414`
- `alibaba/wan-3.0`
- `alibaba/wan-3.0-20260824`
- `alibaba/wan-3.0-prime`
- `alibaba/wan-3.0-prime-20260827`
- `black-forest-labs/flux-3-video`
- `black-forest-labs/flux-3-video-20260804`
- `black-forest-labs/flux-video-upscale`
- `black-forest-labs/flux-video-upscale-20260819`
- `bytedance/seedance-1-5-pro`
- `bytedance/seedance-1-5-pro-20260320`
- `bytedance/seedance-2.0`
- `bytedance/seedance-2.0-20260414`
- `bytedance/seedance-2.0-fast`
- `bytedance/seedance-2.0-fast-20260414`
- `bytedance/seedance-2.0-mini`
- `bytedance/seedance-2.0-mini-20260811`
- `bytedance/seedance-2.5`
- `bytedance/seedance-2.5-20260807`
- `google/veo-3.1`
- `google/veo-3.1-20260320`
- `google/veo-3.1-fast`
- `google/veo-3.1-fast-20260320`
- `google/veo-3.1-lite`
- `google/veo-3.1-lite-20260331`
- `heygen/avatar-iv`
- `heygen/avatar-iv-20260625`
- `kwaivgi/kling-v3.0-pro`
- `kwaivgi/kling-v3.0-pro-20260429`
- `kwaivgi/kling-v3.0-std`
- `kwaivgi/kling-v3.0-std-20260429`
- `kwaivgi/kling-video-o1`
- `kwaivgi/kling-video-o1-20260420`
- `minimax/hailuo-03-20260730`
- `minimax/hailuo-2.3`
- `minimax/hailuo-2.3-20260420`
- `minimax/hailuo-3`
- `openai/sora-2-pro`
- `openai/sora-2-pro-20260320`
- `runway/aleph-2`
- `runway/aleph-2-20260729`
- `runway/gen-4.5`
- `runway/gen-4.5-20260729`
- `x-ai/grok-imagine-video`
- `x-ai/grok-imagine-video-1.5`
- `x-ai/grok-imagine-video-1.5-20260719`
- `x-ai/grok-imagine-video-20260512`
