
# Jarvis Starter v11

This build adds a **real whisper.cpp setup path** for Windows so you do not have to manually guess where the executable and model files belong.

## What is in this build

- Same Jarvis app as v10
- Better whisper.cpp error messages
- Ready-made PowerShell setup scripts:
  - `scripts/setup_whisper_cpp_cpu.ps1`
  - `scripts/setup_whisper_cpp_cuda.ps1`
  - `scripts/test_whisper_cpp.ps1`
- Pre-created folders that Jarvis already knows how to scan:
  - `third_party/whisper.cpp/build/bin/Release`
  - `third_party/whisper.cpp/models`

## What I did **not** bundle

I did **not** bundle:
- `whisper-cli.exe`
- ggml Whisper model files

Those come from the official `whisper.cpp` project and are large external artifacts. The setup scripts fetch/build them on **your** PC instead.

## Fastest path on Windows

Open PowerShell in the Jarvis folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_whisper_cpp_cpu.ps1 -Model small
```

Then in Jarvis Settings:
- set **STT backend** = `whisper.cpp`
- set **STT model** = `small`
- set **Language** = `Hebrew` or `English`

If that works, move to:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_whisper_cpp_cpu.ps1 -Model medium
```

Use `medium` for better Hebrew accuracy.

## CUDA path (optional)

If you already have **Visual Studio C++ build tools** and **CUDA toolkit** installed, you can try:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_whisper_cpp_cuda.ps1 -Model small
```

If that build fails, do not waste time fighting it right away. Use the CPU script first.

## Testing whisper.cpp directly

If you have a WAV file and want to test the binary outside Jarvis:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts	est_whisper_cpp.ps1 -WavPath .\your_audio.wav -Model small -Language he
```

## Notes

- Jarvis records 16 kHz mono WAV for command capture already, so you do **not** need ffmpeg just to test Jarvis voice commands.
- For Hebrew, use multilingual models like `small` or `medium`, **not** `.en` models.


## Web answers

Jarvis can now answer factual web questions.

- In **Settings > Web**, paste a **Tavily API key** for live internet answers.
- Without a Tavily key, Jarvis falls back to **Wikipedia only**.
- Ask things like:
  - `When was the last time a man touched the moon?`
  - `Who is the current president of France?`
  - `מתי האדם האחרון נגע בירח?`

Jarvis will speak a short answer and show source links in the GUI.


## Web answers without a paid API

Jarvis can now use a SearXNG instance for live web answers. In Settings, set **SearXNG instance URL** to a working instance such as a self-hosted local instance. If it is not set, or if the instance blocks JSON responses, Jarvis falls back to Wikipedia.
