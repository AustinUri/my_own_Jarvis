# JARVIS Engineering Context

Read this before changing the repository.

## Core architecture
- Oracle is the always-on cloud core and shared-memory/device-bus coordinator.
- `uri-windows` is the Windows worker with LM Studio / local Qwen.
- `uri-s25` is the Android companion.
- The Android phone must keep working when the PC is off for cloud-supported features.
- Phase 6 requires OS portability: keep platform-independent core separate from Windows/Linux adapters.

## Verified phone behavior — do not regress
- Natural-language contact calling -> Contacts -> Device Bus `phone.call` -> carrier call.
- Real dialer: incoming identity, Answer/Reject, Hang Up, Mute, Speaker, Hold, Add Call, Switch, Merge, conference/participants.
- Incoming caller announcement works.
- Unlock missed-call briefing works.
- Caller memory exists on Oracle.
- Phone connects through Oracle Device Bus; do not reintroduce the old numeric pairing UI.

## AI / cost policy
- Default cost is ₪0.
- LM Studio / local Qwen is the preferred local inference backend.
- Claude Code may use LM Studio's Anthropic-compatible endpoint.
- Never introduce a paid API or paid telephony dependency without explicit user approval.
- Never leak or print secrets, bootstrap tokens, `.env`, cloud tokens, or SSH private keys.

## Git discipline
- Always inspect `git status --short` before substantial edits.
- Never stage guessed file lists.
- Review `git diff` / `git diff --cached`.
- Never commit or push automatically unless the user explicitly requests it.
- Do not delete unrelated working-tree changes.

## Engineering discipline
- Inspect actual current source before patching.
- Prefer the smallest change that preserves proven behavior.
- Run targeted tests/builds and report failures accurately.
- Do not claim success from static reasoning alone.
- For Android changes, compile `android_companion` before calling the change complete.
- For cloud changes, run Python compile/import checks before restart.

## Claude Code roles
- **Tutor**: read-only; teach exact JARVIS code paths using real files/functions.
- **Review**: read-only; find bugs/regressions/security/concurrency/dead code.
- **Architecture**: read-only; map components and OS-portability boundaries.
- **Test**: read-only unless user explicitly asks to fix.
- **Fix**: may edit locally on PC, run tests, and summarize diff; no auto commit/push.
- Phone-triggered Claude tasks are read-only by default.
