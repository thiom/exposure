import unittest

import tags
from app import app
from tests.base import BaseTestCase

class TestTagTitles(unittest.TestCase):
    def test_normalize_title(self):
        self.assertEqual(tags.normalize_title("  Black  and White "), "black and white")
        self.assertEqual(tags.normalize_title("Åland"), "åland")
        self.assertEqual(tags.normalize_title("long-exposure"), "long-exposure")
        self.assertEqual(tags.normalize_title("a" * 20), "a" * 20)

    def test_invalid_titles(self):
        self.assertIsNone(tags.normalize_title(""))
        self.assertIsNone(tags.normalize_title("   "))
        self.assertIsNone(tags.normalize_title("a" * 21))
        self.assertIsNone(tags.normalize_title("<script>"))
        self.assertIsNone(tags.normalize_title("a,b"))

    def test_parse_titles(self):
        self.assertEqual(tags.parse_titles(""), [])
        self.assertEqual(tags.parse_titles("Sea, sky ,, sea"), ["sea", "sky"])
        self.assertIsNone(tags.parse_titles("sea, s&ky"))

class TagTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")

    def tag_titles(self, photo_id):
        with app.app_context():
            return [tag["title"] for tag in tags.get_tags(photo_id)]

    def all_tags(self):
        return [row[0] for row in self.query("SELECT title FROM tags ORDER BY title")]

    def add_tag(self, photo_id, title):
        return self.post("/add_tag", {"photo_id": photo_id, "title": title})

    def remove_tag(self, photo_id, title):
        tag_id = self.query("SELECT id FROM tags WHERE title = ?", [title])[0][0]
        return self.post("/remove_tag", {"photo_id": photo_id, "tag_id": tag_id})

