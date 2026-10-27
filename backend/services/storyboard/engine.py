"""AI Storyboard Engine.

Transforms natural language instructions, scripts, or rough notes into a
comprehensive structured storyboard with scene durations, camera language,
lighting, visuals, narration, audio mood, and continuity bible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class ScenePlan:
    scene_number: int
    title: str
    description: str
    duration_seconds: float
    shot_type: str          # aerial, wide, medium, close-up, extreme-close-up, hero
    camera_movement: str    # static, slow-push, pan-left, dolly-in, orbit, crane
    environment: str
    lighting: str
    voice_over: str
    image_prompt: str
    video_prompt: str
    negative_prompt: str
    music_mood: str
    sfx_description: str
    transition_in: str
    transition_out: str
    continuity_notes: str


@dataclass
class Storyboard:
    title: str
    total_duration: float
    scenes: List[ScenePlan]
    script: str
    scene_bible: dict = field(default_factory=dict)
    voice_script: str = ""
    music_mood_overall: str = "cinematic"


class StoryboardEngine:
    """Generates structured storyboards and scene continuity bibles using LLM."""

    PRESET_INSTRUCTIONS = {
        "advertisement": (
            "Focus on product hero shots, luxury lighting, brand identity, snappy pacing, "
            "clear call-to-action (CTA), and confident commercial voice-over."
        ),
        "product": (
            "Focus on product consistency, 360-degree rotation, macro close-ups, "
            "premium studio rim lighting, component details, and sleek modern aesthetic."
        ),
        "architecture": (
            "Focus on exterior drone establishers, interior walkthroughs, marble/glass/wood textures, "
            "natural golden hour sunlight, architectural scale, and smooth cinematic dollys."
        ),
        "engineering": (
            "Focus on exploded technical views, precise component assembly/disassembly, "
            "labeled parts visualization, mechanical movement, and clean studio contrast."
        ),
        "cartoon": (
            "Focus on expressive character animation, vivid color palette, emotional beats, "
            "dynamic camera angles, consistent character attire, and dialogue rhythm."
        ),
        "educational": (
            "Focus on structured instructional segments, visual diagrams/infographics, "
            "clear step-by-step progression, and engaging explanatory narration."
        ),
        "social_media": (
            "Focus on 9:16 vertical composition, strong first 2-second hook, fast cuts, "
            "bold visual contrasts, and punchy captions."
        ),
    }

    def __init__(self, provider_router: ProviderRouter):
        self.router = provider_router

    async def generate_storyboard(
        self,
        prompt: str,
        project_type: str = "advertisement",
        target_duration: int = 60,
        aspect_ratio: str = "16:9",
        voice_language: str = "en",
        reference_notes: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Storyboard:
        """Prompt the LLM router to generate a structured storyboard."""
        # Calculate target scene count (roughly 5 to 7 seconds per scene)
        approx_scene_duration = 6.0
        target_scene_count = max(3, min(30, round(target_duration / approx_scene_duration)))

        system_prompt = self._build_system_prompt(
            project_type=project_type,
            target_duration=target_duration,
            scene_count=target_scene_count,
            aspect_ratio=aspect_ratio,
        )

        user_prompt = self._build_user_prompt(
            prompt=prompt,
            project_type=project_type,
            target_duration=target_duration,
            reference_notes=reference_notes,
        )

        result = await self.router.route_text_generation(
            prompt=user_prompt,
            system_prompt=system_prompt,
            quality_mode="balanced",
            job_id=job_id,
        )

        if not result.success:
            logger.warning("storyboard_llm_failed_using_heuristic_generator", error=result.error_message)
            return self._generate_heuristic_storyboard(prompt, project_type, target_duration)

        raw_text = result.metadata.get("text", "") if result.metadata else ""
        try:
            return self._parse_json_storyboard(raw_text, target_duration)
        except Exception as e:
            logger.warning("storyboard_json_parse_failed_using_heuristic", error=str(e), raw=raw_text[:300])
            return self._generate_heuristic_storyboard(prompt, project_type, target_duration)

    def _build_system_prompt(self, project_type: str, target_duration: int, scene_count: int, aspect_ratio: str) -> str:
        preset_guide = self.PRESET_INSTRUCTIONS.get(project_type, "Create an engaging, high quality video.")
        return f"""You are an elite video director and master AI prompt engineer.
