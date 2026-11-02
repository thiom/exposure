import os
import unittest

import app as app_module
from tests.base import BaseTestCase, FAKE_JPEG, TEST_PHOTO_DIR

class TestAddPhoto(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")

    def test_new_photo_requires_login(self):
        self.logout()
        self.assertEqual(self.client.get("/new_photo").status_code, 403)
        self.assertEqual(self.upload_photo().status_code, 403)

    def test_add_photo_redirects_to_tag_page(self):
        response = self.upload_photo(description="Sunset")
        self.assertEqual(response.status_code, 302)
        photo_id = int(response.headers["Location"].split("/")[-1])
        self.assertEqual(response.headers["Location"], "/tags/" + str(photo_id))

        row = self.query("SELECT description, image, date_time_added FROM photos")[0]
        self.assertEqual(row["description"], "Sunset")
        self.assertEqual(bytes(row["image"]), FAKE_JPEG)
        self.assertIsNotNone(row["date_time_added"])

    def test_image_is_served_as_jpeg(self):
        photo_id = self.add_photo()
        response = self.client.get("/image/" + str(photo_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/jpeg")
        self.assertEqual(response.data, FAKE_JPEG)

    def test_accepts_jpg_and_jpeg_in_any_case(self):
        for filename in ["a.jpg", "b.jpeg", "c.JPG", "d.JPEG"]:
            self.assertEqual(self.upload_photo(filename=filename).status_code, 302)
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 4)

    def test_rejects_wrong_file_type(self):
        response = self.upload_photo(filename="photo.png")
        self.assertEqual(response.headers["Location"], "/new_photo")
        response = self.upload_photo(image=b"not a jpeg", filename="photo.jpg")
        self.assertEqual(response.headers["Location"], "/new_photo")
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 0)

    def test_rejects_too_large_image(self):
        original = app_module.MAX_IMAGE_SIZE
        app_module.MAX_IMAGE_SIZE = len(FAKE_JPEG) - 1
        try:
            response = self.upload_photo()
        finally:
            app_module.MAX_IMAGE_SIZE = original
        self.assertEqual(response.headers["Location"], "/new_photo")
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 0)

    def test_max_image_size_is_50_mb(self):
        self.assertEqual(app_module.MAX_IMAGE_SIZE, 50 * 1024 * 1024)

    def test_description_length(self):
        self.assertEqual(self.upload_photo(description="").status_code, 403)
        self.assertEqual(self.upload_photo(description="   ").status_code, 403)
        self.assertEqual(self.upload_photo(description="a" * 201).status_code, 403)
        self.assertEqual(self.upload_photo(description="a").status_code, 302)
        self.assertEqual(self.upload_photo(description="a" * 200).status_code, 302)

    def test_requires_csrf_token(self):
        self.assertEqual(self.upload_photo(csrf_token="wrong").status_code, 403)
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 0)

    def test_photo_limit_per_user(self):
        original = app_module.MAX_PHOTOS_PER_USER
        app_module.MAX_PHOTOS_PER_USER = 2
        try:
            self.add_photo()
            self.add_photo()
            self.assertEqual(self.upload_photo().status_code, 403)
            response = self.client.get("/new_photo")
            self.assertEqual(response.headers["Location"], "/my_photos")
        finally:
            app_module.MAX_PHOTOS_PER_USER = original
        self.assertEqual(app_module.MAX_PHOTOS_PER_USER, 500)

    def test_upload_real_test_photos(self):
        path = os.path.join(TEST_PHOTO_DIR, "test_photo_1.JPG")
        if not os.path.exists(path):
            raise unittest.SkipTest("test photo not available")
        with open(path, "rb") as file:
            image = file.read()
        response = self.upload_photo(image=image, filename="test_photo_1.JPG")
        self.assertEqual(response.status_code, 302)
        photo_id = response.headers["Location"].split("/")[-1]
        self.assertEqual(self.client.get("/image/" + photo_id).data, image)

