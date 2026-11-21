# Video Factory — review of the supplied Manus prototype

**Reviewed:** 21 November 2026
**Input:** `youtube_cartoon_upgrade.zip` provided by the project owner.
**Decision:** technical reference / experimental prototype; **not a drop-in replacement for JARVIS**.

## What the ZIP contains

- `renderer.py` — Pillow + FFmpeg local frame renderer for Nori, Blink, a seedling and simple backgrounds, blinking, limb movement, glow and parallax cues.
- `quality.py` — schema/word-count checks plus `ffprobe` checks for video and narration audio.
- `build_episode.py` — single-file command-line preview tool.
- `episode.json` and `episode_prompt.txt` — an educational counting / seed-growing example and a constrained generative prompt.
- `tests/test_quality.py` — four small content-validator tests.
- `requirements.txt` — Pillow dependency only.

The ZIP also contains a generated `tests/__pycache__/` file, which is not source code and should never be committed.

## Why it must NOT overwrite JARVIS

1. **Schema mismatch.** The main JARVIS episode path uses `scenes[].kind/caption/narration`, whereas the Manus prototype requires `scenes[].visual/action/setting/caption/narration`, `learning_goal` and `lesson`. Dropping in the new `renderer.py`/`quality.py` would break or bypass compatibility with `episodes.py`, `creative_factory.py` and other callers.
2. **Narrow animation vocabulary.** The prototype draws a fixed seedling growth arc: `seed`, `water`, `one_leaf`, `two_leaves`, `three_leaves`, `flower`, `celebrate`. A new Qwen story about a boat, lantern or snail would not automatically gain matching animation assets or meaningful character action.
3. **Voice is optional for preview.** Supplying a narration WAV is manual and scene timing is not intrinsically synchronized. It is not a complete automated speech/render pipeline.
4. **Limited QA.** The validator checks fields and a short banned-word list; the media audit checks technical properties. Neither proves character performance, educational accuracy, emotional engagement, visual correctness, licensed/original assets or suitability for child audiences.
5. **Not wired into JARVIS.** No registration with the installed `activator`/`registry`/`router`, creative queue, quality gate, Piper controller or upload system is included.

## Ideas worth transferring into the active design

- One canonical, **versioned** episode contract: goal, visual objects, physical actions, character state, shot/timing and narration; not separate schemas competing with one another.
- Validate every **requested visible object and action** against real renderer capabilities; reject or replan unsupported scenes rather than drawing a substitute and calling it a success.
- Maintain persistent story props across shots and use meaningful animation (interaction, facial expressions, camera work, prop transitions), not pixel movement scores alone.
- Time narration per scene; avoid cutting or blindly stretching speech.
- Require an audiovisual human creative review and explicit release approval; technical QA alone must not authorize posting.
- Keep generation local/free where feasible; store media and credentials only in ignored runtime locations.

## Suggested next engineering sequence

1. Add contract tests to cover old and new episode schemas without breaking the current factory.
2. Build a schema adapter and a capability table for assets/actions, with failure on unsupported visual requests.
3. Prototype a small reusable skeletal/rigged 2D character engine with layered expressions and actual object interaction.
4. Generate two unrelated story genres (e.g. moving a leaf boat and helping a moth) and inspect the rendered scenes *manually*. Both must exhibit distinctly relevant visuals.
5. Add rendering/audio/caption QA and only later connect an opt-in release workflow.

**Do not claim this Manus prototype is integrated or that it fixes cartoon quality.** It has been reviewed and documented only.
