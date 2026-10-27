# Local AI Video Production Studio — Architecture

## 1. System High-Level Architecture

```
                                 [ User Browser / Next.js 14 UI ]
                                                │
                                    (REST / JSON & WebSockets)
                                                ▼
                                [ FastAPI Application Server ]
                                                │
            ┌───────────────────────────────────┼───────────────────────────────────┐
            ▼                                   ▼                                   ▼
 [ Secure Credential Service ]        [ AI Storyboard Engine ]             [ FFmpeg Media Pipeline ]
   • Fernet 256-bit Encryption          • Scene Bible Generator              • Scene Stitching & Cuts
   • Key Masking (last 4 chars)         • Prompt Expander / Pacing           • Voice-Over & Music Ducking
   • In-Memory Transient Decrypt        • Multi-Genre Presets                • Subtitles (SRT/VTT Burn-In)
            │                                   │                            • Aspect Ratio (16:9 / 9:16)
            ▼                                   ▼                                   ▼
 [ Smart Provider Router ]            [ Scene Manager & Checkpoint ]        [ Final Render Export ]
   • Multi-Account Auto-Rotation        • Per-Scene State (`state.json`)      • Master H.264/H.265 MP4
   • Error Classification (429/401)     • Resume Interrupted Jobs             • Web Faststart Streaming
   • Scoring & Hardware Detection       • Reference Media Propagator
            │
            ├──────────────────────┬──────────────────────┬──────────────────────┐
            ▼                      ▼                      ▼                      ▼
  [ Local Inference ]       [ Google Gemini ]      [ Groq LPU ]          [ Fal / Replicate ]
    • ComfyUI AnimateDiff     • Multimodal Script    • Fast LLM & STT      • High-Motion Video
    • macOS Native TTS        • Visual Breakdown     • Instant Whisper     • Kling / Wan 2.1
    • Local Whisper STT
```

## 2. Provider Router Scoring Function

The provider router selects the optimal execution route according to:

$$\text{Score} = (\text{Quality} \times \text{Availability} \times \text{Quota} \times \text{Reliability}) + \text{PriorityBoost} - \text{CostPenalty} - \text{FailurePenalty}$$

Where:
- **Quality Mode**:
  - `local`: Local providers get 3.0× boost; remote paid providers incur heavy penalties.
  - `balanced`: Local-first, with zero-cost or budget cloud fallbacks.
  - `quality`: Favors high quality-rated models within user spend limits.
- **Availability**: Dynamically degrades if an account recently reported errors.
- **Cooldown**: Rate-limited accounts (`HTTP 429`) enter a 15-minute cooldown and are bypassed until the window expires.
- **Failover**: If Account A fails, the router seamlessly advances to Account B, then Account C, then next provider.

## 3. Video Pipeline State Machine

Every generation job transitions sequentially:

1. `QUEUED`: Enqueued in Celery or async background loop.
2. `ANALYZING`: Project prompt & reference image analysis.
3. `STORYBOARDING`: Scene list, duration calculations, and visual prompts generated.
4. `GENERATING_IMAGES`: Keyframe reference generation.
5. `GENERATING_VIDEO`: Scene clips rendered sequentially.
6. `GENERATING_VOICE`: Spoken narration synthesized with chosen voice profile.
7. `SYNCING`: Narration duration synchronized with scene runtimes.
8. `COMPOSITING`: Scene concatenation via FFmpeg.
9. `ADDING_SUBTITLES`: Whisper STT alignment and subtitle burn-in.
10. `QUALITY_CHECK`: Container inspection for resolution and frame integrity.
11. `EXPORTING`: Final encoding with `+faststart` metadata.
12. `COMPLETED`: Master video ready for download and playback.
