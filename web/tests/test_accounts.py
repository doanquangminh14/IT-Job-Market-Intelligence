from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile, User

from .factories import make_user


class RegisterTests(TestCase):
    def test_register_creates_user_profile_and_logs_in(self):
        resp = self.client.post(reverse("accounts:register"), {
            "username": "bob", "email": "Bob@Example.com",
            "password1": "S3cure-pass!", "password2": "S3cure-pass!",
        })
        self.assertRedirects(resp, reverse("accounts:profile"))
        user = User.objects.get(username="bob")
        self.assertEqual(user.email, "bob@example.com")
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_register_rejects_duplicate_email(self):
        make_user("alice")
        resp = self.client.post(reverse("accounts:register"), {
            "username": "alice2", "email": "ALICE@example.com",
            "password1": "S3cure-pass!", "password2": "S3cure-pass!",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Email này đã được sử dụng")
        self.assertFalse(User.objects.filter(username="alice2").exists())


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = make_user("alice")

    def test_login_and_logout(self):
        resp = self.client.post(reverse("accounts:login"), {"username": "alice", "password": "S3cure-pass!"})
        self.assertRedirects(resp, reverse("core:home"))
        resp = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(resp, reverse("core:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_wrong_password(self):
        resp = self.client.post(reverse("accounts:login"), {"username": "alice", "password": "nope"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user("alice")

    def test_requires_login(self):
        resp = self.client.get(reverse("accounts:profile"))
        self.assertRedirects(resp, f"{reverse('accounts:login')}?next={reverse('accounts:profile')}")

    def test_update_profile(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("accounts:profile"), {
            "first_name": "Alice", "last_name": "Nguyen", "email": "alice@example.com",
            "desired_title": "Data Engineer", "skills": "Python, SQL , Spark",
            "years_experience": "2", "preferred_city": "Hà Nội", "preferred_work_mode": "Remote",
            "min_salary": "20", "bio": "",
        })
        self.assertRedirects(resp, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alice")
        self.assertEqual(self.user.profile.skill_list, ["Python", "SQL", "Spark"])
        self.assertEqual(self.user.profile.preferred_work_mode, "Remote")

    def test_profile_created_if_missing(self):
        user = User.objects.create_user(username="noprof", email="np@example.com", password="x")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)
        self.assertTrue(Profile.objects.filter(user=user).exists())
