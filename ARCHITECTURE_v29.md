# JARVIS v29.1 architecture

```text
                         JARVIS CORE
                             |
          +------------------+------------------+
          |                  |                  |
      LM Studio          Coding JARVIS        Tools
     local model        isolated Git dev       |
          |                  |                  |
          +------------------+-----------+------+
                                         |
                               Tailscale Serve HTTPS
                                         |
                              Samsung JARVIS Companion
                               |       |       |
                         local mic  calendar  contacts/calls
                               |                 |
                               +--> PC Whisper   +--> Telecom

Desktop Control Center
  + Living Neutrino Core
  + Phone Center
      - secure link/device
      - recent call metadata
      - native calendar
      - conversation
      - future recorded-call summaries
  + Native Qt/Chromium Surface sibling pane
```

No cloud AI API key is required. Aperture remains optional/off.

Normal SIM call audio remains outside the public third-party Android capture path. V29.1 therefore separates call metadata from conversation summaries and never invents a summary when no recording/transcript exists.
