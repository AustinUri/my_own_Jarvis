# Corrected validation and priorities — 2026-11-20

Base: unified core merge 2da73da with phone, gaming guard and in-call feedback patches. Action Center and revenue-first patches were not installed. Visual work and generic booking demo are paused. Do not apply those patches as prerequisites for this checkpoint.

- Android keypad: local feedback works; remote DTMF receipt, microphone and WhatsApp direction pending field validation. Samsung fallback was observed during a package update; don't update during calls.
- Gaming guard: partial; VRAM release not demonstrated. Inspect actual `lms ps --json` and GPU usage after all jobs are idle. No automatic process killing or unloading active jobs.
- Primary agent: migration not installed/validated; keep existing behavior until tested. Qwen CLI previously worked; Gemma end-to-end not verified. Test separately with the user's known working local `cll` launcher, no paid fallback.
- Skills: 157 harvested previously, not 157 reviewed/executed. Audit each exact skill, then review and sandbox individual approved skills.
- FreeLLMAPI: no active adapter found in reviewed source, installation outside repo unknown. Never send personal/business data to unapproved fallbacks. Caveman paused.
- Phone Intelligence: incomplete/nonworking as reported. Inspect Oracle caller identity and contact write path; use authenticated idempotent sync, explicit editing precedence, pending retry and no blanket address-book upload. Back up database and test with fake contact first. Do not infer content summaries from call logs. Actual call transcript requires lawful, supported audio capture and consent. Keep metadata summaries distinct.
- Full two-way phone voice: not verified ever. Prioritize Hebrew plus English contact names; evaluate local multilingual Whisper path, push-to-talk, Hebrew TTS and response audio. Do not require English speech or change system keyboard. Garmin partial. Wake word/answer-for-user lower priority.
- Phone camera: explicit foreground capture, one photo first through authenticated Device Bus, bounded size/timeout, user-visible controls, no background streaming or persistence by default. Test PC-off behavior and model availability; model processing can require PC on. Real-time video later.
- CAD: STL primitive export in this checkpoint; STEP/parametric CAD via a real CAD kernel later. Physical/thermal solver not implemented. No safety/strength claims from primitive geometry.
- Business: Claude-led per-business websites, Kapso sandbox, PostHog per-site opt-in, site audits and human-approved proposals. This checkpoint includes a workflow, not a deployed business product. Trend-product research via a verified skill; no automatic purchases or postings.
- Proactive updates: Oracle event queue and opt-in spoken app notices first; real inbound calls require a supported telephony/VoIP path, provider credentials, quiet hours and cost/permissions. No phone call integration claimed.
