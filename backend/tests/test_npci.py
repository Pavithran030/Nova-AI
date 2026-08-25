from datetime import datetime
from app.utils.npci import is_valid_npci_window, check_attempt_budget

def test_npci_windows():
    # 9:00 AM IST -> valid (< 10 AM)
    dt_morning = datetime(2026, 8, 25, 9, 0, 0)
    assert is_valid_npci_window(dt_morning) is True

    # 11:30 AM IST -> invalid (between 10 AM and 1 PM)
    dt_midday = datetime(2026, 8, 25, 11, 30, 0)
    assert is_valid_npci_window(dt_midday) is False

    # 2:30 PM IST -> valid (1 PM - 5 PM)
    dt_afternoon = datetime(2026, 8, 25, 14, 30, 0)
    assert is_valid_npci_window(dt_afternoon) is True

    # 7:00 PM IST -> invalid (between 5 PM and 9:30 PM)
    dt_evening = datetime(2026, 8, 25, 19, 0, 0)
    assert is_valid_npci_window(dt_evening) is False

    # 10:00 PM IST -> valid (> 9:30 PM)
    dt_night = datetime(2026, 8, 25, 22, 0, 0)
    assert is_valid_npci_window(dt_night) is True

def test_attempt_budget():
    assert check_attempt_budget(3, 4) is True
    assert check_attempt_budget(4, 4) is False
