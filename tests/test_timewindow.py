import pytest
from datetime import datetime, timezone, timedelta
from core.tuples import TimeWindow, TemporalContext
from core.evaluator import _in_time_window


def test_timewindow_inclusive_start_exclusive_end():
    now = datetime(2025, 11, 2, 12, 0, 0, tzinfo=timezone.utc)
    start = now.replace(hour=10)
    end = now.replace(hour=13)
    tw = TimeWindow(start=start, end=end)

    # start <= now (inclusive) -> True
    assert _in_time_window(now, tw) is True

    # end is exclusive -> now == end should be False
    now_at_end = end
    assert _in_time_window(now_at_end, tw) is False

    # before start is False
    before = start - timedelta(seconds=1)
    assert _in_time_window(before, tw) is False

    # after end is False
    after = end + timedelta(seconds=1)
    assert _in_time_window(after, tw) is False


def test_timewindow_dict_input():
    now = datetime(2025, 11, 2, 9, 30, 0, tzinfo=timezone.utc)
    start = (now - timedelta(hours=1)).isoformat()
    end = (now + timedelta(hours=1)).isoformat()
    window = {"start": start, "end": end}

    assert _in_time_window(now, window) is True


def test_access_window_open_start_or_end():
    now = datetime(2025, 11, 2, 15, 0, 0, tzinfo=timezone.utc)
    # open start -> only end enforced
    w1 = TimeWindow(start=None, end=now + timedelta(hours=1))
    assert _in_time_window(now, w1) is True

    # open end -> only start enforced
    w2 = TimeWindow(start=now - timedelta(hours=1), end=None)
    assert _in_time_window(now, w2) is True

    # both None -> always True
    w3 = TimeWindow(start=None, end=None)
    assert _in_time_window(now, w3) is True
