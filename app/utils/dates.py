"""
Date and time utilities for consistent datetime handling across the platform.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """Convert any datetime to UTC."""
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str | None:
    """Format datetime as string, handling None gracefully."""
    if dt is None:
        return None
    return dt.strftime(format_str)


def days_ago(days: int) -> datetime:
    """Get UTC datetime N days ago."""
    return utc_now() - timedelta(days=days)


def days_from_now(days: int) -> datetime:
    """Get UTC datetime N days from now."""
    return utc_now() + timedelta(days=days)


def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Parse common date string formats into datetime.
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%B %Y",           # "January 2024"
        "%b %Y",           # "Jan 2024"
        "%Y",              # "2024"
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            # Add UTC timezone if naive
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    
    return None


def calculate_streak(activity_dates: list[datetime]) -> tuple[int, int]:
    """
    Calculate current and longest streak from a list of activity dates.
    
    Args:
        activity_dates: List of UTC datetimes (should be sorted, most recent first)
    
    Returns:
        (current_streak, longest_streak)
    """
    if not activity_dates:
        return 0, 0
    
    # Convert to date-only and remove duplicates (same day activities)
    dates = sorted(set(dt.date() for dt in activity_dates), reverse=True)
    
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    today = utc_now().date()
    expected_date = today
    
    # Calculate current streak
    for date in dates:
        if date == expected_date:
            current_streak += 1
            expected_date = date - timedelta(days=1)
        elif date == expected_date + timedelta(days=1) and current_streak == 0:
            # Activity from yesterday when we haven't started counting
            current_streak += 1
            expected_date = date - timedelta(days=1)
        else:
            break
    
    # Calculate longest streak
    temp_streak = 1
    for i in range(1, len(dates)):
        if dates[i-1] - dates[i] == timedelta(days=1):
            temp_streak += 1
        else:
            longest_streak = max(longest_streak, temp_streak)
            temp_streak = 1
    
    longest_streak = max(longest_streak, temp_streak, current_streak)
    
    return current_streak, longest_streak


def time_until_deadline(deadline: datetime) -> dict:
    """
    Calculate human-readable time until deadline.
    
    Returns:
        {
            "days": int,
            "hours": int,
            "minutes": int,
            "expired": bool,
            "urgent": bool (< 24 hours),
            "display": str
        }
    """
    now = utc_now()
    delta = deadline - now
    
    if delta.total_seconds() <= 0:
        return {
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "expired": True,
            "urgent": False,
            "display": "Expired"
        }
    
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    # Generate display string
    if days > 0:
        display = f"{days}d {hours}h"
    elif hours > 0:
        display = f"{hours}h {minutes}m"
    else:
        display = f"{minutes}m"
    
    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "expired": False,
        "urgent": delta.total_seconds() < 86400,  # < 24 hours
        "display": display
    }