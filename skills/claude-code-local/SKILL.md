# Claude Code Local — v0.3
Claude Code provides the repository-agent workflow. LM Studio provides local inference.

Runtime policy: on-demand.
- Start local server only when needed.
- Stop it after the task only if JARVIS started it.
- Models use an idle TTL.

Models:
- Qwen: code/tool-heavy primary.
- Gemma: tutor/alternate perspective.
- Dual: Qwen primary + Gemma critic.

This does not provide Anthropic Claude model intelligence for free.
