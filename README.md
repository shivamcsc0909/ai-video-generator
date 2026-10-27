# Local AI Video Production Studio

A modular, production-grade, local-first AI video generation platform designed for Apple Silicon (macOS) and modern workstations. The studio takes text instructions, scripts, reference images, or rough notes and transforms them through a full production pipeline:

$$\text{Script} \longrightarrow \text{Storyboard} \longrightarrow \text{Scenes} \longrightarrow \text{Clips} \longrightarrow \text{Voice} \longrightarrow \text{Sync} \longrightarrow \text{Compositing} \longrightarrow \text{Subtitles} \longrightarrow \text{QC} \longrightarrow \text{Master MP4}$$

---

## Key Features

1. **Hardware-Aware Local-First Execution**:
   - Tuned for Apple Silicon (M1/M2/M3/M4) unified memory and MPS acceleration.
   - Intelligent degradation: runs lightweight local models on 16 GB unified RAM, with seamless cloud API fallback.

2. **Secure Provider Management (Never In Source Code)**:
   - Dedicated **AI Providers** web interface (`/settings/providers`).
   - Server-side Fernet 256-bit symmetric encryption at rest for all API keys.
   - Keys are masked in all API responses (`************ABCD`) and never logged or exposed to the browser.

3. **Intelligent Multi-Account API Rotation & Failover**:
   - Supports multiple accounts/keys per provider (e.g., *Gemini Personal*, *Gemini Work*, *Groq Fast*).
   - Automatically detects rate limits (`429`) and quota exhaustion, places the limited account on cooldown, and smoothly rotates to the next available account.

4. **Comprehensive Video Modes**:
   - **Commercial Advertisements**: Hero shots, product showcase, brand identity, and call-to-action.
   - **Product & Engineering**: Exploded technical assembly/disassembly views, component reveals, and macro lighting.
   - **Architecture & Interiors**: Drone push establishers, interior walkthroughs, and material textures.
   - **Cartoon & Character**: Consistent character bibles, emotional pacing, and animated continuity.
   - **Explainer & Educational**: Structured instructional pacing with infographics and subtitles.

5. **Audio-Video Synchronization & Subtitle Engine**:
   - Multilingual voice synthesis (English, Hindi, Hinglish, Spanish, French, German, Japanese, etc.).
   - Scene timeline auto-balancing to match spoken cadence without audio distortion.
   - Automated Whisper transcription with burned-in or WebVTT subtitle formatting.

6. **Automated Quality Checks & Granular Resume Support**:
   - Validates frames, bitrates, audio tracks, and container health.
   - Interrupted jobs can be resumed from the exact scene where they stopped without starting from scratch.

---

## Quickstart

### 1. Prerequisites
- macOS (Apple Silicon recommended) or Linux
- Python 3.11+
- Node.js 18+ and npm
- Docker (optional, for PostgreSQL & Redis containers)
- FFmpeg (`brew install ffmpeg`)

### 2. Install
```bash
./scripts/install.sh
```

### 3. Run Diagnostics
Verify dependencies, toolchains, permissions, and port availability:
```bash
./scripts/doctor.sh
```

### 4. Start Studio
```bash
./scripts/start.sh
```
- **Web UI**: [http://localhost:3000](http://localhost:3000)
- **API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Stop Studio
```bash
./scripts/stop.sh
```

---

## Project Monorepo Structure

```
ai-video-studio/
├── frontend/             # Next.js 14, Tailwind CSS, Lucide icons, Zustand
│   ├── app/              # App Router (Dashboard, New, Studio, Queue, Providers)
│   ├── components/       # UI navigation and shared components
│   ├── lib/              # Typed API client
│   └── types/            # TypeScript schemas
├── backend/              # FastAPI async backend
│   ├── api/v1/           # REST endpoints (auth, projects, generations, providers, scenes)
│   ├── core/             # Configuration, database, security, and WebSocket manager
│   ├── models/           # SQLAlchemy 2.0 ORM models
│   ├── providers/        # Base interface, Gemini, Groq, ComfyUI, Fal, Replicate, ElevenLabs
│   ├── services/         # Storyboard engine, scene manager, FFmpeg pipeline, provider router
│   └── workers/          # Background production pipeline workers
├── workflows/comfyui/    # Configurable ComfyUI workflow JSON templates
├── storage/              # Local storage: projects, scene assets, and final renders
├── scripts/              # install.sh, start.sh, stop.sh, doctor.sh
├── docker/               # PostgreSQL init scripts and container configs
├── tests/                # Automated pytest suite (encryption, scoring, storyboard, media)
├── docker-compose.yml    # Database and Redis infrastructure
└── requirements.txt      # Python dependencies
```

---

## Running the Automated Test Suite

```bash
pytest tests/ -v
```
All external network APIs are mocked; tests run fast and never consume API quotas.

---

## Security Model

- **At-Rest Encryption**: Every API key stored in the `provider_accounts` table is encrypted with Fernet symmetric cryptography.
- **Key Masking**: Any API response querying accounts only returns the `key_hint` (last 4 characters, e.g. `************B1C2`).
- **No Client Secrets**: API keys are decrypted in memory on the server only during outbound generation calls and are immediately discarded.
