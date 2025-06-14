from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum

from datetime import date 
from dateutil import relativedelta


#---Abstract Class---
class Personel(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    bio = models.TextField(max_length=250, null=True, blank=True)
    birth = models.DateField()
    picture = models.ImageField(upload_to='personel_photos/', blank=True)


    class Meta:
        abstract = True
    
    @property
    def age(self):
        if not self.birth:
            return None
        today = date.today()
        age = relativedelta(today, self.birth)
        return f"{age.years} years {age.months} months {age.days} days"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"



# --- Constants ---
class SessionChoice(models.TextChoices):
    SPRING = "S", "Spring"
    FALL = "F", "Fall"

class CoachRoles(models.TextChoices):
    HEAD = "H", "Head Coach"
    ASSISTANT = "A", "Assistant Coach"

class MatchStatus(models.TextChoices):
    SCHEDULED = "SCH", "Scheduled"
    LIVE = "LIV", "Live"
    FINISHED = "FIN", "Finished"
    CANCELLED = "CAN", "Cancelled"


    status = models.CharField(max_length=3, choices=MatchStatus.choices, default=MatchStatus.SCHEDULED)


# --- League/Season Model ---
class League(models.Model):  
    year = models.IntegerField()
    session = models.CharField(max_length=1, choices=SessionChoice.choices)
    is_active = models.BooleanField(default=True)
    logo = models.ImageField(upload_to='league_logos/', null=True, blank=True)

    class Meta:
        verbose_name_plural = "Leagues"

    def __str__(self):
        return f"{self.session} - {self.year}"


# --- Team Model ---
class Team(models.Model):
    name = models.CharField(max_length=50)
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Teams"
    
    def get_current_players(self, league):
        return Player.objects.filter(
            playerseasonparticipation__team=self,
            playerseasonparticipation__league=league,
            playerseasonparticipation__is_active=True
        )


    def __str__(self):
        return self.name


    def all_matches(self):
        return Match.objects.filter(
            models.Q(home_team=self) | models.Q(away_team=self)
        )


# --- Coach Model ---
class Coach(Personel):  
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='coaches')
    role = models.CharField(max_length=1, choices=CoachRoles.choices, default=CoachRoles.ASSISTANT)
    
   
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"


# --- Player Model ---
class Player(Personel):
    POSITION_CHOICES = [
        ("GK", "Goalkeeper"),
        ("DF", "Defender"),
        ("MF", "Midfielder"),
        ("FW", "Forward"),
    ]

    position = models.CharField(max_length=2, choices=POSITION_CHOICES)
    is_active = models.BooleanField(verbose_name='active', default=True)


# --- Match Model ---
class Match(models.Model):
    season = models.ForeignKey(League, on_delete=models.CASCADE)
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE)
    home_score = models.PositiveIntegerField(default=0)
    away_score = models.PositiveIntegerField(default=0)
    date = models.DateTimeField()
    status = models.CharField(max_length=3, choices=MatchStatus.choices, default=MatchStatus.SCHEDULED)


    def clean(self):
        """Ensures a team doesn't play against itself"""
        if self.home_team == self.away_team:
            raise ValidationError("A team cannot play against itself")

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} on {self.date.strftime('%Y-%m-%d')}"


    

class PlayerSeasonParticipation(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)

    matches_played = models.IntegerField(default=0)
    goals = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)
    yellow_cards = models.IntegerField(default=0)
    red_cards = models.IntegerField(default=0)

    joined_at = models.DateField(auto_now_add=True)
    left_at = models.DateField(null=True, blank=True)
    is_captain = models.BooleanField(default=False)  # optional
    is_active = models.BooleanField(default=True) 

    def update_totals(self):
        """
        Recalculate cumulative stats from PlayerStats linked to this season participation.
        
        """
        stats = self.player_stats.aggregate(
            total_goals=Sum('goals'),
            total_assists=Sum('assists'),
            total_yellow=Sum('yellow_cards'),
            total_red=Sum('red_cards'),
        )

        self.goals = stats['total_goals'] or 0
        self.assists = stats['total_assists'] or 0
        self.yellow_cards = stats['total_yellow'] or 0
        self.red_cards = stats['total_red'] or 0
        self.matches_played = self.player_stats.count()
        self.save()



    class Meta:
        unique_together = ('player', 'team', 'league')
    
    def __str__(self):
        return f"{self.player} in {self.league}"

    class CoachSeasonParticipation(models.Model):
        coach = models.ForeignKey(Coach, on_delete=models.CASCADE)
        team = models.ForeignKey(Team, on_delete=models.CASCADE)
        league = models.ForeignKey(League, on_delete=models.CASCADE)
        joined_at = models.DateField(auto_now_add=True)
        left_at = models.DateField(null=True, blank=True)

        class Meta:
            unique_together = ['coach', 'team', 'league']



class TeamSeasonParticipation(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)

    points = models.IntegerField(default=0)
    goals_scored = models.IntegerField(default=0)
    goals_conceded = models.IntegerField(default=0)

    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    matches_played = models.IntegerField(default=0)


    @property
    def goal_difference(self):
        return self.goals_scored - self.goals_conceded
    

    class Meta:
        unique_together = ["team", "league"]
        ordering = ['-points', '-goals_scored', 'goals_conceded']
    
    
    def __str__(self):  
        return f"{self.team} in {self.league.session} ({self.league.year})"


    



# --- Player Stats Per Match ---
class PlayerStats(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    player_participation = models.ForeignKey(PlayerSeasonParticipation, on_delete=models.CASCADE, related_name='player_stats' )
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    goals = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    yellow_cards = models.PositiveIntegerField(default=0)
    red_cards = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['match', 'player']
        indexes = [
            models.Index(fields=['match', 'player']),
            models.Index(fields=['player_participation']),
        ]

    def clean(self):
        if self.player != self.player_participation.player:
            raise ValidationError("Player must match with the participation record")
        
        if self.match.season != self.player_participation.league:
            raise ValidationError("Match and participation must be in the same league")



    def __str__(self):
        return f"{self.player} stats in {self.match}"
