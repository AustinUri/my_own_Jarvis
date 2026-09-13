# JARVIS v27 Architecture Notes

## Design principle

One local JARVIS brain, many specialist identities and many surfaces. A specialist is a role/configuration with a focused domain and allowed tools; it is **not** a separate copy of the model.

```text
Voice / Text / Phone
        |
        v
  JARVIS Orchestrator
        |
        +-- Agent Mesh router (47 registered identities)
        +-- Resource Governor
        +-- Tool / permission policy
        |
        v
  Shared LM Studio Qwen + local/free tools
        |
        +-- Control Center / Surface Dock
        +-- Windows actions
        +-- Web research
        +-- Phone companion
```

## Open-source ideas used as inspiration

- Ruflo: specialist/swarm registry, coordination, lifecycle and metrics concepts. **Not a v27 runtime dependency.**
- Microsoft Agent Framework / LangGraph: orchestration, handoff/fan-out and durable workflow concepts for future independent specialist execution.
- GridStack / spatial workspace ideas: future richer panel placement and persistence. v27 keeps the existing zero-build grid runtime for reliability.
- Three.js / React Three Fiber: future deeper spatial visualization. v27 uses a lightweight custom canvas core so no Node build is required at runtime.
- WebView2 / Windows capture / PowerToys workspace patterns: future native-app and managed-browser surfaces. v27 Surface Dock is intentionally limited to normal HTTP(S) web surfaces.

No paid service is required by these v27 foundations.

## Why v27 does not run 47 agents concurrently

The target PC has finite RAM/VRAM. The local Qwen model is shared. Forty-seven simultaneous generations would add contention with no useful benefit. v27 therefore separates:

- **registered identities**: 47
- **selected/active identities for a request**: normally <= 6
- **expensive model generation concurrency**: hard ceiling <= 2

The next step after v27 stability testing is to make selected specialists independently executable in a bounded task pool, not to spawn all of them.

## Surface decision model

The future Surface Manager should choose among:

1. Native JARVIS widget/card
2. Embedded ordinary website
3. Managed browser surface
4. Native Windows window positioned beside/over the dashboard
5. External/full-screen application

User corrections should become persistent rules, for example:

- “Always open this site in the Surface Dock.”
- “Never embed this app.”
- “Put VS Code on monitor 2.”
- “When I ask about F1, show standings next to the answer.”

v27 implements the first explicit website Surface Dock step and the policy boundary needed to evolve toward this safely.
