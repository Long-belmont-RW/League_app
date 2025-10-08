from django.test import TestCase,Client, override_settings
from django.contrib.auth import get_user_model
from datetime import datetime, date, timedelta
from django.utils import timezone
from league.models import Player, Coach, League, Team, PlayerSeasonParticipation, CoachSeasonParticipation, SessionChoice, Match, MatchStatus, TeamSeasonParticipation

from django.urls import reverse
from .models import UserProfile

from unittest import mock

User = get_user_model()


@override_settings(SOCIALACCOUNT_PROVIDERS={})
class UserViewsAndSignalsTest(TestCase):

    @mock.patch('allauth.socialaccount.templatetags.socialaccount.provider_login_url', return_value='')
    def setUp(self, mock_provider_login_url):
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
            birth=date(2000, 1, 1),
            gender='M'
        )

        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@example.com',
            password='password123',
            role='coach',
            birth=date(1985, 5, 10),
            gender='F'
        )

        self.fan_user = User.objects.create_user(
            username='testfan',
            email='fan@example.com',
            password='password123',
            role='fan',
            birth=date(1995, 8, 20),
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
        self.player_participation = PlayerSeasonParticipation.objects.create(
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
            date=timezone.now() + timedelta(days=7),
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
            'password': 'newpassword123',
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

        #--- Context Assertations ---
        self.assertIn('player_team', response.context)
        self.assertEqual(response.context['player_team'], self.player_participation)

        self.assertIn('upcoming_matches', response.context)
        self.assertQuerySetEqual(
            response.context['upcoming_matches'],
            [self.upcoming_match],
            transform=lambda x: x
        )
    
    def test_coach_dashboard(self):
        """
        Tests access rules for Coach dashboard
        """

        self.client.login(email='coach@example.com', password='password123')
        response = self.client.get(reverse('coach_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'coach_dashboard.html')



        # --- Context Assertions ---
        self.assertEqual(response.context['coach_team'], self.coach_participation)
        self.assertQuerySetEqual(
            response.context['upcoming_matches'],
            [self.upcoming_match],
            transform=lambda x: x
        )
        # Check that the coach's team's player is in the context
        self.assertIn(self.player_participation, response.context['players'])

    

    def test_fan_dashboard(self):
        """
        tests access rules for fan dashboard
        """

        self.client.login(email='fan@example.com', password='password123')
        response = self.client.get(reverse('fan_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fan_dashboard.html')

        # --- Context Assertions ---
        self.assertEqual(response.context['latest_league'], self.league)
        self.assertIn(self.upcoming_match, response.context['matches'])
        
        # Check that both teams are in the context
        teams_in_context = [tsp.team for tsp in response.context['teams']]
        self.assertIn(self.team, teams_in_context)
        self.assertIn(self.team2, teams_in_context)


    def test_dashboard_access_for_wrong_roles(self):
        """
        Ensures users with incorrect roles are redirected from dashboards
        """

        # Fan tries to access player dashboard
        self.client.login(email='fan@example.com', password='password123')
        response = self.client.get(reverse('player_dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('player_dashboard')}")

        # Player tries to access coach dashboard
        self.client.login(email='player@example.com', password='password123')
        response = self.client.get(reverse('coach_dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('coach_dashboard')}")

    def test_admin_can_create_admin(self):
        """
        Tests that an admin user can create another admin user.
        """
        # Create an admin user and log them in
        admin_user = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='password123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.client.login(email='admin@example.com', password='password123')

        # POST request to create a new admin
        user_count_before = User.objects.count()
        response = self.client.post(reverse('register'), {
            'username': 'newadmin',
            'email': 'newadmin@example.com',
            'password': 'newpassword123',
            'password2': 'newpassword123',
            'role': 'admin',
            'birth': '1990-01-01',
            'gender': 'M',
        })

        # Check that the user was created and has the correct role
        self.assertEqual(User.objects.count(), user_count_before + 1)
        new_user = User.objects.get(username='newadmin')
        self.assertEqual(new_user.role, 'admin')
        self.assertTrue(new_user.is_staff)


    def test_create_user_view(self):
        """
        Tests the create_user_view for admin users.
        """
        # Create an admin user and log them in
        admin_user = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='password123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.client.login(email='admin@example.com', password='password123')

        # Test GET request
        response = self.client.get(reverse('create_user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_user.html')

        # Test POST request
        user_count_before = User.objects.count()
        response = self.client.post(reverse('create_user'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'role': 'fan',
        })
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertEqual(User.objects.count(), user_count_before + 1)
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.role, 'fan')

        # Test that non-admin user cannot access the view
        self.client.logout()
        self.client.login(email='player@example.com', password='password123')
        response = self.client.get(reverse('create_user'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('create_user')}")


@override_settings(SOCIALACCOUNT_PROVIDERS={})
class SuperuserLoginTest(TestCase):

    @mock.patch('allauth.socialaccount.templatetags.socialaccount.provider_login_url', return_value='')
    def setUp(self, mock_provider_login_url):
        """
        Set up a superuser for testing.
        """
        self.client = Client()
        self.superuser_email = 'superuser@example.com'
        self.superuser_password = 'password123'
        self.superuser = User.objects.create_superuser(
            username='superuser',
            email=self.superuser_email,
            password=self.superuser_password,
            role='admin',
            birth=date(1990, 1, 1),
            gender='M'
        )

    def test_superuser_login(self):
        """
        Tests that a superuser can log in successfully.
        """
        # Attempt to log in with the superuser's credentials
        response = self.client.post(reverse('login'), {
            'username': self.superuser_email,
            'password': self.superuser_password,
        })

        # Check for a successful redirect to the home page
        self.assertRedirects(response, reverse('home'))

        # Check that the user is authenticated
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user, self.superuser)


class SuperuserCreationTests(TestCase):
    """
    Tests for creating superusers using the configured User model.
    Focuses on required flags and basic integrity.
    """

    def setUp(self):
        self.User = get_user_model()

    def test_create_superuser_with_admin_role_sets_flags(self):
        su = self.User.objects.create_superuser(
            username="adminuser",
            email="adminuser@example.com",
            password="testpass123",
            role="admin",
        )
        self.assertTrue(su.is_superuser)
        self.assertTrue(su.is_staff)
        self.assertEqual(su.role, "admin")
        self.assertEqual(su.email, "adminuser@example.com")

    def test_create_superuser_requires_is_superuser_true(self):
        # Django's base manager enforces is_superuser=True
        with self.assertRaisesMessage(ValueError, "Superuser must have is_superuser=True."):
            self.User.objects.create_superuser(
                username="bad_super_flag",
                email="bad_super_flag@example.com",
                password="x",
                role="admin",
                is_superuser=False,
            )

    def test_create_superuser_requires_is_staff_true(self):
        # Django's base manager enforces is_staff=True
        with self.assertRaisesMessage(ValueError, "Superuser must have is_staff=True."):
            self.User.objects.create_superuser(
                username="bad_staff_flag",
                email="bad_staff_flag@example.com",
                password="x",
                role="admin",
                is_staff=False,
            )

    def test_create_superuser_requires_email(self):
        # With USERNAME_FIELD set to 'email', email is required
        with self.assertRaises(ValueError):
            self.User.objects.create_superuser(
                username="noemail",
                email=None,
                password="x",
                role="admin",
            )


@override_settings(SOCIALACCOUNT_PROVIDERS={})
class CreateUserViewTest(TestCase):

    @mock.patch('allauth.socialaccount.templatetags.socialaccount.provider_login_url', return_value='')
    def setUp(self, mock_provider_login_url):
        """
        Set up a super user that can create access the create user view
        """

        self.client = Client()
        self.superuser_email = 'superuser@example.com'
        self.superuser_password = 'password123'
        self.superuser = User.objects.create_superuser(
            username='superuser',
            email=self.superuser_email,
            password=self.superuser_password,
            role='admin',
            gender='M'
        )

        self.url = reverse('create_user')

        #Login the Admin
        self.client.login(username=self.superuser_email, password=self.superuser_password)
    

    def test_admin_can_create_user(self):
        response = self.client.post(self.url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'role':'player',
            'password': 'testpassword123',
        })
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_created_user_can_login(self):
        self.client.post(self.url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'role':'player',
            'password': 'testpassword123',
        })

        self.client.logout()


        login_successful = self.client.login(
            username = 'newuser@example.com',
            password = 'testpassword123'
        )

        self.assertTrue(login_successful)