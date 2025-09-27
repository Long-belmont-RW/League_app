from django.urls import path
from . import views



urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('dashboard/admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('dashboard/coach/', views.coach_dashboard_view, name='coach_dashboard'),
    path('dashboard/player/', views.player_dashboard_view, name='player_dashboard'),
    path('dashboard/fan/', views.fan_dashboard_view, name='fan_dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('create_user/', views.create_user_view, name='create_user'),
    path('complete-profile/', views.complete_profile_view, name='complete_profile'),
]

