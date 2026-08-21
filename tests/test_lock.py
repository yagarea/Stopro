"""Tests for stopro.lock: lock time parsing and the lock lifecycle."""

from datetime import datetime, timedelta

import pytest

from helpers import as_state, locked_state, make_state
from stopro import lock, state as state_module


class TestParseLockTime:

    @pytest.mark.parametrize("raw, expected", [
        ("0", 0),
        ("1", 1),
        ("45", 45),
        ("30s", 30),
        ("0s", 0),
        ("1m", 60),
        ("30m", 1800),
        ("1h", 3600),
        ("4h", 14400),
        ("1d", 86400),
        ("7d", 604800),
        ("30 m", 1800),  # int() tolerates the space before the unit
    ])
    def test_accepts_a_number_with_an_optional_unit(self, raw, expected):
        assert lock.parse_lock_time(raw) == expected

    def test_a_bare_number_means_seconds(self):
        assert lock.parse_lock_time("90") == lock.parse_lock_time("90s")

    @pytest.mark.parametrize("raw", [" 30m", "30m ", "\t15h\n"])
    def test_surrounding_whitespace_is_ignored(self, raw):
        assert lock.parse_lock_time(raw) == lock.parse_lock_time(raw.strip())

    @pytest.mark.parametrize("raw", [
        "",              # nothing at all
        " ",             # whitespace only
        "m",             # unit without a number
        "abc",           # not a number
        "1.5h",          # fractional
        "30M",           # units are case sensitive
        "30w",           # unsupported unit
        "-5",            # negative seconds
        "-5m",           # negative with a unit
        "1e3",           # scientific notation
        "0x10",          # hexadecimal
    ])
    def test_rejects_everything_else(self, raw):
        with pytest.raises(lock.InvalidLockTime):
            lock.parse_lock_time(raw)

    def test_error_quotes_the_offending_value_and_lists_the_units(self):
        with pytest.raises(lock.InvalidLockTime) as error_info:
            lock.parse_lock_time("banana")
        message = str(error_info.value)
        assert "'banana'" in message
        for unit in ("s (seconds)", "m (minutes)", "h (hours)", "d (days)"):
            assert unit in message

    def test_error_keeps_the_raw_value(self):
        with pytest.raises(lock.InvalidLockTime) as error_info:
            lock.parse_lock_time("  banana  ")
        assert error_info.value.value == "  banana  "

    def test_every_documented_unit_is_supported(self):
        assert set(lock.UNIT_MULTIPLIERS) == {"s", "m", "h", "d"}


class TestProgressBars:

    def test_static_bar_renders_the_remaining_time(self, output, freeze_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        freeze_now(start + timedelta(seconds=600), state_module)
        state = as_state(make_state(is_locked=True, locked_since=start.isoformat(),
                                    locked_for=3600))
        lock.static_progressbar(state)
        printed = output()
        assert "Lock:" in printed
        assert "50 minutes remaining" in printed

    def test_static_bar_does_not_wait(self, monkeypatch):
        def explode(_seconds):
            raise AssertionError("the static bar must never sleep")
        monkeypatch.setattr(lock, "sleep", explode)
        lock.static_progressbar(as_state(locked_state(locked_for=3600)))

    def test_blocking_bar_returns_at_once_when_the_lock_expired(self, monkeypatch):
        def explode(_seconds):
            raise AssertionError("nothing left to wait for")
        monkeypatch.setattr(lock, "sleep", explode)
        lock.progressbar(as_state(locked_state(locked_for=60, locked_since_seconds_ago=600)))

    def test_blocking_bar_waits_out_the_lock_one_second_at_a_time(self, monkeypatch, advancing_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        state = as_state(make_state(is_locked=True, locked_since=start.isoformat(), locked_for=3))
        advancing_now(start, state_module)  # every now() call moves one second forward
        slept = []
        monkeypatch.setattr(lock, "sleep", slept.append)
        lock.progressbar(state)
        assert slept == [1, 1, 1]
