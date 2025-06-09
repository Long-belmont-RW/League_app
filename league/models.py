from django.db import models

# --- Constants ---
class SessionChoice(models.TextChoices):
    SPRING = "S", "Spring"
    FALL = "F", "Fall"


# --- League/Season Model ---
class League(models.Model):  
    year = models.IntegerField()
    session = models.CharField(max_length=1, choices=SessionChoice.choices)
    is_active = models.BooleanField(default=True)
    logo = models.ImageField(upload_to='league_logos/', null=True, blank=True)

    def __str__(self):
        return f"{self.get_session_display()} {self.year}"


# --- Team Model ---
class Team(models.Model):
    name = models.CharField(max_length=50)
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.name


# --- Coach Model ---
class Coach(models.Model):  # Fixed typo: models.model → models.Model
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    team = models.OneToOneField(Team, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# --- Player Model ---
class Player(models.Model):
    POSITION_CHOICES = [
        ("GK", "Goalkeeper"),
        ("DF", "Defender"),
        ("MF", "Midfielder"),
        ("FW", "Forward"),
    ]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    position = models.CharField(max_length=2, choices=POSITION_CHOICES)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    picture = models.ImageField(upload_to='player_photos/', null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# --- Match Model ---
class Match(models.Model):
    season = models.ForeignKey(League, on_delete=models.CASCADE)
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE)
    home_score = models.PositiveIntegerField(default=0)
    away_score = models.PositiveIntegerField(default=0)
    date = models.DateTimeField()

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} on {self.date.strftime('%Y-%m-%d')}"


# --- Player Stats Per Match ---
class PlayerStats(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    goals = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    yellow_cards = models.PositiveIntegerField(default=0)
    red_cards = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.player} stats in {self.match}"

class TeamSeasonParticipation(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)

    points = models.IntegerField(default=0)
    goals_scored = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    position = models.IntegerField(null=True, blank=True)


    
