import unittest

import photos
from app import app, show_number, show_shutter_speed
from tests.base import BaseTestCase

PANASONIC = {
    "camera": "Panasonic Lumix S9",
    "lens": "Panasonic Lumix S 24-105mm f/4 Macto O.I.S.",
    "focal_length": "50",
}

SONY = {
    "camera": "Sony a7 IV",
    "lens": "Sigma 24mm f/2 DG DN Contemporary",
    "focal_length": "24",
}

def details_form(**fields):
    form = {"camera": "", "lens": "", "focal_length": "", "aperture": "", "shutter_speed": ""}
    form.update(fields)
    return form

class TestParseText(unittest.TestCase):
    def test_camera_and_lens_values(self):
        self.assertEqual(photos.parse_text(PANASONIC["camera"]), "Panasonic Lumix S9")
        self.assertEqual(photos.parse_text(SONY["lens"]), "Sigma 24mm f/2 DG DN Contemporary")

    def test_empty_is_none(self):
        self.assertIsNone(photos.parse_text(""))
        self.assertIsNone(photos.parse_text("   "))

    def test_whitespace_is_stripped(self):
        self.assertEqual(photos.parse_text("  Sony a7 IV "), "Sony a7 IV")

    def test_max_length_is_50(self):
        self.assertEqual(photos.parse_text("a" * 50), "a" * 50)
        with self.assertRaises(ValueError):
            photos.parse_text("a" * 51)

class TestParseNumber(unittest.TestCase):
    def test_focal_length(self):
        parse = lambda value: photos.parse_number(value, 1, 1.0, 1000.0)
        self.assertEqual(parse("50"), 50.0)
        self.assertEqual(parse("24"), 24.0)
        self.assertEqual(parse("1.0"), 1.0)
        self.assertEqual(parse("1000.0"), 1000.0)
        self.assertEqual(parse("35.5"), 35.5)
        self.assertEqual(parse("35,5"), 35.5)
        self.assertIsNone(parse(""))
        for value in ["0.9", "1000.1", "0", "35.55", "abc", "-50", "1e2", "50.", ".5", "inf"]:
            with self.assertRaises(ValueError, msg=value):
                parse(value)

    def test_aperture(self):
        parse = lambda value: photos.parse_number(value, 2, 1.0, 50.0)
        self.assertEqual(parse("1.00"), 1.0)
        self.assertEqual(parse("2.8"), 2.8)
        self.assertEqual(parse("1.41"), 1.41)
        self.assertEqual(parse("50.00"), 50.0)
        for value in ["0.99", "50.01", "2.825", "f/2.8", "nan"]:
            with self.assertRaises(ValueError, msg=value):
                parse(value)

    def test_shutter_speed(self):
        parse = lambda value: photos.parse_number(value, 2, 0.01, 5000.0)
        self.assertEqual(parse("0.01"), 0.01)
        self.assertEqual(parse("250"), 250.0)
        self.assertEqual(parse("5000.00"), 5000.0)
        for value in ["0.00", "0.009", "5000.01", "1/250", "10000"]:
            with self.assertRaises(ValueError, msg=value):
                parse(value)

class TestParseDetails(unittest.TestCase):
    def test_all_details(self):
        details = photos.parse_details(details_form(
            camera="Sony a7 IV", lens="Sigma 24mm f/2 DG DN Contemporary",
            focal_length="24", aperture="2", shutter_speed="250"))
        self.assertEqual(details, {
            "camera": "Sony a7 IV",
            "lens": "Sigma 24mm f/2 DG DN Contemporary",
            "focal_length": 24.0,
            "aperture": 2.0,
            "shutter_speed": 250.0,
        })

    def test_details_are_optional(self):
        details = photos.parse_details({})
        self.assertEqual(set(details.values()), {None})

    def test_error_names_the_field(self):
        cases = {
            "camera": ("a" * 51, "Camera"),
            "lens": ("a" * 51, "Lens"),
            "focal_length": ("2000", "Focal length"),
            "aperture": ("0.5", "Aperture"),
            "shutter_speed": ("0", "Shutter speed"),
        }
        for field, (value, message) in cases.items():
            with self.assertRaises(ValueError) as context:
                photos.parse_details(details_form(**{field: value}))
            self.assertIn(message, str(context.exception))

class TestShowDetails(unittest.TestCase):
    def test_show_number(self):
        self.assertEqual(show_number(50.0), "50")
        self.assertEqual(show_number(35.5), "35.5")
        self.assertEqual(show_number(1.41), "1.41")
        self.assertEqual(show_number(1000.0), "1000")
        self.assertEqual(show_number(4999.99), "4999.99")

    def test_show_shutter_speed(self):
        self.assertEqual(show_shutter_speed(250.0), "1/250 s")
        self.assertEqual(show_shutter_speed(5000.0), "1/5000 s")
        self.assertEqual(show_shutter_speed(1.0), "1 s")
        self.assertEqual(show_shutter_speed(0.5), "2 s")
        self.assertEqual(show_shutter_speed(0.03), "33.3 s")
        self.assertEqual(show_shutter_speed(0.01), "100 s")

