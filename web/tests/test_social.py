"""Test trang Cộng đồng (thảo luận #002, Stage 2: dữ liệu thật)."""
import io
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.jobs.models import Skill
from apps.social.models import Comment, Follow, Like, Post, Report
from apps.social.selectors import PAGE_SIZE
from apps.social.views import MAX_POSTS_PER_WINDOW

from .factories import make_job, make_user

FEED = reverse("community:feed")


def make_post(author, body="Bài viết thử", tags=(), minutes_ago=0, **fields):
    post = Post.objects.create(author=author, body=body, **fields)
    if minutes_ago:
        Post.objects.filter(pk=post.pk).update(created_at=timezone.now() - timedelta(minutes=minutes_ago))
    post.tags.set([Skill.objects.get_or_create(name=t)[0] for t in tags])
    return post


class ReadPagesTests(TestCase):
    def setUp(self):
        self.alice = make_user("alice", desired_title="Junior Backend", skills="Python, Django",
                               min_salary=30, bio="CV riêng tư của Alice")
        self.post = make_post(self.alice, "Chia sẻ về Django", tags=("Python",))

    def test_public_pages_for_anonymous(self):
        for url in (FEED, reverse("community:post", args=[self.post.pk]),
                    reverse("community:profile", args=["alice"])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        resp = self.client.get(FEED)
        self.assertContains(resp, "Chia sẻ về Django")
        self.assertContains(resp, "Đăng nhập để đăng bài")
        self.assertNotContains(resp, "data-composer")

    def test_nav_link_always_visible(self):
        self.assertContains(self.client.get(reverse("core:home")), f'href="{FEED}"')

    def test_404s(self):
        make_user("bob").__class__.objects.filter(username="bob").update(is_active=False)
        hidden = make_post(self.alice, is_hidden=True)
        self.assertEqual(self.client.get(reverse("community:post", args=[999999])).status_code, 404)
        self.assertEqual(self.client.get(reverse("community:post", args=[hidden.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("community:profile", args=["nobody"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("community:profile", args=["bob"])).status_code, 404)

    def test_profile_shows_only_public_fields(self):
        resp = self.client.get(reverse("community:profile", args=["alice"]))
        self.assertContains(resp, "Junior Backend")
        self.assertContains(resp, "Django")
        self.assertNotContains(resp, "alice@example.com")
        self.assertNotContains(resp, "CV riêng tư")
        self.assertNotContains(resp, "30 triệu")

    def test_hidden_posts_not_in_feed(self):
        make_post(self.alice, "Bài đã bị ẩn", is_hidden=True)
        self.assertNotContains(self.client.get(FEED), "Bài đã bị ẩn")

    def test_body_is_escaped(self):
        make_post(self.alice, "<script>alert(1)</script>")
        resp = self.client.get(FEED)
        self.assertContains(resp, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(resp, "<script>alert(1)</script>")

    def test_empty_feed(self):
        Post.objects.all().delete()
        self.assertContains(self.client.get(FEED), "Chưa có bài viết nào")

    def test_tag_filter_and_link_to_jobs(self):
        make_post(self.alice, "Bài về Docker", tags=("Docker",))
        resp = self.client.get(FEED, {"tag": "python"})
        self.assertEqual([p.body for p in resp.context["posts"]], ["Chia sẻ về Django"])
        self.assertContains(resp, f'{reverse("jobs:list")}?q=Python')

    def test_job_link_chip(self):
        job = make_job("Backend Python Developer")
        make_post(self.alice, "Có tin hay", job=job)
        self.assertContains(self.client.get(FEED), "Backend Python Developer")


class PaginationTests(TestCase):
    def test_keyset_pages_do_not_overlap(self):
        author = make_user("alice")
        for i in range(PAGE_SIZE * 2 + 3):
            make_post(author, f"Bài {i}", minutes_ago=i)
        first = self.client.get(FEED)
        self.assertEqual(len(first.context["posts"]), PAGE_SIZE)
        self.assertTrue(first.context["older_url"])
        second = self.client.get(FEED + first.context["older_url"])
        ids1 = {p.id for p in first.context["posts"]}
        ids2 = {p.id for p in second.context["posts"]}
        self.assertFalse(ids1 & ids2)
        self.assertEqual(len(ids2), PAGE_SIZE)
        third = self.client.get(FEED + second.context["older_url"])
        self.assertEqual(len(third.context["posts"]), 3)
        self.assertEqual(third.context["older_url"], "")

    def test_invalid_cursor_falls_back_to_first_page(self):
        make_post(make_user("alice"), "Bài duy nhất")
        for bad in ("abc", "-1", "999999"):
            with self.subTest(before=bad):
                resp = self.client.get(FEED, {"before": bad})
                self.assertEqual(resp.status_code, 200)

    def test_query_budget(self):
        author = make_user("alice")
        for i in range(PAGE_SIZE):
            make_post(author, f"Bài {i}", tags=("Python", "SQL"))
        self.client.force_login(make_user("viewer"))
        # session, user, posts (gồm đếm like/comment + đã thích), tags (prefetch), chủ đề nổi bật, gợi ý theo dõi.
        # Không đổi theo số bài trên trang → không có N+1.
        with self.assertNumQueries(6):
            self.client.get(FEED)


class WriteActionTests(TestCase):
    def setUp(self):
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.post = make_post(self.bob, "Bài của Bob")
        Skill.objects.create(name="Python")
        self.client.force_login(self.alice)

    def test_writes_require_login_and_post(self):
        anon = Client()
        urls = [reverse("community:create"), reverse("community:like", args=[self.post.pk]),
                reverse("community:comment", args=[self.post.pk]), reverse("community:report", args=[self.post.pk]),
                reverse("community:follow", args=["bob"])]
        for url in urls:
            with self.subTest(url=url):
                resp = anon.post(url)
                self.assertEqual(resp.status_code, 302)
                self.assertIn(reverse("accounts:login"), resp["Location"])
                self.assertEqual(self.client.get(url).status_code, 405)

    def test_csrf_enforced(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.alice)
        self.assertEqual(csrf_client.post(reverse("community:create"), {"body": "x"}).status_code, 403)
        self.assertFalse(Post.objects.filter(author=self.alice).exists())

    def test_create_post_with_allowed_tags_only(self):
        resp = self.client.post(reverse("community:create"), {"body": "  Xin chào  ", "tags": "python, KhôngCó, python"})
        post = Post.objects.get(author=self.alice)
        self.assertRedirects(resp, reverse("community:post", args=[post.pk]))
        self.assertEqual(post.body, "Xin chào")
        self.assertEqual([t.name for t in post.tags.all()], ["Python"])

    def test_create_post_validation(self):
        self.client.post(reverse("community:create"), {"body": "   "})
        self.client.post(reverse("community:create"), {"body": "x" * 2001})
        self.assertFalse(Post.objects.filter(author=self.alice).exists())

    def test_post_rate_limit(self):
        for i in range(MAX_POSTS_PER_WINDOW + 2):
            self.client.post(reverse("community:create"), {"body": f"Bài {i}"})
        self.assertEqual(Post.objects.filter(author=self.alice).count(), MAX_POSTS_PER_WINDOW)

    def test_like_toggle_json_and_unique(self):
        url = reverse("community:like", args=[self.post.pk])
        r1 = self.client.post(url, HTTP_ACCEPT="application/json").json()
        self.assertEqual(r1, {"pressed": True, "count": 1})
        r2 = self.client.post(url, HTTP_ACCEPT="application/json").json()
        self.assertEqual(r2, {"pressed": False, "count": 0})
        Like.objects.create(user=self.alice, post=self.post)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Like.objects.create(user=self.alice, post=self.post)

    def test_liked_state_shown_in_feed(self):
        Like.objects.create(user=self.alice, post=self.post)
        post = self.client.get(FEED).context["posts"][0]
        self.assertTrue(post.liked)
        self.assertEqual(post.like_count, 1)

    def test_follow_toggle_and_following_tab(self):
        carol = make_user("carol")
        make_post(carol, "Bài của Carol")
        make_post(self.alice, "Bài của tôi")
        self.client.post(reverse("community:follow", args=["bob"]))
        self.assertTrue(Follow.objects.filter(follower=self.alice, followee=self.bob).exists())
        bodies = {p.body for p in self.client.get(FEED, {"tab": "following"}).context["posts"]}
        self.assertEqual(bodies, {"Bài của Bob", "Bài của tôi"})
        self.client.post(reverse("community:follow", args=["bob"]))
        self.assertFalse(Follow.objects.filter(follower=self.alice).exists())

    def test_cannot_follow_self(self):
        resp = self.client.post(reverse("community:follow", args=["alice"]), HTTP_ACCEPT="application/json")
        self.assertEqual(resp.status_code, 400)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Follow.objects.create(follower=self.alice, followee=self.alice)

    def test_comment(self):
        url = reverse("community:comment", args=[self.post.pk])
        self.client.post(url, {"body": "Hay quá"})
        self.client.post(url, {"body": ""})
        self.client.post(url, {"body": "x" * 1001})
        self.assertEqual(list(Comment.objects.values_list("body", flat=True)), ["Hay quá"])
        self.assertContains(self.client.get(reverse("community:post", args=[self.post.pk])), "Hay quá")

    def test_report_once_per_user(self):
        url = reverse("community:report", args=[self.post.pk])
        self.client.post(url, {"reason": "spam"})
        self.client.post(url, {"reason": "spam"})
        self.client.post(url, {"reason": "bogus"})
        self.assertEqual(Report.objects.count(), 1)
        self.assertEqual(Report.objects.get().status, Report.Status.OPEN)

    def test_rejects_external_next(self):
        resp = self.client.post(reverse("community:like", args=[self.post.pk]), {"next": "https://evil.com/"})
        self.assertRedirects(resp, reverse("community:post", args=[self.post.pk]))

    def test_admin_can_review_reports(self):
        Report.objects.create(reporter=self.alice, post=self.post, reason="spam")
        admin = make_user("boss")
        admin.is_staff = admin.is_superuser = True
        admin.save()
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("admin:social_report_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:social_post_changelist")).status_code, 200)


class SeedCommandTests(TestCase):
    @override_settings(COMMUNITY_DEMO=False)
    def test_refuses_when_demo_off(self):
        with self.assertRaises(CommandError):
            call_command("seed_community", stdout=io.StringIO())
        self.assertFalse(Post.objects.exists())

    @override_settings(COMMUNITY_DEMO=True)
    def test_seeds_once(self):
        call_command("seed_community", stdout=io.StringIO())
        n = Post.objects.count()
        self.assertGreater(n, 0)
        call_command("seed_community", stdout=io.StringIO())
        self.assertEqual(Post.objects.count(), n)
        demo = Post.objects.first().author
        self.assertFalse(demo.has_usable_password())
