import photo_collections
from tests.base import BaseTestCase

class CollectionTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")

    def draft(self):
        with self.client.session_transaction() as session:
            return session.get("collection_draft")

    def update_draft(self, title="", description="", **button):
        data = {"title": title, "description": description}
        data.update(button)
        return self.post("/update_collection_draft", data)

    def create_collection(self, photo_ids, title="Summer", description="Lakes and forests"):
        self.client.get("/new_collection")
        for photo_id in photo_ids:
            self.update_draft(title, description, add=photo_id)
        response = self.update_draft(title, description, save="1")
        self.assertEqual(response.status_code, 302)
        return int(response.headers["Location"].split("/")[-1])

    def collection_photo_ids(self, collection_id):
        sql = """SELECT photo_id FROM collection_photos
                 WHERE collection_id = ? ORDER BY position"""
        return [row[0] for row in self.query(sql, [collection_id])]

    def collection_count(self):
        return self.query("SELECT COUNT(*) FROM collections")[0][0]

    def insert_collections(self, count, title="collection", user_id=1, photo_id=1):
        for i in range(count):
            self.execute("""INSERT INTO collections (user_id, title, description, date_time_added)
                            VALUES (?, ?, '', datetime('now', ?))""",
                         [user_id, title + " " + str(i), str(i) + " minutes"])
            collection_id = self.query("SELECT MAX(id) FROM collections")[0][0]
            self.execute("""INSERT INTO collection_photos (collection_id, photo_id, position)
                            VALUES (?, ?, 0)""", [collection_id, photo_id])

class TestCreateCollection(CollectionTestCase):
    def test_create_collection(self):
        first = self.add_photo("first")
        second = self.add_photo("second")
        collection_id = self.create_collection([first, second])

        row = self.query("SELECT * FROM collections WHERE id = ?", [collection_id])[0]
        self.assertEqual(row["title"], "Summer")
        self.assertEqual(row["description"], "Lakes and forests")
        self.assertEqual(row["user_id"], 1)
        self.assertIsNotNone(row["date_time_added"])
        self.assertEqual(self.collection_photo_ids(collection_id), [first, second])
        self.assertIsNone(self.draft())

    def test_new_collection_page(self):
        photo_id = self.add_photo()
        response = self.client.get("/new_collection")
        self.assertEqual(response.headers["Location"], "/collection_draft")
        response = self.client.get("/collection_draft")
        self.assertIn(b"new collection", response.data)
        self.assertIn(b'name="title"', response.data)
        self.assertIn(b'name="add" value="' + str(photo_id).encode() + b'"', response.data)
        self.assertIn(b'href="/my_collections" class="button">cancel', response.data)
        data = response.data
        self.assertLess(data.index(b'name="save"'), data.index(b">cancel</a>"))
        self.assertLess(data.index(b'class="form-buttons"'), data.index(b'name="save"'))
        self.assertEqual(data.index(b'type="submit"'), data.index(b'type="submit" name="save"'))
        self.assertIn(b'formnovalidate class="add-plus"', data)
        self.assertNotIn(b">add</button>", data)

    def test_added_photo_leaves_the_list(self):
        first = self.add_photo()
        second = self.add_photo()
        self.client.get("/new_collection")
        response = self.update_draft(add=first)
        self.assertEqual(response.headers["Location"], "/collection_draft#selected")
        self.assertEqual(self.draft()["photo_ids"], [first])

        response = self.client.get("/collection_draft")
        self.assertNotIn(b'name="add" value="' + str(first).encode() + b'"', response.data)
        self.assertIn(b'name="add" value="' + str(second).encode() + b'"', response.data)
        self.assertIn(b'name="remove" value="' + str(first).encode() + b'"', response.data)

    def test_typed_text_is_kept_when_adding(self):
        photo_id = self.add_photo()
        self.client.get("/new_collection")
        self.update_draft("Winter", "Snow", add=photo_id)
        response = self.client.get("/collection_draft")
        self.assertIn(b'value="Winter"', response.data)
        self.assertIn(b">Snow</textarea>", response.data)

    def test_adding_twice_adds_once(self):
        photo_id = self.add_photo()
        self.client.get("/new_collection")
        self.update_draft(add=photo_id)
        self.update_draft(add=photo_id)
        self.assertEqual(self.draft()["photo_ids"], [photo_id])

    def test_remove_photo_from_draft(self):
        photo_id = self.add_photo()
        self.client.get("/new_collection")
        self.update_draft(add=photo_id)
        self.update_draft(remove=photo_id)
        self.assertEqual(self.draft()["photo_ids"], [])

    def test_reorder_photos(self):
        ids = [self.add_photo(), self.add_photo(), self.add_photo()]
        self.client.get("/new_collection")
        for photo_id in ids:
            self.update_draft(add=photo_id)
        self.update_draft(up=ids[2])
        self.assertEqual(self.draft()["photo_ids"], [ids[0], ids[2], ids[1]])
        self.update_draft(down=ids[0])
        self.assertEqual(self.draft()["photo_ids"], [ids[2], ids[0], ids[1]])
        self.update_draft(up=ids[2])
        self.update_draft(down=ids[1])
        self.assertEqual(self.draft()["photo_ids"], [ids[2], ids[0], ids[1]])

    def test_saved_order(self):
        ids = [self.add_photo(), self.add_photo()]
        self.client.get("/new_collection")
        for photo_id in ids:
            self.update_draft(add=photo_id)
        self.update_draft(up=ids[1])
        response = self.update_draft("Order", save="1")
        collection_id = int(response.headers["Location"].split("/")[-1])
        self.assertEqual(self.collection_photo_ids(collection_id), [ids[1], ids[0]])

    def test_new_collection_starts_empty(self):
        photo_id = self.add_photo()
        self.client.get("/new_collection")
        self.update_draft("Old", add=photo_id)
        self.client.get("/new_collection")
        self.assertEqual(self.draft()["photo_ids"], [])
        self.assertEqual(self.draft()["title"], "")

    def test_draft_without_session_redirects(self):
        response = self.client.get("/collection_draft")
        self.assertEqual(response.headers["Location"], "/my_collections")
        response = self.update_draft(save="1")
        self.assertEqual(response.headers["Location"], "/my_collections")

    def test_no_photos_message(self):
        self.client.get("/new_collection")
        response = self.client.get("/collection_draft")
        self.assertIn(b"You have no photos yet", response.data)

