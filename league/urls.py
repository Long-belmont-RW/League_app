from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('leagues/', views.LeaguesView.as_view(), name='leagues'),
    path('league_table/<int:league_id>/', views.league_table_view, name='league_table'),
    path('league/stats/<int:league_id>/', views.TopStatsView.as_view(), name='top_stats'),
    path('teams/', views.TeamView.as_view(), name='teams'),
    path('team_details/<int:team_id>/', views.team, name='team'),
    path('matches/create/', views.MatchFormView.as_view(), name='create_match'),
    path('matches/edit/<int:match_id>/', views.MatchFormView.as_view(), name='edit_match'),
    path('matches/delete/<int:pk>/', views.DeleteMatchView.as_view(), name='delete_match'),
    path('matches/', views.MatchListView.as_view(), name='match_list'),
    path('matches/stats/<int:match_id>/', views.edit_player_stats_view, name='edit_player_stats'),
    path('matches/<int:match_id>/lineup/', views.manage_lineup_view, name='manage_lineup'),
    path('player/<int:player_id>/', views.player_profile, name='player_profile'),
    path('match/<int:match_id>/details/', views.match_details, name='match_details'),
    # path('manage-team-of-the-week/', views.manage_team_of_the_week, name='manage_team_of_the_week'),
    # path('team-of-the-week/', views.team_of_the_week_view, name='team_of_the_week'),
]