Category: {project_type}.
Directive: {preset_guide}
Format: {aspect_ratio} aspect ratio. Total duration: {target_duration} seconds ({scene_count} sequential scenes).

You must return ONLY a raw JSON object (valid RFC 8259, no markdown quotes, no commentary):
{{
  "title": "Creative Title",
  "script": "Full master narration script",
  "voice_script": "Pure spoken narration text without any scene markers or directions",
  "music_mood_overall": "e.g. ambient luxury, cinematic orchestral, upbeat electronic",
  "scene_bible": {{
    "visual_style": "Consistent photographic or illustrative style",
    "color_palette": "Primary and accent color tones",
    "subjects": "Consistent character, product, or architectural details to maintain across all scenes"
  }},
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene 1 Headline",
      "description": "Visual scene breakdown",
      "duration_seconds": 6.0,
      "shot_type": "aerial | wide | medium | close-up | extreme-close-up | hero",
      "camera_movement": "slow-push | pan-left | pan-right | orbit | dolly-in | static | crane",
      "environment": "Physical environment, background, setting",
      "lighting": "Studio rim, golden hour, volumetric rays, neon, soft diffused",
      "voice_over": "Narration specifically spoken during this scene",
      "image_prompt": "Ultra-detailed descriptive prompt for a photorealistic/stylized keyframe",
      "video_prompt": "Motion-focused prompt describing camera movement and subject action",
      "negative_prompt": "blurry, low quality, distorted, jitter, watermarks, text artifacts",
      "music_mood": "Mood during this clip",
      "sfx_description": "Ambient or foley sound effects",
      "transition_in": "cut | dissolve | fade",
      "transition_out": "cut | dissolve | fade",
      "continuity_notes": "Specific visual attributes matching previous scene"
    }}
  ]
}}"""

    def _build_user_prompt(self, prompt: str, project_type: str, target_duration: int, reference_notes: Optional[str]) -> str:
        notes_clause = f"\nUser References & Constraints:\n{reference_notes}" if reference_notes else ""
        return (
            f"User Prompt: {prompt}\n"
            f"Project Category: {project_type}\n"
            f"Target Runtime: {target_duration} seconds\n"
            f"{notes_clause}\n"
            "Generate the comprehensive scene-by-scene storyboard JSON now:"
        )

    def _parse_json_storyboard(self, raw_text: str, target_duration: int) -> Storyboard:
        cleaned = raw_text.strip()
        # Strip markdown fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned)
            cleaned = re.sub(r"```$", "", cleaned).strip()

        # Find first '{' and last '}'
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1:
            cleaned = cleaned[start_idx : end_idx + 1]

        data = json.loads(cleaned)
        scenes: List[ScenePlan] = []
        for s in data.get("scenes", []):
            scenes.append(
                ScenePlan(
                    scene_number=int(s.get("scene_number", len(scenes) + 1)),
                    title=str(s.get("title", f"Scene {len(scenes) + 1}")),
                    description=str(s.get("description", "")),
                    duration_seconds=float(s.get("duration_seconds", 5.0)),
                    shot_type=str(s.get("shot_type", "medium")),
                    camera_movement=str(s.get("camera_movement", "slow-push")),
                    environment=str(s.get("environment", "")),
                    lighting=str(s.get("lighting", "cinematic")),
                    voice_over=str(s.get("voice_over", "")),
                    image_prompt=str(s.get("image_prompt", "")),
                    video_prompt=str(s.get("video_prompt", "")),
                    negative_prompt=str(s.get("negative_prompt", "blurry, low quality")),
                    music_mood=str(s.get("music_mood", "ambient")),
                    sfx_description=str(s.get("sfx_description", "")),
                    transition_in=str(s.get("transition_in", "cut")),
                    transition_out=str(s.get("transition_out", "cut")),
                    continuity_notes=str(s.get("continuity_notes", "")),
                )
            )

        if not scenes:
            raise ValueError("No scenes found in LLM output.")

        total_dur = sum(sc.duration_seconds for sc in scenes)
        voice_script = data.get("voice_script") or " ".join(s.voice_over for s in scenes if s.voice_over)

        return Storyboard(
            title=data.get("title", "AI Video Project"),
            total_duration=round(total_dur, 2),
            scenes=scenes,
            script=data.get("script", voice_script),
            scene_bible=data.get("scene_bible", {}),
            voice_script=voice_script,
            music_mood_overall=data.get("music_mood_overall", "cinematic"),
        )

    def _generate_heuristic_storyboard(self, prompt: str, project_type: str, duration: int) -> Storyboard:
        """Deterministic heuristic storyboard generator when offline or if LLM fails."""
        scene_count = max(3, min(10, round(duration / 6.0)))
        scene_dur = round(duration / float(scene_count), 1)

        scene_templates = [
            ("Establishing Hook", "aerial", "drone-push", "Golden hour cinematic opening showcasing scale and atmosphere."),
            ("Subject Reveal", "wide", "dolly-in", "Dramatic unveil of the primary subject with rim lighting."),
            ("Feature Focus", "close-up", "slow-pan", "Detailed close-up highlighting textures, precision engineering, and craft."),
            ("Dynamic Action", "medium", "orbit", "Dynamic action shot emphasizing motion, functionality, and performance."),
            ("Atmospheric Context", "wide", "static", "Atmospheric environment shot reinforcing the premium mood."),
            ("Hero Climax", "hero", "crane-up", "Hero climax view with striking lighting and iconic silhouette."),
            ("Closing & Call to Action", "medium", "slow-pullback", "Polished closing frame with elegant brand framing."),
        ]

        scenes: List[ScenePlan] = []
        for i in range(scene_count):
            tpl = scene_templates[i % len(scene_templates)]
            sc_num = i + 1
            scenes.append(
                ScenePlan(
                    scene_number=sc_num,
                    title=f"{tpl[0]} ({prompt[:30]}...)",
                    description=tpl[3],
                    duration_seconds=scene_dur,
                    shot_type=tpl[1],
                    camera_movement=tpl[2],
                    environment="High-end cinematic environment",
                    lighting="Soft volumetric lighting with high dynamic range",
                    voice_over=f"Experience the standard of excellence in {prompt[:40]}.",
                    image_prompt=f"Cinematic master shot of {prompt}, {tpl[3]}, 8k resolution, photorealistic, Unreal Engine 5 render style",
                    video_prompt=f"Smooth {tpl[2]} camera movement, {tpl[3]} of {prompt}, cinematic 24fps motion",
                    negative_prompt="blurry, distorted, artifacts, low resolution",
                    music_mood="Inspiring cinematic soundtrack",
                    sfx_description="Subtle ambient breeze and whoosh",
                    transition_in="cut" if sc_num > 1 else "fade",
                    transition_out="cut",
                    continuity_notes="Maintain consistent lighting and color temperature throughout",
                )
            )

        full_vo = " ".join(s.voice_over for s in scenes)
        return Storyboard(
            title=f"{project_type.capitalize()} — {prompt[:30]}",
            total_duration=float(duration),
            scenes=scenes,
            script=full_vo,
            scene_bible={
                "visual_style": "Photorealistic cinematic",
                "color_palette": "Deep contrast, natural warmth",
                "subject": prompt,
            },
            voice_script=full_vo,
            music_mood_overall="cinematic",
        )