class TestCollectionValidation(CollectionTestCase):
    def test_title_is_required(self):
        photo_id = self.add_photo()
        self.client.get("/new_collection")
        self.update_draft(add=photo_id)
        for title in ["", "   "]:
            response = self.update_draft(title, save="1")
            self.assertEqual(response.headers["Location"], "/collection_draft")
        self.assertEqual(self.collection_count(), 0)
        self.assertIn(b"needs a title", self.client.get("/collection_draft").data)

    def test_title_length(self):
        photo_id = self.add_photo()
        self.client.get("/new_collection")
        self.update_draft(add=photo_id)
        response = self.update_draft("a" * 31, save="1")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.collection_count(), 0)
        collection_id = self.create_collection([photo_id], title="a" * 30)
        self.assertEqual(self.query("SELECT title FROM collections WHERE id = ?",
                                    [collection_id])[0][0], "a" * 30)

    def test_title_is_stripped(self):
        collection_id = self.create_collection([self.add_photo()], title="  Summer  ")
        self.assertEqual(self.query("SELECT title FROM collections WHERE id = ?",
                                    [collection_id])[0][0], "Summer")

    def test_description_is_optional(self):
        collection_id = self.create_collection([self.add_photo()], description="")
        self.assertEqual(self.query("SELECT description FROM collections WHERE id = ?",
                                    [collection_id])[0][0], "")

    def test_description_length(self):
        photo_id = self.add_photo()
        self.client.get("/new_collection")
        self.update_draft(add=photo_id)
        response = self.update_draft("Title", "a" * 201, save="1")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.collection_count(), 0)
        self.create_collection([photo_id], description="a" * 200)
        self.assertEqual(self.collection_count(), 1)

    def test_at_least_one_photo(self):
        self.add_photo()
        self.client.get("/new_collection")
        response = self.update_draft("Empty", save="1")
        self.assertEqual(response.headers["Location"], "/collection_draft")
        self.assertEqual(self.collection_count(), 0)
        self.assertIn(b"at least one photo", self.client.get("/collection_draft").data)

    def test_max_50_photos(self):
        self.assertEqual(photo_collections.MAX_PHOTOS_PER_COLLECTION, 50)
        photo_id = self.add_photo()
        for i in range(50):
            self.execute("INSERT INTO photos (user_id, description) VALUES (1, 'x')")
        ids = [row[0] for row in self.query("SELECT id FROM photos WHERE id != ?", [photo_id])]
        self.client.get("/new_collection")
        for i in ids:
            self.update_draft(add=i)
        self.update_draft(add=photo_id)
        self.assertEqual(len(self.draft()["photo_ids"]), 50)
        self.assertNotIn(photo_id, self.draft()["photo_ids"])
        self.assertIn(b"at most 50 photos", self.client.get("/collection_draft").data)

    def test_max_50_collections(self):
        self.assertEqual(photo_collections.MAX_COLLECTIONS_PER_USER, 50)
        photo_id = self.add_photo()
        self.insert_collections(49, photo_id=photo_id)
        self.create_collection([photo_id])
        self.assertEqual(self.collection_count(), 50)

        response = self.client.get("/new_collection")
        self.assertEqual(response.headers["Location"], "/my_collections")
        self.assertIn(b"maximum of 50 collections", self.client.get("/my_collections").data)

    def test_limit_is_checked_when_saving(self):
        photo_id = self.add_photo()
        self.insert_collections(49, photo_id=photo_id)
        self.client.get("/new_collection")
        self.update_draft("Last", add=photo_id)
        self.insert_collections(1, photo_id=photo_id)
        response = self.update_draft("Last", save="1")
        self.assertEqual(response.headers["Location"], "/my_collections")
        self.assertEqual(self.collection_count(), 50)

    def test_invalid_photo_id(self):
        self.client.get("/new_collection")
        self.assertEqual(self.update_draft(add="abc").status_code, 403)
        self.assertEqual(self.update_draft(add="999").status_code, 404)

