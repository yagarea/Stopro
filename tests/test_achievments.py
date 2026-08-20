"""Tests for stopro.achievments: levels, rendering and the concrete badges."""

from io import StringIO

import pytest
from rich.console import Console

from helpers import DEFAULT_CONFIG, make_state, ongoing, session
from stopro import achievments
from stopro.achievments import (Achievement, ForbiddenSitesAchievement,
                                LongestSessionAchievement, TotalLockedTime,
                                TotalTimeAchievement, get_achievements)


def render(renderable) -> str:
    console = Console(file=StringIO(), width=200, color_system=None)
    console.print(renderable)
    return " ".join(console.file.getvalue().split())


def build(milestones, stat_value):
    achievement = Achievement("Test", "A test achievement")
    achievement.level_milestones = milestones
    achievement.next_level_message = ["a", "b", "c", "d", "e", "f"]
    achievement.stat = "stat"
    achievement.update_level(stat_value)
    return achievement


MILESTONES = [10, 20, 30, 40, 50, 60]


class TestUpdateLevel:

    @pytest.mark.parametrize("value, expected_level", [
        (0, 0),
        (9, 0),
        (10, 1),
        (19, 1),
        (20, 2),
        (30, 3),
        (40, 4),
        (50, 5),
        (59, 5),
        (60, 6),
        (10_000, 6),
    ])
    def test_level_follows_the_milestones(self, value, expected_level):
        assert build(MILESTONES, value).level == expected_level

    def test_a_milestone_is_reached_when_it_is_met_exactly(self):
        assert build(MILESTONES, 10).level == 1

    def test_the_top_level_is_six(self):
        assert build(MILESTONES, 10 ** 9).level == 6


class TestLevelPresentation:

    @pytest.mark.parametrize("level, icon", [
        (0, ""), (1, "\U0001F954"), (2, "\U0001F396"), (3, "\U0001F949"),
        (4, "\U0001F948"), (5, "\U0001F947"), (6, "\U0001F31F"),
    ])
    def test_every_level_has_an_icon(self, level, icon):
        achievement = build(MILESTONES, 0)
        achievement.level = level
        assert achievement.get_level_icon() == icon

    @pytest.mark.parametrize("level, colour", [
        (0, "grey37"), (1, "orange4"), (2, "green"),
        (3, "magenta"), (4, "blue"), (5, "yellow"), (6, "red"),
    ])
    def test_every_level_has_a_colour(self, level, colour):
        achievement = build(MILESTONES, 0)
        achievement.level = level
        assert achievement.get_level_color() == colour

    def test_next_level_message_points_at_the_next_milestone(self):
        achievement = build(MILESTONES, 0)
        assert achievement.get_next_level_message() == "Next level: a"
        achievement.level = 5
        assert achievement.get_next_level_message() == "Next level: f"

    def test_the_top_level_has_nothing_left_to_reach(self):
        achievement = build(MILESTONES, 10 ** 9)
        assert achievement.get_next_level_message() == "You've reached the highest level!"


class TestRendering:

    def test_panel_shows_name_description_stat_and_level(self):
        achievement = build(MILESTONES, 25)
        panel = achievement.__rich__()
        panel.width = 60
        rendered = render(panel)
        assert "Test" in rendered
        assert "A test achievement" in rendered
        assert "stat" in rendered
        assert "(2)" in rendered

    def test_every_real_achievement_renders(self, state_file):
        state_file.write(make_state())
        for achievement in get_achievements(DEFAULT_CONFIG):
            assert render(achievement) != ""


class TestTotalTimeAchievement:

    def test_starts_at_level_zero(self, state_file):
        state_file.write(make_state())
        achievement = TotalTimeAchievement()
        assert achievement.name == "Stoic"
        assert achievement.level == 0
        assert achievement.stat == "0 seconds"

    def test_a_day_of_focus_earns_the_first_level(self, state_file):
        state_file.write(make_state(log=[session(90000, 3600)]))
        achievement = TotalTimeAchievement()
        assert achievement.level == 1
        assert "1 day" in achievement.stat

    def test_reads_the_total_from_the_state_file(self, state_file):
        state_file.write(make_state(log=[["2024-05-01 08:00:00", "2024-05-01 09:00:00"]]))
        assert TotalTimeAchievement().stat == "1 hour"


class TestLongestSessionAchievement:

    def test_starts_at_level_zero(self, state_file):
        state_file.write(make_state())
        achievement = LongestSessionAchievement()
        assert achievement.name == "Marathonist"
        assert achievement.level == 0

    def test_a_five_hour_session_earns_the_first_level(self, state_file):
        state_file.write(make_state(log=[session(18000, 0)]))
        achievement = LongestSessionAchievement()
        assert achievement.level == 1
        assert "5 hours" in achievement.stat

    def test_only_the_longest_session_counts(self, state_file):
        state_file.write(make_state(log=[session(18000, 0), session(600, 0)]))
        assert LongestSessionAchievement().level == 1


class TestForbiddenSitesAchievement:

    def test_counts_the_configured_sites(self, state_file):
        state_file.write(make_state())
        achievement = ForbiddenSitesAchievement(DEFAULT_CONFIG)
        assert achievement.name == "Ascetic"
        assert achievement.stat == "3 sites are blocked"
        assert achievement.level == 0

    @pytest.mark.parametrize("site_count, expected_level", [
        (0, 0), (4, 0), (5, 1), (10, 2), (20, 3), (30, 4), (40, 5), (50, 6), (99, 6),
    ])
    def test_level_follows_the_number_of_sites(self, state_file, site_count, expected_level):
        state_file.write(make_state())
        config = {"forbidden_sites": [f"site{i}.com" for i in range(site_count)]}
        assert ForbiddenSitesAchievement(config).level == expected_level


class TestTotalLockedTime:

    def test_starts_at_level_zero(self, state_file):
        state_file.write(make_state())
        achievement = TotalLockedTime()
        assert achievement.name == "Totalitarian"
        assert achievement.level == 0
        assert achievement.stat == "0 seconds"

    def test_reads_the_lifetime_lock_counter(self, state_file):
        state_file.write(make_state(total_time_locked=90000))
        achievement = TotalLockedTime()
        assert achievement.level == 1
        assert "1 day" in achievement.stat


class TestGetAchievements:

    def test_returns_the_four_badges_in_order(self, state_file):
        state_file.write(make_state())
        names = [achievement.name for achievement in get_achievements(DEFAULT_CONFIG)]
        assert names == ["Stoic", "Marathonist", "Ascetic", "Totalitarian"]

    def test_each_badge_is_fully_populated(self, state_file):
        state_file.write(make_state())
        for achievement in get_achievements(DEFAULT_CONFIG):
            assert achievement.description
            assert achievement.stat
            assert len(achievement.level_milestones) == 6
            assert len(achievement.next_level_message) == 6

    def test_works_on_a_machine_that_never_ran_a_session(self, state_file):
        assert not state_file.exists()
        assert len(get_achievements(DEFAULT_CONFIG)) == 4
