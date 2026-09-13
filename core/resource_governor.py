from __future__ import annotations

import csv
import io
import shutil
import subprocess
from dataclasses import dataclass, asdict
from typing import Any

import psutil

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(slots=True)
class ResourceSnapshot:
    cpu: float
    ram: float
    gpu_util: float | None = None
    vram_used_mb: float | None = None
    vram_total_mb: float | None = None
    vram_percent: float | None = None
    gpu_temp_c: float | None = None
    state: str = "normal"
    llm_parallel_limit: int = 2
    active_agent_limit: int = 6
    reason: str = "Resources are within the configured operating envelope."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResourceGovernor:
    """Conservative local resource guard for future multi-agent work.

    The 47-agent registry is mostly dormant identities.  This governor caps
    expensive concurrent LLM work and exposes a clear throttle state before a
    future scheduler is allowed to fan out.
    """

    def __init__(self, config) -> None:
        self.config = config

    def snapshot(self) -> ResourceSnapshot:
        cpu = round(float(psutil.cpu_percent(interval=None)), 1)
        ram = round(float(psutil.virtual_memory().percent), 1)
        gpu = self._gpu_metrics()
        snap = ResourceSnapshot(
            cpu=cpu,
            ram=ram,
            gpu_util=gpu.get("gpu_util"),
            vram_used_mb=gpu.get("vram_used_mb"),
            vram_total_mb=gpu.get("vram_total_mb"),
            vram_percent=gpu.get("vram_percent"),
            gpu_temp_c=gpu.get("gpu_temp_c"),
            llm_parallel_limit=max(1, min(2, int(getattr(self.config, "agent_max_parallel_llm", 2)))),
            active_agent_limit=max(2, min(8, int(getattr(self.config, "agent_max_active_specialists", 6)))),
        )
        self._apply_policy(snap)
        return snap

    def _apply_policy(self, snap: ResourceSnapshot) -> None:
        if not bool(getattr(self.config, "resource_governor_enabled", True)):
            snap.state = "disabled"
            snap.reason = "Resource governor is disabled in Settings."
            return

        ram_warn = float(getattr(self.config, "resource_ram_warn_percent", 75.0))
        ram_stop = float(getattr(self.config, "resource_ram_stop_percent", 85.0))
        vram_warn = float(getattr(self.config, "resource_vram_warn_percent", 85.0))
        vram_stop = float(getattr(self.config, "resource_vram_stop_percent", 92.0))
        gpu_warn = float(getattr(self.config, "resource_gpu_temp_warn_c", 80.0))
        gpu_stop = float(getattr(self.config, "resource_gpu_temp_stop_c", 84.0))

        severe: list[str] = []
        warn: list[str] = []
        if snap.ram >= ram_stop:
            severe.append(f"RAM {snap.ram:.0f}%")
        elif snap.ram >= ram_warn:
            warn.append(f"RAM {snap.ram:.0f}%")

        if snap.vram_percent is not None:
            if snap.vram_percent >= vram_stop:
                severe.append(f"VRAM {snap.vram_percent:.0f}%")
            elif snap.vram_percent >= vram_warn:
                warn.append(f"VRAM {snap.vram_percent:.0f}%")

        if snap.gpu_temp_c is not None:
            if snap.gpu_temp_c >= gpu_stop:
                severe.append(f"GPU {snap.gpu_temp_c:.0f}°C")
            elif snap.gpu_temp_c >= gpu_warn:
                warn.append(f"GPU {snap.gpu_temp_c:.0f}°C")

        if severe:
            snap.state = "protected"
            snap.llm_parallel_limit = 1
            snap.active_agent_limit = min(snap.active_agent_limit, 2)
            snap.reason = "Background heavy fan-out paused; foreground JARVIS remains available: " + ", ".join(severe)
        elif warn:
            snap.state = "throttled"
            snap.llm_parallel_limit = 1
            snap.active_agent_limit = min(snap.active_agent_limit, 4)
            snap.reason = "Parallel work reduced: " + ", ".join(warn)
        else:
            snap.state = "normal"
            snap.reason = "Resources are within the configured operating envelope."

    @staticmethod
    def _gpu_metrics() -> dict[str, float | None]:
        exe = shutil.which("nvidia-smi")
        if not exe:
            return {}
        query = "utilization.gpu,memory.used,memory.total,temperature.gpu"
        try:
            cp = subprocess.run(
                [exe, f"--query-gpu={query}", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3.0,
                creationflags=CREATE_NO_WINDOW,
            )
            if cp.returncode != 0 or not cp.stdout.strip():
                return {}
            row = next(csv.reader(io.StringIO(cp.stdout.strip())))
            util, used, total, temp = (float(x.strip()) for x in row[:4])
            pct = (used / total * 100.0) if total > 0 else None
            return {
                "gpu_util": round(util, 1),
                "vram_used_mb": round(used, 0),
                "vram_total_mb": round(total, 0),
                "vram_percent": None if pct is None else round(pct, 1),
                "gpu_temp_c": round(temp, 1),
            }
        except Exception:
            return {}
