from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('leagues/', views.leagues, name='leagues'),
    path('league_table/<int:league_id>/', views.league_table_view, name='league_table'),
    path('teams/', views.team_view, name='teams'),
    path('team_details/<int:team_id>/', views.team, name="team")
]