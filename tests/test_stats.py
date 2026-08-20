"""Tests for stopro.stats: session arithmetic and the printed summaries."""

from datetime import datetime, timedelta

import pytest

from helpers import ago, locked_state, make_state, ongoing, session
from stopro import lock, stats


FINISHED = ["2024-05-01 08:00:00", "2024-05-01 09:30:00"]   # 90 minutes
SHORT = ["2024-05-02 08:00:00", "2024-05-02 08:10:00"]      # 10 minutes


class TestGetSessionDurations:

    def test_empty_log_has_no_durations(self):
        assert stats.get_session_durations([]) == []

    def test_measures_every_finished_session(self):
        durations = stats.get_session_durations([FINISHED, SHORT])
        assert durations == [timedelta(minutes=90), timedelta(minutes=10)]

    def test_skips_the_session_that_is_still_open(self):
        assert stats.get_session_durations([FINISHED, ongoing(60)]) == [timedelta(minutes=90)]

    def test_an_only_open_session_yields_nothing(self):
        assert stats.get_session_durations([ongoing(60)]) == []

    def test_accepts_both_timestamp_formats(self):
        start = datetime(2024, 5, 1, 8, 0, 0)
        end = start + timedelta(minutes=5)
        assert stats.get_session_durations([[start.isoformat(), str(end)]]) == [timedelta(minutes=5)]


class TestGetDurationOfOngoingSession:

    def test_measures_from_the_last_start(self):
        assert stats.get_duration_of_ongoing_session([ongoing(600)]) == pytest.approx(600, abs=5)

    def test_earlier_sessions_are_ignored(self):
        assert stats.get_duration_of_ongoing_session([FINISHED, ongoing(60)]) == pytest.approx(60, abs=5)

    def test_is_exact_against_a_frozen_clock(self, freeze_now):
        start = datetime(2024, 5, 1, 8, 0, 0)
        freeze_now(start + timedelta(minutes=42), stats)
        assert stats.get_duration_of_ongoing_session([[start.isoformat(), "+"]]) == 2520.0


class TestGetTotalTime:

    def test_zero_without_any_session(self):
        assert stats.get_total_time(make_state()) == 0

    def test_sums_the_finished_sessions(self):
        assert stats.get_total_time(make_state(log=[FINISHED, SHORT])) == 6000.0

    def test_adds_the_ongoing_session_while_running(self):
        state = make_state(running=True, log=[FINISHED, ongoing(600)])
        assert stats.get_total_time(state) == pytest.approx(6000, abs=5)

    def test_a_stale_open_entry_is_ignored_when_not_running(self):
        state = make_state(running=False, log=[FINISHED, ongoing(600)])
        assert stats.get_total_time(state) == 5400.0


class TestGetLongestSession:

    def test_zero_without_any_session(self):
        assert stats.get_longest_session([]) == 0

    def test_picks_the_longest_finished_session(self):
        assert stats.get_longest_session([SHORT, FINISHED]) == 5400.0

    def test_the_ongoing_session_can_be_the_longest(self):
        assert stats.get_longest_session([SHORT, ongoing(7200)]) == pytest.approx(7200, abs=5)

    def test_a_short_ongoing_session_does_not_win(self):
        assert stats.get_longest_session([FINISHED, ongoing(60)]) == 5400.0

    def test_an_only_open_session_counts(self):
        assert stats.get_longest_session([ongoing(300)]) == pytest.approx(300, abs=5)


class TestGetTotalTimeLocked:

    def test_reads_the_lifetime_counter(self):
        assert stats.get_total_time_locked(make_state(total_time_locked=4242)) == 4242

    def test_zero_on_a_fresh_state(self):
        assert stats.get_total_time_locked(make_state()) == 0


class TestPrintSessionStatus:

    def test_reports_an_idle_stopro(self, state_file, output):
        state = state_file.write(make_state())
        stats.print_session_status(state)
        assert output() == "Self control session is not activated"

    def test_reports_a_running_session_with_its_duration(self, state_file, output):
        state = state_file.write(make_state(running=True, log=[ongoing(3600)]))
        stats.print_session_status(state)
        printed = output()
        assert "Self control session is activated" in printed
        assert "Current session: 1 hour" in printed

    def test_reports_the_lock(self, state_file, output):
        state = state_file.write(locked_state(locked_for=1800))
        stats.print_session_status(state)
        assert "This session is locked. (30 minutes)" in output()


class TestPrintLockStatus:

    def test_unlocked_session(self, state_file, output):
        state = state_file.write(make_state(running=True, log=[ongoing(60)]))
        stats.print_lock_status(state)
        assert output() == "This session is not locked"

    def test_locked_session_shows_the_lock_length(self, state_file, output):
        state = state_file.write(locked_state(locked_for=7200))
        stats.print_lock_status(state)
        assert output() == "This session is locked. (2 hours)"

    def test_an_expired_lock_reads_as_unlocked(self, state_file, output):
        state = state_file.write(locked_state(locked_for=60, locked_since_seconds_ago=3600))
        stats.print_lock_status(state)
        assert output() == "This session is not locked"

    def test_the_state_file_decides_whether_a_lock_exists(self, state_file, output):
        """print_lock_status() asks lock.is_locked(), which re-reads the file."""
        state_file.write(make_state())
        stats.print_lock_status(locked_state(locked_for=7200))
        assert output() == "This session is not locked"


class TestPrintGlobalStats:

    def test_reports_all_four_numbers(self, output):
        stats.print_global_stats(make_state(log=[FINISHED, SHORT]))
        printed = output()
        assert "Total time: 1 hour 40 minutes" in printed
        assert "Average time: 50 minutes" in printed
        assert "Total sessions: 2" in printed
        assert "Longest: 1 hour 30 minutes" in printed

    def test_a_fresh_install_reports_zeroes(self, output):
        stats.print_global_stats(make_state())
        printed = output()
        assert "Total time: 0 seconds" in printed
        assert "Average time: 0 seconds" in printed
        assert "Total sessions: 0" in printed
        assert "Longest: 0 seconds" in printed

    def test_the_running_session_is_not_counted_yet(self, output):
        state = make_state(running=True, log=[FINISHED, SHORT, ongoing(60)])
        stats.print_global_stats(state)
        assert "Total sessions: 2" in output()

    def test_the_very_first_session_averages_its_own_length(self, output):
        state = make_state(running=True, log=[ongoing(1800)])
        stats.print_global_stats(state)
        printed = output()
        assert "Total sessions: 0" in printed
        assert "Average time: 30 minutes" in printed

    def test_no_division_by_zero_on_the_first_session(self, output):
        stats.print_global_stats(make_state(running=True, log=[ongoing(1)]))
        assert "Average time:" in output()
