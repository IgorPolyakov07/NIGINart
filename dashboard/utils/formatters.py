from datetime import datetime
from typing import Optional
import pandas as pd
def format_number(value: Optional[float], decimals: int = 0) -> str:
    if value is None:
        return "—"
    if decimals == 0:
        return f"{int(value):,}"
    else:
        return f"{value:,.{decimals}f}"
def format_percent(value: Optional[float], decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}%"
def format_compact(value: Optional[float], show_sign: bool = False) -> str:
    if value is None or pd.isna(value):
        return "—"
    sign = "+" if value > 0 and show_sign else ""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        formatted = f"{value/1_000_000_000:.1f}B"
    elif abs_value >= 1_000_000:
        formatted = f"{value/1_000_000:.1f}M"
    elif abs_value >= 1_000:
        formatted = f"{value/1_000:.1f}K"
    else:
        formatted = f"{int(value)}"
    return sign + formatted if sign else formatted
def format_date(dt: Optional[datetime]) -> str:
    if dt is None:
        return "—"
    months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    return f"{dt.day} {months[dt.month]} {dt.year}"
def format_datetime(dt: Optional[datetime]) -> str:
    if dt is None:
        return "—"
    date_part = format_date(dt)
    time_part = dt.strftime("%H:%M")
    return f"{date_part}, {time_part}"
def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)
