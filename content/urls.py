from django.urls import path
from . import views



urlpatterns = [
    path('invite/coach/', views.invite_coach, name='invite_coach'),
    path('invite/accept/<uuid:token>/', views.accept_invitation, name='accept_invitation'),
    path('invite/player/', views.invite_player_view, name='invite_player'),

]

