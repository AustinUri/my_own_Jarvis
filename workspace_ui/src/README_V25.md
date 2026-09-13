# Note about the v25 UI source

JARVIS v28 runs the zero-build Control Center from `workspace_ui/dist/`.

The older React/TypeScript prototype under this `src/` directory is retained only as reference from v24 and is **not** the runtime bundle for v25. Do not run `npm build` expecting it to reproduce the v28 Control Center yet; `scripts/rebuild_workspace.ps1` intentionally warns instead of overwriting the shipped runtime.
