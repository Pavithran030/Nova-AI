from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

def is_valid_npci_window(dt: datetime) -> bool:
    # Convert to IST (Asia/Kolkata) to enforce NPCI windows correctly
    ist = dt.astimezone(ZoneInfo("Asia/Kolkata"))
    t = ist.time()
    
    # Valid windows: before 10:00 AM, 1:00 PM - 5:00 PM, after 9:30 PM (IST)
    if t < time(10, 0):
        return True
    if time(13, 0) <= t <= time(17, 0):
        return True
    if t >= time(21, 30):
        return True
        
    return False

def get_next_valid_window(dt: datetime) -> datetime:
    # Convert to IST, compute next valid time, return as IST (still naive)
    ist = dt.astimezone(ZoneInfo("Asia/Kolkata"))
    t = ist.time()
    next_dt = ist.replace(tzinfo=None)  # strip tzinfo to keep naive for DB
    
    if time(10, 0) <= t < time(13, 0):
        next_dt = next_dt.replace(hour=13, minute=0, second=0, microsecond=0)
    elif time(17, 0) < t < time(21, 30):
        next_dt = next_dt.replace(hour=21, minute=30, second=0, microsecond=0)
        
    return next_dt

def check_attempt_budget(attempts_used: int, max_attempts: int) -> bool:
    return attempts_used < max_attempts
