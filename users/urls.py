from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('dashboard/admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('dashboard/coach/', views.coach_dashboard_view, name='coach_dashboard'),
    path('dashboard/player/', views.player_dashboard_view, name='player_dashboard'),
    path('dashboard/fan/', views.fan_dashboard_view, name='fan_dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('create_user/', views.create_user_view, name='create_user'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('add_player/', views.add_player_view, name='add_player'),
    path('coming-soon/', views.coming_soon, name='coming_soon'),
    path('password_change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # Admin tools
    path('dashboard/admin/bulk-upload-players/', views.bulk_upload_players_view, name='bulk_upload_players'),
]
