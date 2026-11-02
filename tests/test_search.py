from tests.base import BaseTestCase

class TestSearch(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")
        self.sunset_id = self.add_photo(description="Sunset over the lake", tags="nature")
        self.city_id = self.add_photo(description="Rainy evening", tags="street, city")
        self.logout()
        self.register("uolevi")

    def image(self, photo_id):
        return b'src="/image/' + str(photo_id).encode() + b'"'

    def test_index_has_search_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'action="/search"', response.data)

    def test_search_by_description(self):
        response = self.client.get("/search?query=sunset")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.image(self.sunset_id), response.data)
        self.assertNotIn(self.image(self.city_id), response.data)

    def test_search_by_tag(self):
        response = self.client.get("/search?query=street")
        self.assertIn(self.image(self.city_id), response.data)
        self.assertNotIn(self.image(self.sunset_id), response.data)

    def test_photo_with_many_matching_tags_is_listed_once(self):
        response = self.client.get("/search?query=t")
        self.assertEqual(response.data.count(self.image(self.city_id)), 1)

    def test_search_without_login(self):
        self.logout()
        response = self.client.get("/search?query=lake")
        self.assertIn(self.image(self.sunset_id), response.data)

    def test_no_results_stays_on_index(self):
        response = self.client.get("/search?query=mountain")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No photos found", response.data)
        self.assertIn(b'value="mountain"', response.data)
        self.assertNotIn(b'src="/image/', response.data)

    def test_empty_query_redirects_to_index(self):
        response = self.client.get("/search?query=")
        self.assertEqual(response.headers["Location"], "/")

    def test_query_is_not_sql(self):
        response = self.client.get("/search?query=%27%20OR%201=1%20--")
        self.assertIn(b"No photos found", response.data)
