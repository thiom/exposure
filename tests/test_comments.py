import photos
from tests.base import BaseTestCase

class TestComments(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")
        self.photo_id = self.add_photo()
        self.url = "/photo/" + str(self.photo_id)

    def comment(self, content, **fields):
        data = {"photo_id": self.photo_id, "content": content}
        data.update(fields)
        return self.post("/create_comment", data)

    def comment_count(self):
        return self.query("SELECT COUNT(*) FROM comments")[0][0]

    def test_comment_own_photo(self):
        response = self.comment("Nice light")
        self.assertEqual(response.status_code, 302)
        row = self.query("SELECT content, sent_at, user_id, photo_id FROM comments")[0]
        self.assertEqual(row["content"], "Nice light")
        self.assertEqual(row["photo_id"], self.photo_id)
        self.assertIsNotNone(row["sent_at"])

    def test_comment_other_users_photo(self):
        self.logout()
        self.register("uolevi")
        self.comment("Great shot")
        response = self.client.get(self.url)
        self.assertIn(b"Great shot", response.data)
        self.assertIn(b"uolevi", response.data)

    def test_comments_are_shown_in_order(self):
        self.comment("first")
        self.comment("second")
        response = self.client.get(self.url)
        self.assertLess(response.data.index(b"first"), response.data.index(b"second"))

    def test_comments_are_not_shown_in_lists(self):
        self.comment("Hidden in lists")
        for url in ["/latest", "/my_photos", "/search?query=photo"]:
            self.assertNotIn(b"Hidden in lists", self.client.get(url).data, msg=url)

    def test_comment_length(self):
        self.assertEqual(self.comment("").status_code, 403)
        self.assertEqual(self.comment("   ").status_code, 403)
        self.assertEqual(self.comment("a" * 201).status_code, 403)
        self.assertEqual(self.comment_count(), 0)
        self.assertEqual(self.comment("a").status_code, 302)
        self.assertEqual(self.comment("a" * 200).status_code, 302)
        self.assertEqual(self.comment_count(), 2)

    def test_comment_is_escaped(self):
        self.comment("<script>alert(1)</script>")
        response = self.client.get(self.url)
        self.assertNotIn(b"<script>alert(1)</script>", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)

    def test_max_100_comments(self):
        self.assertEqual(photos.MAX_COMMENTS_PER_PHOTO, 100)
        user_id = self.query("SELECT id FROM users")[0][0]
        for i in range(100):
            self.execute("INSERT INTO comments (photo_id, user_id, content) VALUES (?, ?, ?)",
                         [self.photo_id, user_id, "comment " + str(i)])
        response = self.comment("one too many")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.comment_count(), 100)
        response = self.client.get(self.url)
        self.assertIn(b"maximum of 100 comments", response.data)
        self.assertNotIn(b'action="/create_comment"', response.data)

    def test_comment_requires_login(self):
        self.logout()
        response = self.client.post("/create_comment", data={
            "photo_id": self.photo_id, "content": "anonymous"
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.comment_count(), 0)

    def test_comment_form_only_when_logged_in(self):
        self.assertIn(b'action="/create_comment"', self.client.get(self.url).data)
        self.logout()
        response = self.client.get(self.url)
        self.assertNotIn(b'action="/create_comment"', response.data)
        self.assertIn(b"log in to comment", response.data)

    def test_comment_requires_csrf_token(self):
        response = self.client.post("/create_comment", data={
            "photo_id": self.photo_id, "content": "x", "csrf_token": "wrong"
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.comment_count(), 0)

    def test_comment_missing_photo(self):
        response = self.post("/create_comment", {"photo_id": 999, "content": "x"})
        self.assertEqual(response.status_code, 404)

    def test_redirect_keeps_back_url(self):
        response = self.comment("x", back="/latest/2")
        self.assertEqual(response.headers["Location"],
                         self.url + "?back=/latest/2#comments")

    def test_redirect_rejects_external_urls(self):
        response = self.comment("x", back="//evil.example")
        self.assertEqual(response.headers["Location"], self.url + "?back=/#comments")
        response = self.comment("x", redirect="https://evil.example")
        self.assertEqual(response.headers["Location"], self.url + "?back=/#comments")

    def test_comment_from_edit_view(self):
        response = self.client.get("/edit_photo/" + str(self.photo_id))
        self.assertIn(b'action="/create_comment"', response.data)
        response = self.comment("x", redirect="/edit_photo/" + str(self.photo_id))
        self.assertEqual(response.headers["Location"],
                         "/edit_photo/" + str(self.photo_id) + "#comments")

    def test_comments_are_removed_with_photo(self):
        self.comment("x")
        self.logout()
        self.register("uolevi")
        self.comment("y")
        self.logout()
        self.login("maija")
        self.post("/remove_photo/" + str(self.photo_id), {"remove": "delete photo"})
        self.assertEqual(self.comment_count(), 0)
