from tests.base import BaseTestCase, PASSWORD

class TestRegister(BaseTestCase):
    def test_register_logs_in_and_redirects_to_index(self):
        response = self.register("maija")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        with self.client.session_transaction() as session:
            self.assertEqual(session["username"], "maija")
            self.assertIn("user_id", session)
            self.assertIn("csrf_token", session)

    def test_password_is_stored_as_hash(self):
        self.register("maija")
        password_hash = self.query("SELECT password_hash FROM users")[0][0]
        self.assertNotEqual(password_hash, PASSWORD)

    def test_username_already_in_use(self):
        self.register("maija")
        self.logout()
        self.register("maija")
        response = self.client.get("/register")
        self.assertIn(b"Username already in use, pick another one", response.data)
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 1)

    def test_username_length(self):
        response = self.register("")
        self.assertEqual(response.headers["Location"], "/register")
        response = self.register("a" * 31)
        self.assertEqual(response.headers["Location"], "/register")
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 0)

        self.assertEqual(self.register("a" * 30).headers["Location"], "/")
        self.logout()
        self.assertEqual(self.register("b").headers["Location"], "/")

    def test_password_length(self):
        self.assertEqual(self.register("maija", "a" * 9).headers["Location"], "/register")
        self.assertEqual(self.register("maija", "a" * 31).headers["Location"], "/register")
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 0)

        self.assertEqual(self.register("maija", "a" * 10).headers["Location"], "/")
        self.logout()
        self.assertEqual(self.register("uolevi", "a" * 30).headers["Location"], "/")

    def test_passwords_must_match(self):
        response = self.register("maija", PASSWORD, PASSWORD + "x")
        self.assertEqual(response.headers["Location"], "/register")
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 0)

    def test_register_page(self):
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'action="/create"', response.data)

class TestLogin(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")
        self.logout()

    def test_login_success(self):
        response = self.login("maija")
        self.assertEqual(response.headers["Location"], "/")
        with self.client.session_transaction() as session:
            self.assertEqual(session["username"], "maija")

    def test_login_wrong_password(self):
        response = self.login("maija", "wrong-password")
        self.assertEqual(response.headers["Location"], "/login")
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_login_unknown_user(self):
        response = self.login("uolevi")
        self.assertEqual(response.headers["Location"], "/login")

    def test_logout(self):
        self.login("maija")
        self.logout()
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_login_page_has_register_button_and_no_side_buttons(self):
        response = self.client.get("/login")
        self.assertIn(b'href="/register"', response.data)
        self.assertNotIn(b'href="/latest"', response.data)
        self.assertNotIn(b'href="/login"', response.data)

    def test_navigation_depends_on_login(self):
        response = self.client.get("/")
        self.assertIn(b"log in", response.data)
        self.assertNotIn(b"my photos", response.data)

        self.login("maija")
        response = self.client.get("/")
        self.assertIn(b"log out", response.data)
        self.assertIn(b"my photos", response.data)
