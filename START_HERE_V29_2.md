# Start JARVIS v29.2

## PC
```powershell
cd "C:\Users\austi\Desktop\Jarvis_v29_2"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

Normal later start:
```powershell
cd "C:\Users\austi\Desktop\Jarvis_v29_2"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\scripts\run_jarvis.ps1
```

## Samsung companion
Build the APK on the PC when you want a new phone install:
```powershell
.\scripts\build_android_v29_2.ps1
```
Install `JARVIS_Companion_v29_2-debug.apk` on the Samsung phone.

### New V29.2 checks
- Say **Hey Jarvis**. If the packaged OpenWakeWord model is corrupt, JARVIS should remove/redownload that model once instead of permanently killing the listener.
- From PC voice, PC chat, or phone Tap-to-Talk: **“WhatsApp Mum and tell her I’ll be home at eight.”** JARVIS should open the single deduplicated contact in WhatsApp with the message prepared. Review and tap Send on the phone.
