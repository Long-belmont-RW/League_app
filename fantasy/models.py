from django.conf import settings
from django.db import models
from django.db.models import Q


class FantasyLeague(models.Model):
    name = models.CharField(max_length=255)
    scoring_rules = models.JSONField(default=dict, help_text="JSON scoring config: e.g., goals, assists, cards, clean_sheets")
    start_date = models.DateField()
    end_date = models.DateField()

    max_team_size = models.PositiveIntegerField(default=15)
    budget_cap = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transfer_limit = models.PositiveIntegerField(default=1, help_text="Transfers allowed per match week")
    max_per_real_team = models.PositiveIntegerField(default=3)

    allow_captain_multiplier = models.BooleanField(default=True)
    captain_multiplier = models.PositiveIntegerField(default=2)

    class SellPricePolicy(models.TextChoices):
        PURCHASE = "purchase", "Refund at purchase price"
        CURRENT = "current", "Refund at current price"

    sell_price_policy = models.CharField(
        max_length=16,
        choices=SellPricePolicy.choices,
        default=SellPricePolicy.PURCHASE,
        help_text="How to compute refund when removing a player",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class FantasyTeam(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fantasy_teams")
    fantasy_league = models.ForeignKey(FantasyLeague, on_delete=models.CASCADE, related_name="teams")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Convenience relation for querying selected real players
    players = models.ManyToManyField('league.Player', through='FantasyPlayer', related_name='fantasy_teams')

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "fantasy_league"], name="unique_team_per_user_per_league"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.fantasy_league.name})"


class FantasyPlayer(models.Model):
    fantasy_team = models.ForeignKey(FantasyTeam, on_delete=models.CASCADE, related_name="fantasy_players")
    player = models.ForeignKey('league.Player', on_delete=models.CASCADE, related_name="fantasy_players")
    price_at_purchase = models.DecimalField(max_digits=12, decimal_places=2)

    is_captain = models.BooleanField(default=False)
    is_vice_captain = models.BooleanField(default=False)

    active_from = models.DateField()
    active_to = models.DateField(null=True, blank=True, help_text="Null means currently in the squad")

    class Meta:
        constraints = [
            # Only one active record for a given player in a given fantasy team
            models.UniqueConstraint(
                fields=["fantasy_team", "player"],
                condition=Q(active_to__isnull=True),
                name="unique_active_player_on_team",
            ),
            # Only one active captain per team
            models.UniqueConstraint(
                fields=["fantasy_team"],
                condition=Q(is_captain=True, active_to__isnull=True),
                name="unique_active_captain_per_team",
            ),
            # Only one active vice-captain per team
            models.UniqueConstraint(
                fields=["fantasy_team"],
                condition=Q(is_vice_captain=True, active_to__isnull=True),
                name="unique_active_vice_captain_per_team",
            ),
        ]
        ordering = ["fantasy_team_id", "player_id"]

    def __str__(self) -> str:
        return f"{self.player} @ {self.fantasy_team}"


class FantasyMatchWeek(models.Model):
    fantasy_league = models.ForeignKey(FantasyLeague, on_delete=models.CASCADE, related_name="match_weeks")
    index = models.PositiveIntegerField(help_text="Week number starting at 1")
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    deadline_at = models.DateTimeField()

    matches = models.ManyToManyField('league.Match', related_name='fantasy_match_weeks', blank=True)

    class Meta:
        unique_together = ("fantasy_league", "index")
        ordering = ["fantasy_league_id", "index"]

    def __str__(self) -> str:
        return f"{self.fantasy_league.name} – GW{self.index}: {self.name}"


class FantasyPlayerStats(models.Model):
    fantasy_player = models.ForeignKey(FantasyPlayer, on_delete=models.CASCADE, related_name="week_stats")
    fantasy_match_week = models.ForeignKey(FantasyMatchWeek, on_delete=models.CASCADE, related_name="player_stats")
    points = models.IntegerField(default=0)
    breakdown = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["fantasy_player", "fantasy_match_week"], name="unique_stats_per_player_per_week"),
        ]
        ordering = ["-fantasy_match_week_id", "-updated_at"]

    def __str__(self) -> str:
        return f"Stats {self.fantasy_player} – {self.fantasy_match_week}"


class FantasyLeaderboard(models.Model):
    fantasy_team = models.ForeignKey(FantasyTeam, on_delete=models.CASCADE, related_name="leaderboard_entries")
    fantasy_match_week = models.ForeignKey(FantasyMatchWeek, on_delete=models.CASCADE, null=True, blank=True, related_name="leaderboard_entries")

    points_week = models.IntegerField(default=0)
    cumulative_points = models.IntegerField(default=0)
    rank = models.PositiveIntegerField(default=0)
    is_overall = models.BooleanField(default=False, help_text="True for overall/cumulative row")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Ensure at most one weekly entry per team per week
            models.UniqueConstraint(
                fields=["fantasy_team", "fantasy_match_week"],
                name="unique_weekly_leaderboard_entry",
            ),
            # Ensure single overall entry per team
            models.UniqueConstraint(
                fields=["fantasy_team", "is_overall"],
                condition=Q(is_overall=True),
                name="unique_overall_leaderboard_entry",
            ),
        ]
        ordering = ["-is_overall", "rank", "-updated_at"]

    def __str__(self) -> str:
        scope = "Overall" if self.is_overall else (self.fantasy_match_week and f"GW{self.fantasy_match_week.index}")
        return f"{self.fantasy_team} – {scope}"


class FantasyTransfer(models.Model):
    fantasy_team = models.ForeignKey(FantasyTeam, on_delete=models.CASCADE, related_name="transfers")
    fantasy_match_week = models.ForeignKey(FantasyMatchWeek, on_delete=models.CASCADE, related_name="transfers")
    
    class Action(models.TextChoices):
        ADD = "add", "Add"
        REMOVE = "remove", "Remove"
        SWAP = "swap", "Swap"

    action = models.CharField(max_length=10, choices=Action.choices, default=Action.ADD)
    player_in = models.ForeignKey('league.Player', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    player_out = models.ForeignKey('league.Player', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.fantasy_team} transfer in {self.player_in} (out {self.player_out or '-'}), GW{self.fantasy_match_week.index}"


