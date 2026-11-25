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
        response = self.register("maija")
        self.assertIn(b"Username already in use, pick another one", response.data)
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 1)

    def test_username_length(self):
        response = self.register("")
        self.assertIn(b"Username must be 1-30 characters long", response.data)
        response = self.register("a" * 31)
        self.assertIn(b"Username must be 1-30 characters long", response.data)
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 0)

        self.assertEqual(self.register("a" * 30).headers["Location"], "/")
        self.logout()
        self.assertEqual(self.register("b").headers["Location"], "/")

    def test_password_length(self):
        response = self.register("maija", "a" * 9)
        self.assertIn(b"Password must be 10-30 characters long", response.data)
        response = self.register("maija", "a" * 31)
        self.assertIn(b"Password must be 10-30 characters long", response.data)
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 0)

        self.assertEqual(self.register("maija", "a" * 10).headers["Location"], "/")
        self.logout()
        self.assertEqual(self.register("uolevi", "a" * 30).headers["Location"], "/")

    def test_passwords_must_match(self):
        response = self.register("maija", PASSWORD, PASSWORD + "x")
        self.assertIn(b"Passwords do not match", response.data)
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 0)

    def test_failed_registration_keeps_inputs(self):
        cases = [
            ("a" * 31, PASSWORD, PASSWORD),
            ("maija", "a" * 9, "a" * 9),
            ("maija", PASSWORD, PASSWORD + "x"),
        ]
        for username, password1, password2 in cases:
            response = self.register(username, password1, password2)
            self.assertEqual(response.status_code, 200)
            html = response.data.decode()
            self.assertIn('name="username" id="username" value="' + username + '"', html)
            self.assertIn('name="password1" id="password1" value="' + password1 + '"', html)
            self.assertIn('name="password2" id="password2" value="' + password2 + '"', html)

    def test_username_in_use_keeps_inputs(self):
        self.register("maija")
        self.logout()
        response = self.register("maija", PASSWORD, PASSWORD)
        html = response.data.decode()
        self.assertIn('id="username" value="maija"', html)
        self.assertIn('id="password1" value="' + PASSWORD + '"', html)
        self.assertIn('id="password2" value="' + PASSWORD + '"', html)

    def test_failed_registration_escapes_inputs(self):
        response = self.register('"><b>x', "a" * 9, "a" * 9)
        self.assertIn(b'value="&#34;&gt;&lt;b&gt;x"', response.data)

    def test_register_page_fields_are_empty(self):
        response = self.client.get("/register")
        self.assertIn(b'id="username" value=""', response.data)
        self.assertIn(b'id="password1" value=""', response.data)

    def test_register_page(self):
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'action="/create"', response.data)

    def test_register_page_has_log_in_button(self):
        html = self.client.get("/register").data.decode()
        self.assertIn('<a href="/login" class="button">go to log in</a>', html)
        self.assertLess(html.index('value="create account"'), html.index("go to log in"))

    def test_failed_registration_has_log_in_button(self):
        response = self.register("maija", PASSWORD, PASSWORD + "x")
        self.assertIn(b"go to log in", response.data)

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
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Wrong username or password", response.data)
        self.assertIn(b'id="username" value="maija"', response.data)
        self.assertIn(b'id="password" value="wrong-password"', response.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_login_unknown_user(self):
        response = self.login("uolevi")
        self.assertIn(b"Wrong username or password", response.data)
        self.assertIn(b'id="username" value="uolevi"', response.data)
        self.assertIn(b'id="password" value="' + PASSWORD.encode() + b'"', response.data)

    def test_login_page_fields_are_empty(self):
        response = self.client.get("/login")
        self.assertIn(b'id="username" value=""', response.data)
        self.assertIn(b'id="password" value=""', response.data)

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

    def test_sign_up_link_is_left_of_log_in(self):
        self.logout()
        data = self.client.get("/").data.decode()
        right = data[data.index('class="nav-right"'):data.index("</nav>")]
        self.assertIn('<a href="/register">sign up</a>', right)
        self.assertLess(right.index('href="/register"'), right.index('href="/login"'))

        response = self.client.get("/register")
        self.assertNotIn(b"sign up", response.data)
        response = self.client.get("/login")
        self.assertNotIn(b"sign up", response.data)

        self.login("maija")
        response = self.client.get("/")
        self.assertNotIn(b"sign up", response.data)

    def test_own_links_are_left_of_log_out(self):
        self.login("maija")
        data = self.client.get("/").data.decode()
        right = data[data.index('class="nav-right"'):data.index("</nav>")]
        left = data[data.index('class="nav-left"'):data.index('class="nav-center"')]
        self.assertIn('href="/latest"', left)
        self.assertNotIn('href="/my_photos"', left)
        self.assertLess(right.index('href="/my_photos"'), right.index('href="/my_collections"'))
        self.assertLess(right.index('href="/my_collections"'), right.index('href="/logout"'))
