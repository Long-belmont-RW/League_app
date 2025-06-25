from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('leagues/', views.leagues, name='leagues'),
    path('league_table/<int:league_id>/', views.league_table_view, name='league_table'),
    path('league/stats/<int:league_id>', views.top_stats_view, name='top_stats'),
    path('teams/', views.team_view, name='teams'),
    path('team_details/<int:team_id>/', views.team, name="team"),

    path('matches/create/', views.match_form_view, name="create_match"),
    path('matches/edit/<int:match_id>', views.match_form_view, name="edit_match"),
    path('matches/delete/<int:match_id>', views.delete_match, name="delete_match"),
    path('matches/', views.match_list_view, name="match_list"),

    path('matches/stats/<int:match_id>', views.edit_player_stats_view, name='edit_player_stats'),

]