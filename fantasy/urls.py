from django.urls import path
from . import views


app_name = "fantasy"

urlpatterns = [
    path("", views.fantasy_league_list, name="league_list"),
    path("<int:league_id>/", views.fantasy_league_detail, name="league_detail"),
    path("<int:league_id>/my-team/", views.my_fantasy_team, name="my_team"),
    path("<int:league_id>/leaderboard/", views.fantasy_leaderboard, name="leaderboard"),
    path("<int:league_id>/week/<int:week_index>/", views.fantasy_week_summary, name="week_summary"),
    path("<int:league_id>/transfers/", views.fantasy_transfers, name="transfers"),
]


