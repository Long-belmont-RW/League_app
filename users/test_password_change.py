from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class PasswordChangeTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='old_password',
            role='player'
        )
        self.client.login(email='testuser@example.com', password='old_password')

    def test_change_password(self):
        response = self.client.post(reverse('password_change'), {
            'old_password': 'old_password',
            'new_password1': 'new_password',
            'new_password2': 'new_password',
        })
        self.assertRedirects(response, reverse('profile_edit'))

        self.client.login(email='testuser@example.com', password='new_password')

        # Verify that the old password no longer works
        self.client.logout()
        self.client.login(email='testuser@example.com', password='old_password')
        response = self.client.get(reverse('home'), follow=True)
        self.assertContains(response, "Please enter a correct email and password. Note that both fields may be case-sensitive.")
