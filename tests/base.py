import io
import os
import sqlite3
import tempfile
import unittest

import config
import db
from app import app

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_PHOTO_DIR = os.path.join(ROOT_DIR, "test_photos")
PASSWORD = "secret-password"

# minimal bytes that start like a JPEG file
FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database = config.database
        config.database = os.path.join(self.temp_dir.name, "test.db")

        con = sqlite3.connect(config.database)
        with open(os.path.join(ROOT_DIR, "schema.sql"), encoding="utf-8") as file:
            con.executescript(file.read())
        con.close()

        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        config.database = self.original_database
        self.temp_dir.cleanup()

    def query(self, sql, params=[]):
        with app.app_context():
            return db.query(sql, params)

    def execute(self, sql, params=[]):
        with app.app_context():
            db.execute(sql, params)

    def register(self, username, password=PASSWORD, password2=None):
        if password2 is None:
            password2 = password
        return self.client.post("/create", data={
            "username": username,
            "password1": password,
            "password2": password2,
        })

    def login(self, username, password=PASSWORD):
        return self.client.post("/login", data={
            "username": username,
            "password": password,
        })

    def logout(self):
        return self.client.get("/logout")

    def csrf_token(self):
        with self.client.session_transaction() as session:
            return session.get("csrf_token", "")

    def upload_photo(self, description="A photo", tags="", image=FAKE_JPEG,
                     filename="photo.jpg", csrf_token=None):
        if csrf_token is None:
            csrf_token = self.csrf_token()
        return self.client.post("/create_photo", data={
            "description": description,
            "tags": tags,
            "image": (io.BytesIO(image), filename),
            "csrf_token": csrf_token,
        }, content_type="multipart/form-data")

    def add_photo(self, description="A photo", tags=""):
        response = self.upload_photo(description=description, tags=tags)
        self.assertEqual(response.status_code, 302)
        return int(response.headers["Location"].split("/")[-1])

    def post(self, url, data):
        data = dict(data)
        data["csrf_token"] = self.csrf_token()
        return self.client.post(url, data=data)
