import io
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.contrib.auth import get_user_model

from league.models import Team, League, TeamSeasonParticipation, Player, PlayerSeasonParticipation


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class BulkUploadPlayersTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_password = 'AdminPass123!'
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password=self.admin_password,
            role='admin',
            is_superuser=True,
        )
        self.team = Team.objects.create(name='Test FC')
        self.league = League.objects.create(year=2025, session='S', is_active=True)
        TeamSeasonParticipation.objects.create(team=self.team, league=self.league)

    def login_admin(self):
        self.assertTrue(self.client.login(username=self.admin.email, password=self.admin_password))

    def _upload(self, csv_text: str):
        file = SimpleUploadedFile('players.csv', csv_text.encode('utf-8'), content_type='text/csv')
        url = reverse('bulk_upload_players')
        return self.client.post(url, {
            'team': self.team.id,
            'league': self.league.id,
            'file': file,
        }, follow=True)

    def test_success_creates_users_players_psp_and_sends_emails(self):
        self.login_admin()
        csv_text = (
            'first_name,last_name,email,position\n'
            'Jane,Doe,jane@example.com,FW\n'
            'John,Smith,john@example.com,GK\n'
        )
        resp = self._upload(csv_text)
        self.assertEqual(resp.status_code, 200)

        # 2 users created
        User = get_user_model()
        self.assertEqual(User.objects.filter(role='player').count(), 2)
        # 2 players exist (via signal)
        self.assertEqual(Player.objects.count(), 2)
        # PSPs created
        self.assertEqual(PlayerSeasonParticipation.objects.filter(team=self.team, league=self.league).count(), 2)
        # emails sent to both
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Password:', mail.outbox[0].body)

    def test_existing_user_is_attached_no_password_email(self):
        self.login_admin()
        User = get_user_model()
        existing = User.objects.create_user(email='exists@example.com', password='xyz12345', role='fan', first_name='Ex', last_name='Ist')
        csv_text = (
            'first_name,last_name,email,position\n'
            'Ex,Ist,exists@example.com,MF\n'
            'New,Player,new@example.com,DF\n'
        )
        resp = self._upload(csv_text)
        self.assertEqual(resp.status_code, 200)

        # role updated to player
        existing.refresh_from_db()
        self.assertEqual(existing.role, 'player')
        # PSPs for both
        self.assertEqual(PlayerSeasonParticipation.objects.filter(team=self.team, league=self.league).count(), 2)
        # emails sent only for new user
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('new@example.com', mail.outbox[0].to)

    def test_missing_header_aborts(self):
        self.login_admin()
        csv_text = (
            'first_name,last_name,email\n'  # missing position
            'Jane,Doe,jane@example.com\n'
        )
        resp = self._upload(csv_text)
        self.assertEqual(resp.status_code, 200)
        # No creations
        User = get_user_model()
        self.assertEqual(User.objects.filter(role='player').count(), 0)
        self.assertEqual(Player.objects.count(), 0)
        self.assertEqual(PlayerSeasonParticipation.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_position_aborts(self):
        self.login_admin()
        csv_text = (
            'first_name,last_name,email,position\n'
            'Jane,Doe,jane@example.com,XYZ\n'
        )
        self._upload(csv_text)
        User = get_user_model()
        self.assertEqual(User.objects.filter(role='player').count(), 0)
        self.assertEqual(Player.objects.count(), 0)
        self.assertEqual(PlayerSeasonParticipation.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_duplicate_emails_in_csv_aborts(self):
        self.login_admin()
        csv_text = (
            'first_name,last_name,email,position\n'
            'Jane,Doe,jane@example.com,FW\n'
            'John,Smith,jane@example.com,GK\n'
        )
        self._upload(csv_text)
        User = get_user_model()
        self.assertEqual(User.objects.filter(role='player').count(), 0)
        self.assertEqual(Player.objects.count(), 0)
        self.assertEqual(PlayerSeasonParticipation.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_team_not_active_in_league_aborts(self):
        self.login_admin()
        # Use a league where team isn't registered
        league2 = League.objects.create(year=2026, session='F', is_active=True)
        file = SimpleUploadedFile('players.csv', (
            'first_name,last_name,email,position\nJane,Doe,jane@example.com,FW\n'
        ).encode('utf-8'), content_type='text/csv')
        url = reverse('bulk_upload_players')
        resp = self.client.post(url, {
            'team': self.team.id,
            'league': league2.id,
            'file': file,
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        User = get_user_model()
        self.assertEqual(User.objects.filter(role='player').count(), 0)
        self.assertEqual(len(mail.outbox), 0)
