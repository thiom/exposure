import db
import tags

def add_photo(user_id, image, description, tag_titles):
    sql = """INSERT INTO photos (user_id, image, description, date_time_added)
             VALUES (?, ?, ?, datetime('now'))"""
    db.execute(sql, [user_id, image, description])

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

def update_photo(photo_id, description):
    sql = "UPDATE photos SET description = ? WHERE id = ?"
    db.execute(sql, [description, photo_id])

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