class TestCollectionAccess(CollectionTestCase):
    def test_cannot_add_other_users_photo(self):
        self.logout()
        self.register("uolevi")
        other_photo = self.add_photo()
        self.logout()
        self.login("maija")
        self.client.get("/new_collection")
        response = self.update_draft(add=other_photo)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.draft()["photo_ids"], [])

    def test_other_users_photos_are_not_listed(self):
        self.logout()
        self.register("uolevi")
        other_photo = self.add_photo()
        self.logout()
        self.login("maija")
        self.client.get("/new_collection")
        response = self.client.get("/collection_draft")
        self.assertNotIn(b'name="add" value="' + str(other_photo).encode() + b'"', response.data)
        self.assertNotIn(b'src="/image/' + str(other_photo).encode() + b'"', response.data)

    def test_requires_login(self):
        self.logout()
        for url in ["/new_collection", "/collection_draft", "/my_collections",
                    "/edit_collection/1", "/remove_collection/1"]:
            self.assertEqual(self.client.get(url).status_code, 403, msg=url)
        response = self.client.post("/update_collection_draft",
                                    data={"title": "x", "description": "", "save": "1"})
        self.assertEqual(response.status_code, 403)

    def test_requires_csrf_token(self):
        photo_id = self.add_photo()
        self.client.get("/new_collection")
        response = self.client.post("/update_collection_draft", data={
            "title": "x", "description": "", "add": photo_id, "csrf_token": "wrong"
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.draft()["photo_ids"], [])

    def test_cannot_edit_or_remove_other_users_collection(self):
        collection_id = self.create_collection([self.add_photo()])
        self.logout()
        self.register("uolevi")
        for url in ["/edit_collection/", "/remove_collection/"]:
            response = self.client.get(url + str(collection_id))
            self.assertEqual(response.status_code, 403, msg=url)
        response = self.post("/remove_collection/" + str(collection_id), {"remove": "x"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.collection_count(), 1)

        response = self.client.get("/collection/" + str(collection_id))
        self.assertNotIn(b"/edit_collection/", response.data)

    def test_missing_collection(self):
        self.assertEqual(self.client.get("/collection/999").status_code, 404)
        self.assertEqual(self.client.get("/edit_collection/999").status_code, 404)
        self.assertEqual(self.client.get("/remove_collection/999").status_code, 404)

    def test_logout_clears_draft(self):
        self.client.get("/new_collection")
        self.logout()
        self.assertIsNone(self.draft())

class TestEditCollection(CollectionTestCase):
    def test_edit_collection(self):
        first = self.add_photo()
        second = self.add_photo()
        third = self.add_photo()
        collection_id = self.create_collection([first, second])

        response = self.client.get("/edit_collection/" + str(collection_id))
        self.assertEqual(response.headers["Location"], "/collection_draft")
        self.assertEqual(self.draft()["photo_ids"], [first, second])

        response = self.client.get("/collection_draft")
        self.assertIn(b"edit collection", response.data)
        self.assertIn(b'value="Summer"', response.data)
        cancel = 'href="/collection/' + str(collection_id) + '" class="button">cancel'
        self.assertIn(cancel.encode(), response.data)
        self.assertIn(b"delete collection", response.data)

        self.update_draft("Autumn", "Leaves", remove=first)
        self.update_draft("Autumn", "Leaves", add=third)
        response = self.update_draft("Autumn", "Leaves", save="1")
        self.assertEqual(response.headers["Location"], "/collection/" + str(collection_id))

        row = self.query("SELECT title, description FROM collections WHERE id = ?",
                         [collection_id])[0]
        self.assertEqual((row["title"], row["description"]), ("Autumn", "Leaves"))
        self.assertEqual(self.collection_photo_ids(collection_id), [second, third])
        self.assertEqual(self.collection_count(), 1)

    def test_cancel_does_not_save(self):
        photo_id = self.add_photo()
        collection_id = self.create_collection([photo_id])
        self.client.get("/edit_collection/" + str(collection_id))
        self.update_draft("Changed", remove=photo_id)
        self.assertEqual(self.collection_photo_ids(collection_id), [photo_id])
        self.client.get("/edit_collection/" + str(collection_id))
        self.assertEqual(self.draft()["photo_ids"], [photo_id])
        self.assertEqual(self.draft()["title"], "Summer")

    def test_edit_cannot_leave_collection_empty(self):
        photo_id = self.add_photo()
        collection_id = self.create_collection([photo_id])
        self.client.get("/edit_collection/" + str(collection_id))
        self.update_draft("Summer", remove=photo_id)
        response = self.update_draft("Summer", save="1")
        self.assertEqual(response.headers["Location"], "/collection_draft")
        self.assertEqual(self.collection_photo_ids(collection_id), [photo_id])

class TestRemoveCollection(CollectionTestCase):
    def test_remove_collection(self):
        photo_id = self.add_photo()
        collection_id = self.create_collection([photo_id])
        url = "/remove_collection/" + str(collection_id)
        response = self.client.get(url)
        self.assertIn(b"Are you sure", response.data)

        response = self.post(url, {"remove": "delete collection"})
        self.assertEqual(response.headers["Location"], "/my_collections")
        self.assertEqual(self.collection_count(), 0)
        self.assertEqual(self.query("SELECT COUNT(*) FROM collection_photos")[0][0], 0)
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 1)

    def test_cancel_remove(self):
        collection_id = self.create_collection([self.add_photo()])
        url = "/remove_collection/" + str(collection_id)
        response = self.post(url, {"back": "cancel"})
        self.assertEqual(response.headers["Location"], "/collection/" + str(collection_id))
        self.client.get("/edit_collection/" + str(collection_id))
        response = self.post(url, {"back": "cancel"})
        self.assertEqual(response.headers["Location"], "/collection_draft")
        self.assertEqual(self.collection_count(), 1)

    def test_removing_last_photo_removes_collection(self):
        first = self.add_photo()
        second = self.add_photo()
        single = self.create_collection([first], title="Single")
        double = self.create_collection([first, second], title="Double")

        response = self.client.get("/remove_photo/" + str(first))
        self.assertIn(b"Single", response.data)
        self.assertNotIn(b"Double", response.data)

        self.post("/remove_photo/" + str(first), {"remove": "delete photo"})
        self.assertEqual(self.client.get("/collection/" + str(single)).status_code, 404)
        self.assertEqual(self.collection_photo_ids(double), [second])

    def test_remove_photo_page_without_collections(self):
        photo_id = self.add_photo()
        response = self.client.get("/remove_photo/" + str(photo_id))
        self.assertNotIn(b"will be deleted too", response.data)

class TestShowCollection(CollectionTestCase):
    def test_show_collection(self):
        first = self.add_photo()
        second = self.add_photo()
        collection_id = self.create_collection([second, first])
        response = self.client.get("/collection/" + str(collection_id))
        self.assertIn(b"<h1>Summer</h1>", response.data)
        self.assertIn(b"Lakes and forests", response.data)
        self.assertLess(response.data.index(b'src="/image/' + str(second).encode()),
                        response.data.index(b'src="/image/' + str(first).encode()))
        date = self.query("SELECT date_time_added FROM collections")[0][0][:10]
        self.assertIn(b'class="collection-footer">' + date.encode(), response.data)
        self.assertIn(b"/edit_collection/" + str(collection_id).encode(), response.data)

    def test_photos_link_back_to_collection(self):
        photo_id = self.add_photo()
        collection_id = self.create_collection([photo_id])
        response = self.client.get("/collection/" + str(collection_id))
        link = "/photo/" + str(photo_id) + "?back=/collection/" + str(collection_id)
        self.assertIn(link.encode(), response.data)

    def test_anonymous_user_can_view(self):
        collection_id = self.create_collection([self.add_photo()])
        self.logout()
        response = self.client.get("/collection/" + str(collection_id))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"/edit_collection/", response.data)

    def test_collection_is_escaped(self):
        collection_id = self.create_collection([self.add_photo()], title="<b>x</b>",
                                               description="<i>y</i>")
        response = self.client.get("/collection/" + str(collection_id))
        self.assertIn(b"&lt;b&gt;x&lt;/b&gt;", response.data)
        self.assertIn(b"&lt;i&gt;y&lt;/i&gt;", response.data)
        self.assertNotIn(b"<b>x</b>", response.data)

