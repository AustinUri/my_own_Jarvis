# JARVIS v29.2 architecture

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

Normal SIM call audio remains outside the public third-party Android capture path. V29.2 therefore separates call metadata from conversation summaries and never invents a summary when no recording/transcript exists.


## V29.2 mobile communications
Phone Tap-to-Talk records audio locally in the companion and sends it over the authenticated private Tailscale bridge to the PC Whisper pipeline. WhatsApp composition is executed on Android after JARVIS resolves one canonical contact number. The companion opens the WhatsApp conversation with text pre-filled; V29.2 does not automate the final Send tap. Wake word model repair is bounded to packaged OpenWakeWord ONNX files and retries only once.