class TestPhotoDetails(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register("maija")

    def get_details(self, photo_id):
        sql = """SELECT camera, lens, focal_length, aperture, shutter_speed
                 FROM photos WHERE id = ?"""
        return dict(self.query(sql, [photo_id])[0])

    def update(self, photo_id, **fields):
        data = details_form(**fields)
        data["photo_id"] = photo_id
        data["description"] = "A photo"
        return self.post("/update_photo", data)

    def test_add_photo_with_details(self):
        photo_id = self.add_photo(details=PANASONIC)
        self.assertEqual(self.get_details(photo_id), {
            "camera": "Panasonic Lumix S9",
            "lens": "Panasonic Lumix S 24-105mm f/4 Macto O.I.S.",
            "focal_length": 50.0,
            "aperture": None,
            "shutter_speed": None,
        })

    def test_add_photo_without_details(self):
        photo_id = self.add_photo()
        self.assertEqual(set(self.get_details(photo_id).values()), {None})

    def test_add_photo_with_invalid_details(self):
        for field, value in [("camera", "a" * 51), ("lens", "a" * 51),
                             ("focal_length", "0.5"), ("aperture", "51"),
                             ("shutter_speed", "0.001")]:
            response = self.upload_photo(details={field: value})
            self.assertEqual(response.headers["Location"], "/new_photo", msg=field)
        self.assertEqual(self.query("SELECT COUNT(*) FROM photos")[0][0], 0)

        response = self.client.get("/new_photo")
        self.assertIn(b"Shutter speed must be", response.data)

    def test_edit_details(self):
        photo_id = self.add_photo(details=PANASONIC)
        response = self.update(photo_id, **SONY, aperture="2.8", shutter_speed="250")
        self.assertEqual(response.headers["Location"], "/photo/" + str(photo_id))
        self.assertEqual(self.get_details(photo_id), {
            "camera": "Sony a7 IV",
            "lens": "Sigma 24mm f/2 DG DN Contemporary",
            "focal_length": 24.0,
            "aperture": 2.8,
            "shutter_speed": 250.0,
        })

    def test_edit_can_clear_details(self):
        photo_id = self.add_photo(details=PANASONIC)
        self.update(photo_id)
        self.assertEqual(set(self.get_details(photo_id).values()), {None})

    def test_edit_with_invalid_details(self):
        photo_id = self.add_photo(details=PANASONIC)
        response = self.update(photo_id, focal_length="1000.1")
        self.assertEqual(response.headers["Location"], "/edit_photo/" + str(photo_id))
        self.assertEqual(self.get_details(photo_id)["focal_length"], 50.0)

    def test_edit_form_is_prefilled(self):
        photo_id = self.add_photo(details=dict(SONY, aperture="2.8", shutter_speed="250"))
        response = self.client.get("/edit_photo/" + str(photo_id))
        self.assertIn(b'value="Sony a7 IV"', response.data)
        self.assertIn(b'value="24"', response.data)
        self.assertIn(b'value="2.8"', response.data)
        self.assertIn(b'value="250"', response.data)

    def test_details_are_shown_in_photo_view(self):
        photo_id = self.add_photo(details=dict(PANASONIC, aperture="4", shutter_speed="125"))
        response = self.client.get("/photo/" + str(photo_id))
        self.assertIn(b"Panasonic Lumix S9", response.data)
        self.assertIn(b"Panasonic Lumix S 24-105mm f/4 Macto O.I.S.", response.data)
        self.assertIn(b"50 mm", response.data)
        self.assertIn(b"f/4", response.data)
        self.assertIn(b"1/125 s", response.data)

    def test_missing_details_are_not_shown(self):
        photo_id = self.add_photo()
        response = self.client.get("/photo/" + str(photo_id))
        self.assertNotIn(b"<dt>camera</dt>", response.data)
        self.assertNotIn(b"<dt>shutter speed</dt>", response.data)

    def test_details_are_not_shown_in_lists(self):
        self.add_photo(description="Lake", tags="lake", details=SONY)
        for url in ["/latest", "/my_photos", "/search?query=lake", "/tag/1"]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, msg=url)
            self.assertNotIn(b"Sony a7 IV", response.data, msg=url)
            self.assertNotIn(b"24 mm", response.data, msg=url)

    def test_details_are_escaped(self):
        photo_id = self.add_photo(details={"camera": "<b>cam</b>"})
        response = self.client.get("/photo/" + str(photo_id))
        self.assertIn(b"&lt;b&gt;cam&lt;/b&gt;", response.data)

    def test_new_photo_form_has_detail_fields(self):
        response = self.client.get("/new_photo")
        for field in [b"camera", b"lens", b"focal_length", b"aperture", b"shutter_speed"]:
            self.assertIn(b'name="' + field + b'"', response.data)

    def test_real_test_photo_values(self):
        with app.app_context():
            for values in [PANASONIC, SONY]:
                details = photos.parse_details(values)
                self.assertEqual(details["camera"], values["camera"])
                self.assertEqual(details["focal_length"], float(values["focal_length"]))
