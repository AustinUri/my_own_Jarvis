from __future__ import annotations

from typing import List, Tuple


def list_input_devices() -> List[Tuple[str, int]]:
    try:
        import sounddevice as sd
    except Exception:
        return [('Default', -1)]
    devices = []
    try:
        for index, device in enumerate(sd.query_devices()):
            if int(device.get('max_input_channels', 0)) > 0:
                name = str(device.get('name', f'Input {index}')).strip() or f'Input {index}'
                devices.append((name, index))
    except Exception:
        return [('Default', -1)]
    return [('Default', -1), *devices] if devices else [('Default', -1)]


def resolve_input_device(selected_name: str | None) -> int | None:
    if not selected_name or selected_name == 'Default':
        return None
    try:
        import sounddevice as sd
    except Exception:
        return None
    try:
        for index, device in enumerate(sd.query_devices()):
            if int(device.get('max_input_channels', 0)) <= 0:
                continue
            name = str(device.get('name', '')).strip()
            if name == selected_name:
                return index
        lowered = selected_name.lower()
        for index, device in enumerate(sd.query_devices()):
            if int(device.get('max_input_channels', 0)) <= 0:
                continue
            name = str(device.get('name', '')).strip()
            if lowered in name.lower():
                return index
    except Exception:
        return None
    return None
