# Start JARVIS v29.1

## First PC start

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v29_1"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

Later starts only need activation + `run_jarvis.ps1`.

## Build the Android companion

```powershell
cd "C:\Users\austi\Desktop\Jarvis_v29_1"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\build_android_v29_1.ps1
```

Install `JARVIS_Companion_v29_1-debug.apk` on the Samsung phone.

The app now requests permissions with normal Android permission dialogs. `READ_CALL_LOG` is optional and Android may restrict it on a sideloaded non-dialer app; Phone Center falls back to calls initiated by JARVIS if full history is unavailable.

The phone `TAP TO TALK` button records directly inside the JARVIS app and sends audio to the PC for local Whisper transcription. It does not use Google Voice recognition.
