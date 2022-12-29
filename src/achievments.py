from rich.panel import Panel
from utils import get_state
from stats import format_second, get_longest_session, get_total_time

class Achievement:

    def __init__(self, name, description):
        self.name: str = name
        self.description: str = description
        self.level: int = 0
        self.level_milestones: list[int]
        self.stat: str = None
        self.next_level_message: str = None


    def __rich__(self):
        """Render achievement."""
        return Panel(
            f"[bold]{self.name}[/bold]\n{self.description}\n{self.stat}",
            title=f"{self.get_level_icon()} ({self.level})",
            subtitle=self.get_next_level_message(),
            title_align="left",
            border_style=self.get_level_color(),
            padding=(0, 1),
        )


    def get_level_icon(self):
        return ("", "🥔","🎖","🥉", "🥈", "🥇","🌟")[self.level]


    def get_level_color(self):
        return ("grey37","orange4","green","magenta","blue","yellow","red")[self.level]


    def get_next_level_message(self):
        if self.level >= 6:
            return "You've reached the highest level!"
        return "Next level: " + self.next_level_message[self.level]

    def update_level(self,x):
        """Update level based on stat."""
        for i, milestone in enumerate(self.level_milestones):
            if x < milestone:
                self.level = i
                return
        self.level = 6


class TotalTimeAchievement(Achievement):

    def __init__(self):
        super().__init__("Total Time", "Total time spent in self control sessions.")
        self.level_milestones = [86400, 1209600, 2592000, 5184000, 8640000, 15552000]
        total_time = get_total_time(get_state()["log"])
        self.update_level(total_time)
        self.stat = format_second(total_time)
        self.next_level_message = ["1 day",
                                   "14 days",
                                   "30 days",
                                   "60 days",
                                   "100 days",
                                   "180 days"]


class LongestSessionAchievement(Achievement):

    def __init__(self):
        super().__init__("Longest Session", "The longest time you have spend in self control session.")
        self.level_milestones = [14400, 28800, 57600, 86400, 604800,1209600]
        longest_session = get_longest_session(get_state()["log"])
        self.update_level(longest_session)
        self.stat = format_second(longest_session)
        self.next_level_message = ["4 hours",
                                   "8 hours",
                                   "16 hours",
                                   "1 day",
                                   "1 week",
                                   "2 weeks"]



class ForbiddenSitesAchievement(Achievement):

    def __init__(self, config):
        super().__init__("Number of forbidden sites", "Number of sites you have blocked to enhance your self control.")
        self.level_milestones = [5, 10, 20, 40, 60, 100]
        longest_session = get_longest_session(get_state()["log"])
        blocked_sites = len(config["forbidden_sites"])
        self.update_level(blocked_sites)
        self.stat = f"{blocked_sites} sites are blocked"
        self.next_level_message = ["5 sites",
                                   "10 sites",
                                   "20 sites",
                                   "40 sites",
                                   "60 sites",
                                   "100 sites"]


def get_achievements(config):
    return [
        TotalTimeAchievement(),
        LongestSessionAchievement(),
        ForbiddenSitesAchievement(config),
        ]

