from __future__ import annotations

from datetime import datetime


def tell_time() -> str:
    now = datetime.now()
    return f"The time is {now:%H:%M}."