class TestShowPhoto(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")
        self.photo_id = self.add_photo(description="Foggy morning")

    def test_show_photo(self):
        response = self.client.get("/photo/" + str(self.photo_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Foggy morning", response.data)
        self.assertIn(b"maija", response.data)

    def test_edit_button_only_for_owner(self):
        url = "/photo/" + str(self.photo_id)
        self.assertIn(b"/edit_photo/", self.client.get(url).data)
        self.logout()
        self.assertNotIn(b"/edit_photo/", self.client.get(url).data)
        self.register("uolevi")
        self.assertNotIn(b"/edit_photo/", self.client.get(url).data)

    def test_missing_photo(self):
        self.assertEqual(self.client.get("/photo/999").status_code, 404)
        self.assertEqual(self.client.get("/image/999").status_code, 404)

    def test_back_button(self):
        url = "/photo/" + str(self.photo_id)
        response = self.client.get(url + "?back=/search%3Fquery%3Dfog")
        self.assertIn(b'href="/search?query=fog"', response.data)
        response = self.client.get(url)
        self.assertIn(b'href="/" class="button">back', response.data)

    def test_back_button_rejects_external_urls(self):
        url = "/photo/" + str(self.photo_id)
        for back in ["https://evil.example", "//evil.example", "/\\evil.example"]:
            response = self.client.get(url, query_string={"back": back})
            self.assertIn(b'href="/" class="button">back', response.data)

    def test_photo_lists_link_back_to_list(self):
        response = self.client.get("/my_photos")
        self.assertIn(b"?back=/my_photos", response.data)

class TestEditPhoto(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")
        self.photo_id = self.add_photo(description="Old")

    def update(self, description):
        return self.post("/update_photo", {"photo_id": self.photo_id, "description": description})

    def test_edit_page(self):
        response = self.client.get("/edit_photo/" + str(self.photo_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"delete photo", response.data)
        self.assertIn(b"/tags/" + str(self.photo_id).encode(), response.data)

    def test_update_description(self):
        response = self.update("New")
        self.assertEqual(response.headers["Location"], "/photo/" + str(self.photo_id))
        self.assertEqual(self.query("SELECT description FROM photos")[0][0], "New")

    def test_update_validates_description(self):
        self.assertEqual(self.update("").status_code, 403)
        self.assertEqual(self.update("a" * 201).status_code, 403)
        self.assertEqual(self.query("SELECT description FROM photos")[0][0], "Old")

    def test_other_user_cannot_edit(self):
        self.logout()
        self.register("uolevi")
        self.assertEqual(self.client.get("/edit_photo/" + str(self.photo_id)).status_code, 403)
        self.assertEqual(self.update("Hacked").status_code, 403)
        self.assertEqual(self.query("SELECT description FROM photos")[0][0], "Old")

    def test_edit_requires_login(self):
        self.logout()
        self.assertEqual(self.client.get("/edit_photo/" + str(self.photo_id)).status_code, 403)

    def test_edit_missing_photo(self):
        self.assertEqual(self.client.get("/edit_photo/999").status_code, 404)

class TestRemovePhoto(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")
        self.photo_id = self.add_photo()
        self.url = "/remove_photo/" + str(self.photo_id)

    def test_confirmation_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Are you sure", response.data)

    def test_remove_photo(self):
        user_id = self.query("SELECT id FROM users")[0][0]
        self.execute("INSERT INTO comments (photo_id, user_id, content) VALUES (?, ?, ?)",
                   [self.photo_id, user_id, "Nice"])
        response = self.post(self.url, {"remove": "delete photo"})
        self.assertEqual(response.headers["Location"], "/my_photos")
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 0)
        self.assertEqual(self.client.get("/photo/" + str(self.photo_id)).status_code, 404)

    def test_cancel(self):
        response = self.post(self.url, {"back": "cancel"})
        self.assertEqual(response.headers["Location"], "/edit_photo/" + str(self.photo_id))
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 1)

    def test_requires_csrf_token(self):
        response = self.client.post(self.url, data={"remove": "x", "csrf_token": "wrong"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 1)

    def test_only_owner_can_remove(self):
        self.logout()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.register("uolevi")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.post(self.url, {"remove": "x"}).status_code, 403)
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 1)

class TestPhotoLists(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")

    def test_my_photos_shows_only_own_photos(self):
        other_id = self.add_photo()
        self.logout()
        self.register("uolevi")
        own_id = self.add_photo()

        response = self.client.get("/my_photos")
        self.assertIn(b"/image/" + str(own_id).encode() + b'"', response.data)
        self.assertNotIn(b"/image/" + str(other_id).encode() + b'"', response.data)
        self.assertIn(b'href="/new_photo"', response.data)

    def test_my_photos_requires_login(self):
        self.logout()
        self.assertEqual(self.client.get("/my_photos").status_code, 403)

    def test_latest_pagination(self):
        photo_ids = [self.add_photo() for _ in range(21)]
        self.logout()

        response = self.client.get("/latest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'<img src="/image/'), 20)
        self.assertIn(b"/image/" + str(photo_ids[-1]).encode() + b'"', response.data)
        self.assertIn(b"1 / 2", response.data)

        response = self.client.get("/latest/2")
        self.assertEqual(response.data.count(b'<img src="/image/'), 1)
        self.assertIn(b"/image/" + str(photo_ids[0]).encode() + b'"', response.data)

        self.assertEqual(self.client.get("/latest/0").headers["Location"], "/latest/1")
        self.assertEqual(self.client.get("/latest/9").headers["Location"], "/latest/2")

    def test_latest_without_photos(self):
        self.assertEqual(self.client.get("/latest").status_code, 200)
