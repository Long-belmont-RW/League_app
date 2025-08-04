from django.test import TestCase,Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from league.models import Player, Coach, League, Team, \
    TeamSeasonParticipation, SessionChoice, PlayerSeasonParticipation, \
    CoachSeasonParticipation, Match, MatchStatus
from .models import UserProfile
import datetime



#Get the custom User Model
User = get_user_model()

'-----------------------------------------'
'                   TESTS                  '
'-----------------------------------------'
class UserViewsAndSignalsTest(TestCase):

    def setUp(self):
        """
        Sets up objects to be used by all the test methods 
        This method runs before each test
        """

        #Create a client to my http requests
        self.client = Client()

        #Create Users with different roles
        self.player_user = User.objects.create_user(
            username='testplayer',
            email='player@example.com',
            password='password123',
            role='player',
            birth=datetime.date(2000, 1, 1),
            gender='M'
        )

        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@example.com',
            password='password123',
            role='coach',
            birth=datetime.date(1985, 5, 10),
            gender='F'
        )

        self.fan_user = User.objects.create_user(
            username='testfan',
            email='fan@example.com',
            password='password123',
            role='fan',
            birth=datetime.date(1995, 8, 20),
            gender='M'
        )
        

        # ---Create related objects needed for dashboard views
        self.league = League.objects.create(year=2025, session=SessionChoice.FALL)
        self.team = Team.objects.create(name="Test Dragons")
        self.team2 = Team.objects.create(name="Test Knights")
        
        TeamSeasonParticipation.objects.create(team=self.team, league=self.league, points=10)
        TeamSeasonParticipation.objects.create(team=self.team2, league=self.league, points=5)

        #Create participation records to link personels (e.g coach,player...)
        self.player_obj = Player.objects.get(userprofile__user=self.player_user)
        self.coach_obj = Coach.objects.get(userprofile__user=self.coach_user)

        #Player joins Team for the league
        PlayerSeasonParticipation.objects.create(
            player=self.player_obj,
            team=self.team,
            league=self.league
        )

        # Coach joins Team 1 for the league
        self.coach_participation = CoachSeasonParticipation.objects.create(
            coach=self.coach_obj,
            team=self.team,
            league=self.league
        )


        # --- Create a future match for testing "upcoming matches" ---
        self.upcoming_match = Match.objects.create(
            season=self.league,
            home_team=self.team,
            away_team=self.team2,
            date=timezone.now() + datetime.timedelta(days=7),
            status=MatchStatus.SCHEDULED
        )


        

    # =================================================================
    # ==  TEST FOR THE DUPLICATE OBJECT BUG (SIGNAL TEST)            ==
    # =================================================================
    
    def test_signal_creates_one_personel_object(self):
        """"
        Tests that creating a User with creates ONE object for each role
        """

        self.assertEqual(User.objects.count(), 3)



        #Check that the UserProfile is correctly linked to the a personel (e.g player)
        player_profile = UserProfile.objects.get(user=self.player_user)
        self.assertIsNotNone(player_profile.player)
        self.assertIsNone(player_profile.coach) # Ensure it's not also a coach

    
    # =================================================================
    # ==  AUTHENTICATION VIEW TESTS (register, login, logout)        ==
    # =================================================================

    def test_register_view(self):
        """
        Tests the registraton view for both GET and POST requests.
        """

        #GET request
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')


        #POST request
        user_count_before = User.objects.count()
        response = self.client.post(reverse('register'), {
            'username': 'newfan',
            'email': 'newfan@example.com',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
            'role': 'fan',
            'birth': '1990-01-01',
            'gender': 'F',
        })
        
        # Should redirect to home on success
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(User.objects.count(), user_count_before + 1)


    def test_login_logout_view(self):
        """
        Tests the login and logout functionality
        """

        #Test successful Login
        response = self.client.post(reverse('login'), 
           { 'username': 'fan@example.com', # Form uses email as username
            'password': 'password123'
            }
            )
        
        self.assertRedirects(response, reverse('home'))

        #Check the user is now logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        # Test logout
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        
        # Make a new request to confirm the user is logged out
        response = self.client.get(reverse('home'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    
    def test_login_view_invalid_credentials(self):
        """
        Tests the login view with incorrect password.
        """
        response = self.client.post(reverse('login'), {
            'username': 'fan@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200) # Stays on the login page
        self.assertTemplateUsed(response, 'registration/login.html')
        self.assertContains(response, "Please enter a correct email and password. Note that both fields may be case-sensitive.") # Check for error message

    # =================================================================
    # ==  DASHBOARD ACCESS CONTROL TESTS                             ==
    # =================================================================
    def test_player_dashboard_access(self):
        """
        Tests access rules for player dashboard.
        """

        self.client.login(email='player@example.com', password='password123')
        response = self.client.get(reverse('player_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'player_dashboard.html')