class TestAddTags(TagTestCase):
    def test_add_tags_with_new_photo(self):
        photo_id = self.add_photo(tags="Sea, sky")
        self.assertEqual(self.tag_titles(photo_id), ["sea", "sky"])

    def test_invalid_tags_with_new_photo(self):
        response = self.upload_photo(tags="sea, a" + "b" * 20)
        self.assertEqual(response.headers["Location"], "/new_photo")
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 0)

    def test_at_most_20_tags_with_new_photo(self):
        titles = ", ".join("tag" + str(i) for i in range(21))
        response = self.upload_photo(tags=titles)
        self.assertEqual(response.headers["Location"], "/new_photo")

        titles = ", ".join("tag" + str(i) for i in range(20))
        photo_id = self.add_photo(tags=titles)
        self.assertEqual(len(self.tag_titles(photo_id)), 20)

    def test_existing_tag_is_reused(self):
        first_id = self.add_photo(tags="sea")
        self.logout()
        self.register("uolevi")
        second_id = self.add_photo(tags="SEA")
        self.add_tag(second_id, "Sea")

        self.assertEqual(self.all_tags(), ["sea"])
        self.assertEqual(self.tag_titles(first_id), ["sea"])
        self.assertEqual(self.tag_titles(second_id), ["sea"])

    def test_add_tag_when_editing(self):
        photo_id = self.add_photo()
        response = self.add_tag(photo_id, "forest")
        self.assertEqual(response.headers["Location"], "/tags/" + str(photo_id))
        self.assertEqual(self.tag_titles(photo_id), ["forest"])

    def test_add_invalid_tag(self):
        photo_id = self.add_photo()
        self.add_tag(photo_id, "")
        self.add_tag(photo_id, "x" * 21)
        self.assertEqual(self.tag_titles(photo_id), [])

    def test_at_most_20_tags_when_editing(self):
        photo_id = self.add_photo(tags=", ".join("tag" + str(i) for i in range(20)))
        self.add_tag(photo_id, "one too many")
        self.assertEqual(len(self.tag_titles(photo_id)), 20)
        self.assertNotIn("one too many", self.all_tags())

        response = self.client.get("/tags/" + str(photo_id))
        self.assertNotIn(b'name="query"', response.data)

    def test_only_owner_can_change_tags(self):
        photo_id = self.add_photo(tags="sea")
        self.logout()
        self.register("uolevi")
        self.assertEqual(self.client.get("/tags/" + str(photo_id)).status_code, 403)
        self.assertEqual(self.add_tag(photo_id, "hacked").status_code, 403)
        self.assertEqual(self.remove_tag(photo_id, "sea").status_code, 403)
        self.assertEqual(self.tag_titles(photo_id), ["sea"])

    def test_tag_changes_require_csrf_token(self):
        photo_id = self.add_photo()
        response = self.client.post("/add_tag", data={
            "photo_id": photo_id, "title": "sea", "csrf_token": "wrong"
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.tag_titles(photo_id), [])

class TestFuzzySearch(TagTestCase):
    def setUp(self):
        super().setUp()
        self.photo_id = self.add_photo(tags="landscape, portrait, street, black and white")

    def find(self, query):
        with app.app_context():
            return [tag["title"] for tag in tags.find_tags(query)]

    def test_exact_and_prefix_matches(self):
        self.assertEqual(self.find("landscape")[0], "landscape")
        self.assertEqual(self.find("Port")[0], "portrait")

    def test_substring_match(self):
        self.assertIn("black and white", self.find("white"))

    def test_typo_match(self):
        self.assertEqual(self.find("lanscape")[0], "landscape")
        self.assertEqual(self.find("streat")[0], "street")

    def test_no_match(self):
        self.assertEqual(self.find("xyz"), [])
        self.assertEqual(self.find(""), [])

    def test_tag_page_suggests_existing_tags(self):
        other_id = self.add_photo()
        response = self.client.get("/tags/" + str(other_id) + "?query=lanscape")
        self.assertIn(b'value="#landscape"', response.data)
        self.assertIn(b"create #lanscape", response.data)

    def test_tag_page_does_not_offer_creating_existing_tag(self):
        other_id = self.add_photo()
        response = self.client.get("/tags/" + str(other_id) + "?query=Landscape")
        self.assertIn(b'value="#landscape"', response.data)
        self.assertNotIn(b"create #", response.data)

    def test_tag_page_hides_tags_already_on_photo(self):
        response = self.client.get("/tags/" + str(self.photo_id) + "?query=landscape")
        self.assertNotIn(b'value="#landscape"', response.data)

class TestRemoveTags(TagTestCase):
    def test_removed_tag_is_kept_when_used_elsewhere(self):
        first_id = self.add_photo(tags="sea")
        self.add_photo(tags="sea")
        self.remove_tag(first_id, "sea")
        self.assertEqual(self.tag_titles(first_id), [])
        self.assertEqual(self.all_tags(), ["sea"])

    def test_removed_tag_is_deleted_when_unused(self):
        photo_id = self.add_photo(tags="sea, sky")
        self.remove_tag(photo_id, "sea")
        self.assertEqual(self.all_tags(), ["sky"])

    def test_removing_photo_deletes_only_unused_tags(self):
        first_id = self.add_photo(tags="sea, sky")
        self.add_photo(tags="sky")
        self.post("/remove_photo/" + str(first_id), {"remove": "delete photo"})
        self.assertEqual(self.all_tags(), ["sky"])
        self.assertEqual(self.query("SELECT COUNT(*) FROM photo_tags")[0][0], 1)

class TestTagViews(TagTestCase):
    def test_tags_are_links_in_photo_view(self):
        photo_id = self.add_photo(tags="sea")
        tag_id = self.query("SELECT id FROM tags")[0][0]
        response = self.client.get("/photo/" + str(photo_id))
        self.assertIn(('href="/tag/' + str(tag_id) + '"').encode(), response.data)

    def test_tag_view_lists_photos_with_tag(self):
        sea_id = self.add_photo(tags="sea")
        sky_id = self.add_photo(tags="sky")
        tag_id = self.query("SELECT id FROM tags WHERE title = 'sea'")[0][0]
        self.logout()

        response = self.client.get("/tag/" + str(tag_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"#sea", response.data)
        self.assertIn(b"/image/" + str(sea_id).encode() + b'"', response.data)
        self.assertNotIn(b"/image/" + str(sky_id).encode() + b'"', response.data)

    def test_missing_tag(self):
        self.assertEqual(self.client.get("/tag/999").status_code, 404)