class TestMyCollections(CollectionTestCase):
    def test_nav_link(self):
        self.assertIn(b'href="/my_collections"', self.client.get("/").data)
        self.logout()
        self.assertNotIn(b'href="/my_collections"', self.client.get("/").data)

    def test_empty(self):
        response = self.client.get("/my_collections")
        self.assertIn(b"not created any collections", response.data)
        self.assertIn(b'href="/new_collection" class="add-new"', response.data)
        self.assertNotIn(b"add new</a>", response.data)

    def test_single_collection_is_centered(self):
        photo_id = self.add_photo()
        self.create_collection([photo_id])
        response = self.client.get("/my_collections")
        self.assertIn(b'class="my-collections single"', response.data)
        self.assertIn(b'class="collection-list single"', response.data)

    def test_two_columns(self):
        photo_id = self.add_photo()
        self.create_collection([photo_id], title="One")
        self.create_collection([photo_id], title="Two")
        response = self.client.get("/my_collections")
        self.assertIn(b'class="my-collections"', response.data)
        self.assertIn(b'class="collection-list"', response.data)

    def test_card_contents(self):
        first = self.add_photo()
        second = self.add_photo()
        collection_id = self.create_collection([second, first])
        response = self.client.get("/my_collections")
        self.assertIn(b'href="/collection/' + str(collection_id).encode() + b'"', response.data)
        self.assertIn(b'src="/image/' + str(second).encode() + b'"', response.data)
        self.assertNotIn(b'src="/image/' + str(first).encode() + b'"', response.data)
        date = self.query("SELECT date_time_added FROM collections")[0][0][:10]
        self.assertIn(date.encode(), response.data)
        self.assertNotIn(b"by maija", response.data)
        data = response.data
        self.assertLess(data.index(b"Summer"), data.index(b"Lakes and forests"))
        self.assertLess(data.index(b"Lakes and forests"), data.index(date.encode()))

    def test_shows_only_own_collections(self):
        self.create_collection([self.add_photo()], title="Mine")
        self.logout()
        self.register("uolevi")
        self.create_collection([self.add_photo()], title="Theirs")
        response = self.client.get("/my_collections")
        self.assertIn(b"Theirs", response.data)
        self.assertNotIn(b"Mine", response.data)

