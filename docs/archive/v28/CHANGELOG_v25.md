# JARVIS v25 changelog

## Runtime
- Added `ServiceManager` to keep LM Studio/Qwen and SearXNG available in the background.
- Can launch Docker Desktop automatically and start an existing SearXNG container.
- Can create a managed SearXNG container with JSON output enabled when no container exists.
- Windows autostart now uses `.venv\Scripts\pythonw.exe` so JARVIS starts silently without a console window.
- Tray is now the primary runtime control surface: open Control Center, push-to-talk, wake toggle, voice toggle, service health, full quit.

## Daily Intelligence
- Added persistent daily briefing cache.
- Optional sections: Israel, IDF/security, Champions League, Formula 1, AI/tech, weather, Calendar.
- Briefing is prepared on first Control Center connection each day and can be refreshed manually.
- Champions League briefing explicitly asks for all verified matches/scores and official highlight links when available.
- Added persistent F1 learning progression.

## Personal services
- Added Open-Meteo weather tool and Weather widget.
- Added Google Calendar OAuth service, event reading, status, and event creation tool.
- Calendar tokens and credentials live under `%APPDATA%\Jarvis\credentials`, outside the source tree.

## Workspaces / modes
- Added persistent server-side workspace profiles under `%APPDATA%\Jarvis\profiles`.
- Added built-in Command Center, Morning, Sports, F1, Research, Developer, Vision, Minimal, and Normal modes.
- Custom modes survive source upgrades because they no longer depend only on browser localStorage.
- Added Daily Briefing, Weather, Calendar, Champions League, F1 Learning and Runtime Services widgets.

## Visuals
- Reworked the default Stark theme toward a cyan/blue cinematic command-center design.
- Updated the central core palette and dashboard styling while keeping the interface original rather than copying film assets.
