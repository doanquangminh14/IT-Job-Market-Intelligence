"""Test trang Cộng đồng (thảo luận #002, Stage 1: giao diện + dữ liệu demo)."""
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.social import mock_data

from .factories import make_job, make_user

FEED = reverse("community:feed")


def _post(**overrides):
    base = {"id": 99, "author": "lan.nguyen", "created_at": mock_data._t(24, 12), "tags": ["Python"],
            "job_id": None, "like_count": 0, "body": "Bài thử"}
    return {**base, **overrides}


@override_settings(COMMUNITY_DEMO=True)
class CommunityPagesTests(TestCase):
    def urls(self):
        return [FEED, reverse("community:post", args=[1]), reverse("community:profile", args=["lan.nguyen"])]

    def test_routes_render_for_anonymous_and_logged_in(self):
        for url in self.urls():
            with self.subTest(url=url, user="anonymous"):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(make_user())
        for url in self.urls():
            with self.subTest(url=url, user="logged in"):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_unknown_post_and_user_return_404(self):
        make_user("alice")  # người dùng thật: Stage 1 chỉ có hồ sơ demo
        self.assertEqual(self.client.get(reverse("community:post", args=[999])).status_code, 404)
        self.assertEqual(self.client.get(reverse("community:profile", args=["nobody"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("community:profile", args=["alice"])).status_code, 404)

    def test_feed_shows_mock_posts_banner_and_nav_link(self):
        resp = self.client.get(FEED)
        self.assertContains(resp, "multi-stage build")
        self.assertContains(resp, "Bản demo:")
        self.assertContains(resp, f'href="{FEED}"')

    def test_tag_filter_case_insensitive(self):
        resp = self.client.get(FEED, {"tag": "docker"})
        ids = sorted(p.id for p in resp.context["page_obj"])
        self.assertEqual(ids, [5, 7])

    def test_out_of_range_page_is_clamped(self):
        resp = self.client.get(FEED, {"page": 99})
        page = resp.context["page_obj"]
        self.assertEqual(page.number, page.paginator.num_pages)

    def test_newest_first(self):
        posts = list(self.client.get(FEED).context["page_obj"])
        self.assertEqual([p.created_at for p in posts], sorted((p.created_at for p in posts), reverse=True))

    def test_anonymous_gets_login_prompt_member_gets_composer(self):
        resp = self.client.get(FEED)
        self.assertContains(resp, "Đăng nhập để đăng bài")
        self.assertNotContains(resp, "data-composer")
        self.assertNotContains(resp, 'data-action="like"')
        self.client.force_login(make_user())
        resp = self.client.get(FEED)
        self.assertContains(resp, "data-composer")
        self.assertContains(resp, 'data-action="like"')

    def test_post_body_is_escaped(self):
        with patch.object(mock_data, "POSTS", [_post(body="<script>alert(1)</script>")]), \
             patch.object(mock_data, "COMMENTS", []):
            resp = self.client.get(FEED)
        self.assertContains(resp, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(resp, "<script>alert(1)</script>")

    def test_empty_feed_renders_empty_state(self):
        with patch.object(mock_data, "POSTS", []), patch.object(mock_data, "COMMENTS", []):
            resp = self.client.get(FEED)
        self.assertContains(resp, "Chưa có bài viết nào")

    def test_tag_links_to_jobs(self):
        resp = self.client.get(reverse("community:post", args=[1]))
        self.assertContains(resp, f'{reverse("jobs:list")}?q=Python')

    def test_job_link_chip_shows_existing_job_only(self):
        job = make_job("Backend Python Developer")
        with patch.object(mock_data, "POSTS", [_post(id=1, job_id=job.pk), _post(id=2, job_id=999999)]), \
             patch.object(mock_data, "COMMENTS", []):
            resp = self.client.get(FEED)
        self.assertContains(resp, "Backend Python Developer", count=1)
        self.assertContains(resp, "cm-job-chip", count=1)

    def test_profile_shows_public_fields_and_own_posts(self):
        resp = self.client.get(reverse("community:profile", args=["huy.dev"]))
        self.assertContains(resp, "Junior Backend Developer")
        self.assertTrue(all(p.author.username == "huy.dev" for p in resp.context["posts"]))
        self.assertEqual(resp.context["counts"]["posts"], 2)

    def test_query_count(self):
        with self.assertNumQueries(0):
            self.client.get(FEED)


@override_settings(COMMUNITY_DEMO=False)
class CommunityDisabledTests(TestCase):
    def test_flag_off_returns_404_and_hides_nav(self):
        self.assertEqual(self.client.get(FEED).status_code, 404)
        self.assertEqual(self.client.get(reverse("community:post", args=[1])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("core:home")), f'href="{FEED}"')
