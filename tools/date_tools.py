from __future__ import annotations

from datetime import datetime


def tell_date() -> str:
    now = datetime.now()
    return now.strftime("Today is %A, %B %d, %Y.")