class TestLatestCollections(CollectionTestCase):
    def test_tabs(self):
        response = self.client.get("/latest")
        self.assertIn(b'<a href="/latest" class="selected">photos</a>', response.data)
        self.assertIn(b'<a href="/collections">collections</a>', response.data)
        self.assertNotIn(b"latest photos</h1>", response.data)
        response = self.client.get("/collections")
        self.assertIn(b'<a href="/latest">photos</a>', response.data)
        self.assertIn(b'<a href="/collections" class="selected">collections</a>', response.data)

    def test_no_add_button(self):
        self.create_collection([self.add_photo()])
        response = self.client.get("/collections")
        self.assertNotIn(b'class="add-new"', response.data)

    def test_shows_collections_of_all_users(self):
        self.create_collection([self.add_photo()], title="Mine")
        self.logout()
        self.register("uolevi")
        self.create_collection([self.add_photo()], title="Theirs")
        self.logout()
        response = self.client.get("/collections")
        self.assertIn(b"by maija", response.data)
        self.assertIn(b"by uolevi", response.data)
        self.assertLess(response.data.index(b"Theirs"), response.data.index(b"Mine"))

    def test_empty(self):
        response = self.client.get("/collections")
        self.assertIn(b"no collections yet", response.data)

    def test_pagination(self):
        photo_id = self.add_photo()
        self.insert_collections(25, photo_id=photo_id)
        response = self.client.get("/collections")
        self.assertEqual(response.data.count(b'class="collection-card"'), 20)
        self.assertIn(b"collection 24<", response.data)
        self.assertIn(b"1 / 2", response.data)
        self.assertIn(b'href="/collections/2"', response.data)

        response = self.client.get("/collections/2")
        self.assertEqual(response.data.count(b'class="collection-card"'), 5)
        self.assertIn(b"collection 0<", response.data)

        self.assertEqual(self.client.get("/collections/0").headers["Location"], "/collections/1")
        self.assertEqual(self.client.get("/collections/9").headers["Location"], "/collections/2")

    def test_search_by_title_and_description(self):
        photo_id = self.add_photo()
        self.create_collection([photo_id], title="Lapland", description="Snow")
        self.create_collection([photo_id], title="Archipelago", description="Sea and islands")
        response = self.client.get("/collections?query=lap")
        self.assertIn(b"Lapland", response.data)
        self.assertNotIn(b"Archipelago", response.data)
        response = self.client.get("/collections?query=island")
        self.assertIn(b"Archipelago", response.data)
        self.assertNotIn(b"Lapland", response.data)
        self.assertIn(b'value="island"', response.data)

    def test_search_without_results(self):
        self.create_collection([self.add_photo()])
        response = self.client.get("/collections?query=nothing")
        self.assertIn(b"No collections found", response.data)

    def test_search_pagination_keeps_query(self):
        photo_id = self.add_photo()
        self.insert_collections(21, title="forest", photo_id=photo_id)
        self.insert_collections(5, title="city", photo_id=photo_id)
        response = self.client.get("/collections?query=forest")
        self.assertIn(b'href="/collections/2?query=forest"', response.data)
        response = self.client.get("/collections/2?query=forest")
        self.assertEqual(response.data.count(b'class="collection-card"'), 1)
        response = self.client.get("/collections/5?query=forest")
        self.assertEqual(response.headers["Location"], "/collections/2?query=forest")

    def test_search_form_on_collections_page(self):
        response = self.client.get("/collections")
        self.assertIn(b'action="/collections" method="get" class="search-form compact"',
                      response.data)

    def test_photo_search_form_on_latest_photos_page(self):
        response = self.client.get("/latest")
        self.assertIn(b'action="/search" method="get" class="search-form compact"',
                      response.data)
        self.assertIn(b'placeholder="search by tag or description"', response.data)

    def test_search_form_on_home_page_is_unchanged(self):
        response = self.client.get("/")
        self.assertIn(b'class="search-form"', response.data)
