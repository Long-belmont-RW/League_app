from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Invitation
from league.models import Team, League
import uuid
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from .services import process_invitation

User = get_user_model()

class ContentViewsTest(TestCase):

    def setUp(self):
        """
        Set up objects to be used by all test methods.
        """
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='password123',
            role='admin'
        )
        self.team = Team.objects.create(name="Test Team")
        self.league = League.objects.create(year=2025)
        self.invitation = Invitation.objects.create(
            email='newcoach@example.com',
            role='coach',
            team=self.team,
            token=uuid.uuid4()
        )

    def test_accept_invitation_view_redirects(self):
        """
        Tests that the accept_invitation view redirects to the register view.
        """
        response = self.client.get(reverse('accept_invitation', args=[self.invitation.token]))
        self.assertRedirects(response, reverse('register') + f'?token={self.invitation.token}')

    from league.models import Team, League, Coach, CoachSeasonParticipation

    def test_accept_invitation_post_flow(self):
        """
        Tests the successful submission of the acceptance form through the registration flow.
        """
        user_count_before = User.objects.count()

        # 1. Access the accept_invitation link, which should redirect to the register page
        response = self.client.get(reverse('accept_invitation', args=[self.invitation.token]), follow=False)
        self.assertEqual(response.status_code, 302)
        register_url_with_token = response.url

        # 2. Post to the registration page with the token
        response = self.client.post(register_url_with_token, {
            'username': 'newcoach',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
            'birth': '1990-01-01',
            'gender': 'M',
            'email': 'newcoach@example.com',
        }, follow=False)

        # 3. Check that the response is a redirect to the coach_dashboard
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('coach_dashboard'))

        # 4. Verify the user and invitation state
        self.assertEqual(User.objects.count(), user_count_before + 1)
        new_user = User.objects.get(username='newcoach')
        self.assertEqual(new_user.email, self.invitation.email)
        self.assertEqual(new_user.role, 'coach')

        self.invitation.refresh_from_db()
        self.assertTrue(self.invitation.is_accepted)

        # 5. Verify that the coach and team participation are created
        self.assertTrue(Coach.objects.filter(user=new_user).exists())
        coach = Coach.objects.get(user=new_user)
        self.assertTrue(CoachSeasonParticipation.objects.filter(coach=coach, team=self.invitation.team).exists())

class ProcessInvitationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@user.com', password='password', role='admin')
        self.team = Team.objects.create(name='Test Team')

    @patch('content.services.send_mail')
    def test_process_invitation_success(self, mock_send_mail):
        request = MagicMock()
        request.user = self.user
        request.build_absolute_uri.return_value = 'http://testserver/accept/some-token'
        
        email = 'new.player@example.com'
        role = 'player'
        
        result = process_invitation(request, email, role, self.team.id)
        
        self.assertTrue(result)
        self.assertTrue(Invitation.objects.filter(email=email, role=role, team=self.team).exists())
        mock_send_mail.assert_called_once()

    def test_process_invitation_user_exists(self):
        request = MagicMock()
        email = 'existing.user@example.com'
        User.objects.create_user(username='existinguser', email=email, password='password')
        
        result = process_invitation(request, email, 'player', self.team.id)
        
        self.assertFalse(result)
        self.assertFalse(Invitation.objects.filter(email=email).exists())

    def test_process_invitation_active_invitation_exists(self):
        request = MagicMock()
        email = 'invited.user@example.com'
        Invitation.objects.create(email=email, role='player', team=self.team)
        
        result = process_invitation(request, email, 'player', self.team.id)
        
        self.assertFalse(result)
        # Make sure we have only one invitation object
        self.assertEqual(Invitation.objects.filter(email=email).count(), 1)

    @patch('content.services.send_mail')
    def test_process_invitation_expired_invitation_deleted(self, mock_send_mail):
        request = MagicMock()
        request.user = self.user
        request.build_absolute_uri.return_value = 'http://testserver/accept/some-token'
        email = 'expired.invite@example.com'
        
        # Create an expired invitation
        expired_invitation = Invitation.objects.create(email=email, role='player', team=self.team)
        expired_invitation.created_at = timezone.now() - timedelta(days=4)
        expired_invitation.save()
        
        result = process_invitation(request, email, 'player', self.team.id)
        
        self.assertTrue(result)
        self.assertTrue(Invitation.objects.filter(email=email, role='player', team=self.team).exists())
        # The old one should be deleted, and a new one created.
        self.assertEqual(Invitation.objects.filter(email=email).count(), 1)
        mock_send_mail.assert_called_once()
