from django.urls import path
from . import views


app_name = "fantasy"

urlpatterns = [
    path("", views.fantasy_league_list, name="league_list"),
    path("<int:league_id>/", views.fantasy_league_detail, name="league_detail"),
    path("<int:league_id>/my-team/", views.my_fantasy_team, name="my_team"),
    path("<int:league_id>/team/create/", views.create_fantasy_team, name="create_team"),
    path("<int:league_id>/player/add/", views.add_player_to_team, name="add_player"),
    path("<int:league_id>/player/remove/", views.remove_player_from_team, name="remove_player"),
    path("<int:league_id>/player/captain/", views.set_captain, name="set_captain"),
    path("<int:league_id>/player/vice-captain/", views.set_vice_captain, name="set_vice_captain"),
    path("<int:league_id>/leaderboard/", views.fantasy_leaderboard, name="leaderboard"),
    path("<int:league_id>/week/<int:week_index>/", views.fantasy_week_summary, name="week_summary"),
    path("<int:league_id>/transfers/", views.fantasy_transfers, name="transfers"),
]


