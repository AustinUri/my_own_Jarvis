# JARVIS v28 Architecture

```text
                       ┌──────────────────────────┐
                       │       User / Sir         │
                       └────────────┬─────────────┘
                                    │
                     voice / text / camera / phone
                                    │
                  ┌─────────────────▼─────────────────┐
                  │          JARVIS CORE v28           │
                  │ Orchestrator + shared local model  │
                  └───────┬───────────┬───────────┬───┘
                          │           │           │
                    Speech Guard   Agent Mesh   Vision/HoloLab
                          │           │           │
               sentence-complete   shared LLM   Camera + hand tracking
                    playback         limits      + visual test engine
                          │
                          └──────────────────────────────┐
                                                         │
                     ┌───────────────────────────────────▼────────────┐
                     │         PRIVATE PHONE BRIDGE                  │
                     │ 127.0.0.1:8766 -> Tailscale Serve HTTPS      │
                     └──────────────────┬─────────────────────────────┘
                                        │
                 URL identity: https://<pc>.<tailnet>.ts.net
                 optional DNS socket target: 100.x.x.x
                                        │
                     ┌──────────────────▼──────────────────┐
                     │ Android Companion v28              │
                     │ OkHttp custom DNS + TLS hostname   │
                     │ ECDSA signed requests              │
                     └─────────────────────────────────────┘
```

## Key V28 rule

The raw Tailscale IPv4 is never treated as the Android HTTPS identity. It is only an optional connection target returned by the custom DNS layer. The request hostname remains the `.ts.net` name so TLS/SNI/certificate verification remain intact.

## Resource rule

The governor may throttle background specialist fan-out, but foreground conversation remains available. 47 profiles still share the same local model rather than loading 47 model copies.

## HoloLab rule

HoloLab visual checks are clearly separated from real engineering solvers. No FEA/thermal/manufacturing result is invented from a webcam overlay.
