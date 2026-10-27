export type ProjectType =
  | "advertisement"
  | "product"
  | "architecture"
  | "engineering"
  | "cartoon"
  | "educational"
  | "documentary"
  | "story"
  | "social_media"
  | "explainer"
  | "custom";

export type QualityMode = "local" | "balanced" | "quality" | "max_quality";

export type AspectRatio = "16:9" | "9:16" | "1:1" | "4:5";

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  project_type: ProjectType;
  status: string;
  prompt: string;
  script?: string;
  target_duration: number;
  aspect_ratio: AspectRatio;
  quality_mode: QualityMode;
  voice_language?: string;
  voice_accent?: string;
  voice_name?: string;
  voice_emotion?: string;
  voice_speed: number;
  include_subtitles: boolean;
  include_music: boolean;
  include_sfx: boolean;
  output_path?: string;
  thumbnail_path?: string;
  scene_bible?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Scene {
  id: string;
  project_id: string;
  generation_id?: string;
  scene_number: number;
  title: string;
  description?: string;
  duration_seconds: number;
  status: "pending" | "generating" | "completed" | "failed";
  shot_type?: string;
  camera_movement?: string;
  environment?: string;
  lighting?: string;
  voice_over?: string;
  image_prompt?: string;
  video_prompt?: string;
  negative_prompt?: string;
  music_mood?: string;
  sfx_description?: string;
  transition_in?: string;
  transition_out?: string;
  continuity_notes?: string;
  provider_used?: string;
  image_path?: string;
  video_path?: string;
  audio_path?: string;
  retry_count: number;
  error_message?: string;
}

export interface Generation {
  id: string;
  project_id: string;
  status:
    | "QUEUED"
    | "ANALYZING"
    | "STORYBOARDING"
    | "GENERATING_IMAGES"
    | "GENERATING_VIDEO"
    | "GENERATING_VOICE"
    | "SYNCING"
    | "COMPOSITING"
    | "ADDING_SUBTITLES"
    | "QUALITY_CHECK"
    | "EXPORTING"
    | "COMPLETED"
    | "FAILED"
    | "CANCELLED";
  current_step?: string;
  progress_percent: number;
  total_scenes: number;
  completed_scenes: number;
  failed_scenes: number;
  error_message?: string;
  estimated_cost?: number;
  actual_cost?: number;
  output_path?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface Provider {
  id: string;
  name: string;
  display_name: string;
  provider_type: "llm" | "video" | "image" | "tts" | "stt";
  description?: string;
  website_url?: string;
  is_enabled: boolean;
  supports_local: boolean;
  capabilities?: string[];
}

export interface ProviderAccount {
  id: string;
  provider_id: string;
  account_name: string;
  key_hint?: string; // MASKED (e.g. ************ABCD)
  is_active: boolean;
  is_healthy: boolean;
  priority: number;
  allow_paid_usage: boolean;
  daily_spend_limit?: number;
  monthly_spend_limit?: number;
  daily_request_count: number;
  success_count: number;
  failure_count: number;
  avg_latency_ms?: number;
  last_used_at?: string;
  last_success_at?: string;
  last_error_at?: string;
  last_error_message?: string;
  cooldown_until?: string;
  created_at: string;
}

export interface HardwareInfo {
  os_name: string;
  os_version: string;
  arch: string;
  cpu_model: string;
  cpu_cores: number;
  ram_gb: number;
  is_apple_silicon: bool;
  gpu_name?: string;
  has_cuda: boolean;
  has_mps: boolean;
  available_disk_gb: number;
  python_version: string;
  ffmpeg_available: boolean;
  ffmpeg_version?: string;
  comfyui_running: boolean;
  recommended_config: string;
}

export interface Asset {
  id: string;
  project_id?: string;
  filename: string;
  original_filename: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  asset_type: string;
  purpose: string;
  width?: number;
  height?: number;
  created_at: string;
}
