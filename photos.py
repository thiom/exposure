import re

import db
import tags

MAX_TEXT_LENGTH = 50
MAX_COMMENTS_PER_PHOTO = 100

def parse_text(value, max_length=MAX_TEXT_LENGTH):
    value = value.strip()
    if len(value) > max_length:
        raise ValueError
    return value or None

def parse_number(value, decimals, minimum, maximum):
    value = value.strip().replace(",", ".")
    if not value:
        return None
    if not re.search("^[0-9]{1,4}(\\.[0-9]{1," + str(decimals) + "})?$", value):
        raise ValueError
    number = round(float(value), decimals)
    if number < minimum or number > maximum:
        raise ValueError
    return number

def parse_details(form):
    details = {}
    try:
        details["camera"] = parse_text(form.get("camera", ""))
    except ValueError:
        raise ValueError("Camera can be at most 50 characters long")
    try:
        details["lens"] = parse_text(form.get("lens", ""))
    except ValueError:
        raise ValueError("Lens can be at most 50 characters long")
    try:
        details["focal_length"] = parse_number(form.get("focal_length", ""), 1, 1.0, 1000.0)
    except ValueError:
        raise ValueError("Focal length must be a number between 1.0 and 1000.0 "
                         "with at most one decimal")
    try:
        details["aperture"] = parse_number(form.get("aperture", ""), 2, 1.0, 50.0)
    except ValueError:
        raise ValueError("Aperture must be a number between 1.00 and 50.00 "
                         "with at most two decimals")
    try:
        details["shutter_speed"] = parse_number(form.get("shutter_speed", ""), 2, 0.01, 5000.0)
    except ValueError:
        raise ValueError("Shutter speed must be a number between 0.01 and 5000.00 "
                         "with at most two decimals")
    return details

def add_photo(user_id, image, description, details, tag_titles):
    sql = """INSERT INTO photos (user_id, image, description, camera, lens,
                                 focal_length, aperture, shutter_speed, date_time_added)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))"""
    db.execute(sql, [user_id, image, description, details["camera"], details["lens"],
                     details["focal_length"], details["aperture"], details["shutter_speed"]])

    photo_id = db.last_insert_id()

    for title in tag_titles:
        tags.add_tag(photo_id, title)

    return photo_id

def get_photo(photo_id):
    sql = """SELECT photos.id,
                    photos.description,
                    photos.camera,
                    photos.lens,
                    photos.focal_length,
                    photos.aperture,
                    photos.shutter_speed,
                    photos.date_time_added,
                    users.id user_id,
                    users.username
             FROM photos, users
             WHERE photos.user_id = users.id AND
                   photos.id = ?"""
    result = db.query(sql, [photo_id])
    return result[0] if result else None

def get_image(photo_id):
    sql = "SELECT image FROM photos WHERE id = ?"
    result = db.query(sql, [photo_id])
    return result[0][0] if result else None

def photo_count():
    sql = "SELECT COUNT(*) FROM photos"
    return db.query(sql)[0][0]

def get_photos(page, page_size):
    sql = """SELECT id, description
             FROM photos
             ORDER BY date_time_added DESC, id DESC
             LIMIT ? OFFSET ?"""
    limit = page_size
    offset = page_size * (page - 1)
    return db.query(sql, [limit, offset])

def user_photo_count(user_id):
    sql = "SELECT COUNT(*) FROM photos WHERE user_id = ?"
    return db.query(sql, [user_id])[0][0]

def get_user_photos(user_id):
    sql = """SELECT id, description
             FROM photos
             WHERE user_id = ?
             ORDER BY date_time_added DESC, id DESC"""
    return db.query(sql, [user_id])

def update_photo(photo_id, description, details):
    sql = """UPDATE photos SET description = ?,
                               camera = ?,
                               lens = ?,
                               focal_length = ?,
                               aperture = ?,
                               shutter_speed = ?
                           WHERE id = ?"""
    db.execute(sql, [description, details["camera"], details["lens"], details["focal_length"],
                     details["aperture"], details["shutter_speed"], photo_id])

def add_comment(photo_id, user_id, content):
    sql = """INSERT INTO comments (photo_id, user_id, content, sent_at)
             VALUES (?, ?, ?, datetime('now'))"""
    db.execute(sql, [photo_id, user_id, content])

def get_comments(photo_id):
    sql = """SELECT comments.content, comments.sent_at, users.username
             FROM comments, users
             WHERE comments.user_id = users.id AND
                   comments.photo_id = ?
             ORDER BY comments.id"""
    return db.query(sql, [photo_id])

def comment_count(photo_id):
    sql = "SELECT COUNT(*) FROM comments WHERE photo_id = ?"
    return db.query(sql, [photo_id])[0][0]

def remove_photo(photo_id):
    sql = "DELETE FROM photo_tags WHERE photo_id = ?"
    db.execute(sql, [photo_id])
    sql = "DELETE FROM comments WHERE photo_id = ?"
    db.execute(sql, [photo_id])
    sql = "DELETE FROM collection_photos WHERE photo_id = ?"
    db.execute(sql, [photo_id])
    sql = "DELETE FROM photos WHERE id = ?"
    db.execute(sql, [photo_id])
    tags.remove_unused_tags()

def find_photos(query):
    sql = """SELECT DISTINCT photos.id, photos.description, photos.date_time_added
             FROM photos LEFT JOIN photo_tags ON photos.id = photo_tags.photo_id
                         LEFT JOIN tags ON photo_tags.tag_id = tags.id
             WHERE photos.description LIKE ? OR tags.title LIKE ?
             ORDER BY photos.date_time_added DESC, photos.id DESC"""
    like = "%" + query + "%"
    return db.query(sql, [like, like])
