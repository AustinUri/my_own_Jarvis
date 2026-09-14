# JARVIS v28 — Start Here

## Keep V27 intact

Extract this build beside V27, for example:

```text
C:\Users\austi\Desktop\Jarvis_v27
C:\Users\austi\Desktop\Jarvis_v28
```

Do not overwrite V27 yet. Both versions use ports 8765/8766, so exit V27 completely before starting V28.

## First-time Python setup

Open PowerShell in `Jarvis_v28`:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
```

Then start V28:

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

## Phone Link v28

Keep the phone's server URL as the HTTPS tailnet hostname, for example:

```text
https://uri.tail3e47e7.ts.net
```

Do **not** replace that URL with `http://100.x.x.x` in the V28 companion.

Run on the PC:

```powershell
.\scripts\setup_phone_link.ps1
```

It prints two values:

```text
Secure server URL : https://...ts.net
DNS fallback IP   : 100.x.x.x
```

Enter both into the V28 Android companion. The fallback IP is optional when MagicDNS works. When supplied, V28 connects to the private Tailscale IP while still validating HTTPS using the `.ts.net` hostname.

Build the new Android APK with:

```powershell
.\scripts\build_android_v28.ps1
```

Then install `JARVIS_Companion_v28-debug.apk` on the Samsung.

## HoloLab Alpha

Open workspace **HoloLab** or **Vision**, enable the camera, then choose **Enter HoloLab**.

- show one hand: object anchors near the palm
- pinch thumb + index: object enters grabbed state
- move/rotate the hand: object follows
- use **Shape** to switch cube/sphere/ring
- use **Run visual test** for interaction/geometry checks
- if hand tracking cannot load, drag the hologram with mouse/touch and use the wheel for scale

HoloLab Alpha is visualization, not real CAD/FEA yet.

## Speech

V28 finishes the sentence currently being spoken before a normal interruption. This is deliberate and is meant to eliminate the V27 mid-sentence cut-off behavior.

## Resource protection

High VRAM can still throttle background specialist work, but it should no longer make JARVIS refuse the foreground request with the old “I paused heavy AI work” answer.

## Optional Away Mode

For a PC that will remain at home while you are away, after V28 is stable run:

```powershell
.\scripts\enable_away_mode.ps1
```

This creates a Windows Scheduled Task that starts the headless JARVIS core at your user logon and restarts it after unexpected process exits. It does not magically solve a powered-off PC: for unattended recovery after a power cut, configure BIOS **Restore on AC Power Loss** and use an appropriate UPS/sign-in setup.
