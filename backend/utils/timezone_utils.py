"""
IST Timezone Utilities
Centralizes timezone handling for the entire platform
"""

from datetime import datetime, timezone, timedelta
import pytz

# IST Timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))
IST_PYTZ = pytz.timezone('Asia/Kolkata')

def now_ist() -> datetime:
    """Get current time in IST timezone"""
    return datetime.now(IST)

def utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST"""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(IST)

def ist_to_utc(ist_dt: datetime) -> datetime:
    """Convert IST datetime to UTC for database storage"""
    if ist_dt.tzinfo is None:
        ist_dt = ist_dt.replace(tzinfo=IST)
    return ist_dt.astimezone(timezone.utc)

def format_ist_datetime(dt: datetime, format_str: str = "%Y-%m-%d %I:%M %p IST") -> str:
    """Format datetime for IST display"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ist_dt = dt.astimezone(IST)
    return ist_dt.strftime(format_str)

def parse_ist_datetime(date_str: str) -> datetime:
    """Parse IST datetime string to timezone-aware datetime"""
    # Add IST timezone info if not present
    try:
        dt = datetime.fromisoformat(date_str.replace('IST', '').strip())
        return dt.replace(tzinfo=IST)
    except Exception:
        # Fallback parsing
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=IST)