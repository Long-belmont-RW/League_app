from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from users.authentication import EmailRoleAuthBackend


class EmailRoleAuthBackendTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.backend = EmailRoleAuthBackend()

    def test_authenticate_case_insensitive_email_and_role(self):
        user = self.User.objects.create_user(
            username="user1",
            email="user@example.com",
            password="secret123",
            role="player",
        )

        res = self.backend.authenticate(request=None, username="USER@EXAMPLE.COM", password="secret123")
        self.assertEqual(res, user)

    def test_authenticate_rejects_inactive_user(self):
        user = self.User.objects.create_user(
            username="inactive1",
            email="inactive@example.com",
            password="secret123",
            role="fan",
        )
        user.is_active = False
        user.save()

        res = self.backend.authenticate(request=None, username="inactive@example.com", password="secret123")
        self.assertIsNone(res)

    def test_authenticate_accepts_email_kwarg_and_strips(self):
        user = self.User.objects.create_user(
            username="strip1",
            email="strip@example.com",
            password="secret123",
            role="coach",
        )

        res = self.backend.authenticate(request=None, email="  strip@example.com  ", password="secret123")
        self.assertEqual(res, user)

    def test_duplicate_case_variants_disambiguate_by_password(self):
        try:
            u1 = self.User.objects.create_user(
                username="dupe1",
                email="Dupe@example.com",
                password="pass1",
                role="player",
            )
            u2 = self.User.objects.create_user(
                username="dupe2",
                email="dupe@example.com",
                password="pass2",
                role="coach",
            )
        except IntegrityError:
            self.skipTest("Database enforces case-insensitive email uniqueness; cannot create case variants.")

        with self.assertLogs("users.authentication", level="WARNING") as cm:
            res = self.backend.authenticate(request=None, username="dupe@example.com", password="pass1")

        self.assertEqual(res, u1)
        self.assertTrue(any("Duplicate email detected" in msg for msg in cm.output))

    def test_duplicate_case_variants_ambiguous_returns_none(self):
        try:
            u1 = self.User.objects.create_user(
                username="mix1",
                email="Mix@example.com",
                password="samepass",
                role="fan",
            )
            u2 = self.User.objects.create_user(
                username="mix2",
                email="mix@example.com",
                password="samepass",
                role="coach",
            )
        except IntegrityError:
            self.skipTest("Database enforces case-insensitive email uniqueness; cannot create case variants.")

        with self.assertLogs("users.authentication", level="ERROR") as cm:
            res = self.backend.authenticate(request=None, username="mix@example.com", password="samepass")

        self.assertIsNone(res)
        self.assertTrue(any("authentication aborted" in msg.lower() for msg in cm.output))

