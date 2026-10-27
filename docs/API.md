# Local AI Video Production Studio — REST API Specification

Base URL: `http://localhost:8000/api/v1`

---

## 1. Authentication (`/auth`)

### `POST /auth/token`
Authenticate with credentials and obtain a JWT bearer token.
- **Form Data**: `username`, `password`
- **Response**: `{"access_token": "...", "token_type": "bearer"}`

### `POST /auth/register`
Create first local admin account.
- **Body**: `{"username": "admin", "password": "...", "email": "..."}`

### `GET /auth/me`
Fetch profile of currently authenticated user.

---

## 2. Projects (`/projects`)

### `GET /projects/`
List projects with pagination.
- **Query Params**: `skip=0`, `limit=50`

### `POST /projects/`
Create a new project.
- **Body**:
  ```json
  {
    "name": "Luxury Penthouse Commercial",
    "prompt": "Create a 60-second commercial for a modern penthouse...",
    "project_type": "advertisement",
    "target_duration": 60,
    "aspect_ratio": "16:9",
    "quality_mode": "balanced",
    "voice_language": "en",
    "voice_name": "Samantha",
    "include_subtitles": true,
    "include_music": true,
    "include_sfx": true
  }
  ```

### `GET /projects/{id}`
Retrieve project metadata and timeline settings.

### `POST /projects/{id}/generate-storyboard`
Generates structured scene breakdown with camera movements, durations, and narration.

---

## 3. Generations (`/generations`)

### `POST /generations/`
Schedule a full end-to-end video generation pipeline.
- **Body**: `{"project_id": "UUID", "quality_mode": "balanced"}`

### `GET /generations/{id}`
Fetch live job progress, current stage, and output video URL.

### `POST /generations/{id}/resume`
Resumes an interrupted generation from the last saved scene checkpoint.

### `POST /generations/{id}/cancel`
Cancels an ongoing generation job.

---

## 4. AI Providers (`/providers`)

### `GET /providers/`
List all supported providers and their declared capabilities.

### `GET /providers/accounts`
List configured accounts. Returns `key_hint` (masked, last 4 chars), NEVER the raw secret.

### `POST /providers/accounts`
Add a new provider credential. The key is encrypted immediately.
- **Body**:
  ```json
  {
    "provider_id": "UUID",
    "account_name": "Gemini Personal",
    "api_key": "AIzaSyD...",
    "priority": 1,
    "allow_paid_usage": false,
    "daily_spend_limit": 5.0
  }
  ```

### `POST /providers/accounts/{id}/test`
Tests connection and authentication with the external API or local service.

### `GET /providers/usage-summary`
Aggregated usage stats, error counts, and cooldown states across all configured accounts.

---

## 5. WebSockets (`/ws/{job_id}`)

Connect to `/ws/{job_id}` for real-time progress broadcasts:
```json
{
  "job_id": "...",
  "status": "GENERATING_VIDEO",
  "progress": 45.0,
  "step": "Scene 3/6 rendered",
  "scene_number": 3,
  "completed_scenes": 3
}
```
