#home view
def home(request):
    active_league = League.objects.filter(is_active=True).first()
    matches = Match.objects.none()
    top_scorers = PlayerSeasonParticipation.objects.none()
    team_of_the_week = None
    
    # Dropdown population
    leagues = League.objects.filter(is_active=True)
    weeks = TeamOfTheWeek.objects.values_list('week_number', flat=True).distinct().order_by('week_number')

    # Search/filter logic
    selected_league_id = request.GET.get('league')
    selected_week = request.GET.get('week')

    if selected_league_id and selected_week:
        try:
            team_of_the_week = TeamOfTheWeek.objects.prefetch_related('players').get(
                league_id=selected_league_id, 
                week_number=selected_week
            )
        except TeamOfTheWeek.DoesNotExist:
            team_of_the_week = None
    else:
        # Default to the latest team of the week
        team_of_the_week = TeamOfTheWeek.objects.prefetch_related('players').order_by('-league__year', '-week_number').first()

    if active_league:
        matches = Match.objects.filter(season=active_league, status=MatchStatus.FINISHED).select_related('home_team', 'away_team').order_by('-date')[:5]
        top_scorers = PlayerSeasonParticipation.objects.filter(
            league=active_league, is_active=True
        ).select_related('player').order_by('-goals')[:5]

        upcoming_matches = Match.objects.filter(season=active_league, status=MatchStatus.SCHEDULED).select_related('home_team', 'away_team').order_by('-date')[:5]
        league_table = TeamSeasonParticipation.objects.filter(league=active_league)[:3]

    context = {
        'matches': matches,
        'top_scorers': top_scorers,
        'active_league': active_league,
        'upcoming_matches': upcoming_matches,
        'league_table': league_table,
        'team_of_the_week': team_of_the_week,
        'leagues': leagues,
        'weeks': weeks,
        'selected_league': int(selected_league_id) if selected_league_id else None,
        'selected_week': int(selected_week) if selected_week else None,
    }
    return render(request, 'home.html', context)



#model.py
# --- Team of the Week ---
class TeamOfTheWeekPlayer(models.Model):
    class Position(models.TextChoices):
        GOALKEEPER = 'GK', 'Goalkeeper'
        DEFENDER = 'DEF', 'Defender'
        MIDFIELDER = 'MID', 'Midfielder'
        FORWARD = 'FWD', 'Forward'

    team_of_the_week = models.ForeignKey('TeamOfTheWeek', on_delete=models.CASCADE)
    player = models.ForeignKey('Player', on_delete=models.CASCADE)
    position = models.CharField(
        max_length=3,
        choices=Position.choices,
        default=Position.DEFENDER
    )

    def __str__(self):
        return f"{self.player.first_name} {self.player.last_name} ({self.get_position_display()}) on {self.team_of_the_week}"

class TeamOfTheWeek(models.Model):
    league = models.ForeignKey('League', on_delete=models.CASCADE)
    week_number = models.IntegerField()
    players = models.ManyToManyField('Player', through=TeamOfTheWeekPlayer, related_name='teams_of_the_week')

    class Meta:
        unique_together = ('league', 'week_number')

    def __str__(self):
        return f"Team of the Week for {self.league} - Week {self.week_number}"


        