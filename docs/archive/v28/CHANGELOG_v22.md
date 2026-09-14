# v22 changes

- Replaced Ollama integration with a generic OpenAI-compatible provider layer targeting LM Studio by default.
- Added Qwen3.5 9B setup path with stable API identifier `jarvis-qwen`.
- Added real recent-turn conversation memory.
- Added model-driven tool calling with a controlled ToolRegistry.
- Added a policy layer for answer/suggest/execute behavior.
- Prevents public web search from substituting for unsupported personal/private data.
- Added arbitrary domain opening (`open chess.com`).
- Added AI provider settings and a Test AI button.
- Added setup/doctor/run PowerShell scripts.
- Kept the old deterministic parser only as an emergency degraded fallback.
- Phone companion intentionally deferred.
