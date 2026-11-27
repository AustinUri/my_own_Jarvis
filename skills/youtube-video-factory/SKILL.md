---
name: youtube-video-factory
description: Generate original English Nori and Blink cartoon drafts locally with a reusable character rig, Piper, FFmpeg and per-scene review.
---
# YouTube Video Factory

Ask JARVIS “Create an English kids animation draft” or “תכין פרק חדש של נורי ובלינק”. On the Windows worker these commands run the local skill and return the finished preview path. The episode generator also runs directly from the repository.

```powershell
python -m core.capabilities.youtube_autopilot.skill_runtime status
python -m core.capabilities.youtube_autopilot.skill_runtime create-draft --backend auto --render
python -m core.capabilities.youtube_autopilot.skill_runtime audit-draft --draft-id <generated-id>
```

Use `core.capabilities.youtube_autopilot.skill_runtime.execute` for the four skill actions `capabilities`, `status`, `create-draft` and `audit-draft`. By default the skill stores scripts under `var/youtube_autopilot/creative_drafts/`, movies and narration under `renders/` inside that directory, and audit results under `reports/`. Use `--root` for an isolated library and its voice configuration.

## Production

1. With `--backend auto`, the writer tries the configured loopback LM Studio endpoint. Qwen plans each shot and writes the dialogue. The action selected for the rig supplies the narrator's action line. The factory checks titles, narration and staged action sequences against the local library. Offline mode chooses from thirteen original six-beat plots and stops when they are exhausted. Explicit `--backend local-ai` reports a failed generation if the model is unavailable or its plans fail validation.
2. Every beat specifies a setting, framing, character action and one featured prop. The stage draws two original jointed characters and the selected prop on a painted set. Carrying uses a hand attachment. Tracking and close shots change the composition. The vocabulary is defined in `visual_contract.py`; extend the actual staging and its tests when adding words to that contract.
3. Install Pillow, make FFmpeg and ffprobe available, and configure `piper_bin` and `piper_model` in the local runtime config. Each English Piper recording sets its own scene length. The encoder appends a brief reaction hold and cuts on a video frame boundary.
4. `create-draft --render` fits captions and checks the encoded MP4. `render_rejected` identifies an output that failed technical review. `audit-draft` rechecks the stored movie against its storyboard, prop art and narration timeline. Review motion, prop contact, facial acting, pacing, voice and story on the actual movie.

The local draft worker can repeat this process while the PC is running. For a single unattended cycle:

```powershell
python -m core.capabilities.youtube_autopilot.creative_factory worker --backend auto --render --max-cycles 1
```

Publication approval stays with the owner. This skill has no upload, OAuth, scheduling or publishing action. Keep the legacy publisher, its queue and its credentials outside this workflow. Generated media, voice models and runtime state belong in ignored `var/`. See [the creative review criteria](references/QUALITY_BAR.md).
