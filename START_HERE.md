# Start here — JARVIS v23

## 1. Extract v23 to its own folder

Do not copy an old `.venv` into it.

## 2. Open PowerShell in the v23 project folder

If PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 3. Create the environment

```powershell
.\scripts\setup_windows.ps1
```

You can also run without activating the venv. All included scripts call `.venv\Scripts\python.exe` directly.

## 4. Start local services

Make sure Qwen is loaded in LM Studio as `jarvis-qwen`:

```powershell
lms ps
```

If needed:

```powershell
lms load qwen/qwen3.5-9b --identifier jarvis-qwen --context-length 16384
lms server start
```

Start SearXNG:

```powershell
docker start searxng
```

Or use:

```powershell
.\scripts\start_services.ps1
```

## 5. Verify

```powershell
.\scripts\doctor.ps1
```

## 6. Run JARVIS

```powershell
.\scripts\run_jarvis.ps1
```

v23 starts a local server at:

```text
http://127.0.0.1:8765
```

On Windows it will try to open the workspace in Edge/Chrome app mode. JARVIS remains alive in the system tray when that workspace window is closed.

## Workspace controls

- Drag panels by the panel title bar.
- Resize from the lower-right handle while layout editing is enabled.
- `×` hides a widget.
- `↗` opens a widget in its own window.
- `⛶` makes a widget fullscreen.
- `Ctrl+K` opens the command palette.
- The `Add Widget` bar restores hidden widgets.
- `Lock layout` disables accidental dragging/resizing.
- Layouts are saved automatically on this PC.

Try saying/typing:

- `Jarvis, switch to Research workspace.`
- `Show me the Sources panel.`
- `Hide Agent Activity.`
- `Switch to Minimal workspace.`

Those requests use safe UI tools; merely mentioning a panel does not rearrange the interface.

## Camera

The Vision workspace includes a Camera widget. It is OFF by default. Click `Enable camera` and Windows/browser permission will be requested. v23 provides the preview/permission architecture; gesture recognition is a later layer.

## Legacy UI

If you need the old PySide window:

```powershell
.\scripts\run_legacy.ps1
```

## Background mode

```powershell
.\scripts\run_background.ps1
```

JARVIS runs in the tray without automatically opening the workspace. Double-click the tray icon to open it.

## Frontend development

The shipped `workspace_ui/dist` is a zero-build runtime and works without Node.js. A React/TypeScript/Three.js development scaffold is also included under `workspace_ui/src` for the next UI iteration.

If you want to rebuild that development frontend and have Node/npm installed:

```powershell
.\scripts\rebuild_workspace.ps1
```
