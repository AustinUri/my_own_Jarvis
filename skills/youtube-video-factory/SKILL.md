---
name: youtube-video-factory
description: JARVIS first-party local kids episode storyboarding, narrated draft generation and strict publication QA. Never auto-upload from this skill.
---
# YouTube Video Factory — JARVIS First-Party Skill

## Status and scope
This skill is **project-owned, tracked in Git**, and uses the installed code under
`core/capabilities/youtube_autopilot/`. It is a **draft-production skill**, not
proof of professional animation. The current renderer is procedural clip-art;
its output must NOT be published until replaced and creatively reviewed.

## Natural-language triggers
- "JARVIS, create a new original Nori & Blink episode"
- "Create an English kids animation draft"
- "תכין פרק חדש של נורי ובלינק"
- "תייצר סרטון ילדים מקורי ליוטיוב"

## Execution boundary
Import `core.capabilities.youtube_autopilot.skill_runtime.execute` and call
only its explicit actions: `capabilities`, `status`, `create-draft`, `audit-draft`.
This skill MUST NEVER call `youtube_autopilot.enable`, `run-once`, `worker`,
`youtube_api.upload` or `authorize` as a generic agent action.

Commands in the repository root:

```powershell
python -m core.capabilities.youtube_autopilot.skill_runtime status
python -m core.capabilities.youtube_autopilot.skill_runtime create-draft --backend offline
python -m core.capabilities.youtube_autopilot.skill_runtime create-draft --backend local-ai --render
```

The `local-ai` backend requires an already-running LM Studio Qwen model and
zero paid API tokens. Offline fallback has only 12 original story templates,
then safely exhausts rather than repeating stories.

## Pipeline
1. Original plot and narration written by local AI or finite offline fallback.
2. Distinct six-beat storyboard; check character roles, action and prop alignment.
3. Generate English speech with local Piper.
4. Render an MP4 preview with FFmpeg, into ignored `var/` runtime state.
5. Run mechanical video QA **and** storyboard visual audit.
6. Human evaluates actual animation, sound, story and originality.
7. **BLOCK** publication. Existing YouTube Autopilot's separate publisher remains
   outside this Skill; not integrated into an approved release process.

## Quality constraints
- Do not treat motion-score or a valid MP4 as evidence of child-friendly production quality.
- Story objects must appear visually when mentioned; weak scene labels alone do not prove rendering.
- Stable, original designs; use only licensed assets.
- The current procedural renderer is below the publication bar.
- Final deployment requires explicit release process and child-directed-content settings.

## Project state and privacy
- Code and this Skill live in Git. Generated renders, tokens, queue, voice models,
  local runtime JSON and drafts live under `var/youtube_autopilot/`, **ignored by Git**.
- No secrets, voice files, local videos, or user/customer data in Git.
- A worker generates only while the PC is on; pre-scheduled YouTube videos can
  publish independently after upload, but the local model cannot run with PC off.
