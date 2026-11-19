import db

MAX_TITLE_LENGTH = 30
MAX_DESCRIPTION_LENGTH = 200
MAX_PHOTOS_PER_COLLECTION = 50
MAX_COLLECTIONS_PER_USER = 50

# columns shown in collection lists, the cover is the first photo of the collection
LIST_COLUMNS = """collections.id,
                  collections.title,
                  collections.description,
                  collections.date_time_added,
                  users.username,
                  (SELECT photo_id FROM collection_photos
                   WHERE collection_id = collections.id
                   ORDER BY position LIMIT 1) cover_id"""

def add_collection(user_id, title, description, photo_ids):
    sql = """INSERT INTO collections (user_id, title, description, date_time_added)
             VALUES (?, ?, ?, datetime('now'))"""
    db.execute(sql, [user_id, title, description])
    collection_id = db.last_insert_id()
    add_photos(collection_id, photo_ids)
    return collection_id

def add_photos(collection_id, photo_ids):
    sql = """INSERT INTO collection_photos (collection_id, photo_id, position)
             VALUES (?, ?, ?)"""
    for position, photo_id in enumerate(photo_ids):
        db.execute(sql, [collection_id, photo_id, position])

def update_collection(collection_id, title, description, photo_ids):
    sql = "UPDATE collections SET title = ?, description = ? WHERE id = ?"
    db.execute(sql, [title, description, collection_id])
    sql = "DELETE FROM collection_photos WHERE collection_id = ?"
    db.execute(sql, [collection_id])
    add_photos(collection_id, photo_ids)

def remove_collection(collection_id):
    sql = "DELETE FROM collection_photos WHERE collection_id = ?"
    db.execute(sql, [collection_id])
    sql = "DELETE FROM collections WHERE id = ?"
    db.execute(sql, [collection_id])

def remove_empty_collections():
    sql = """DELETE FROM collections
             WHERE id NOT IN (SELECT collection_id FROM collection_photos)"""
    db.execute(sql)

def get_collection(collection_id):
    sql = """SELECT collections.id,
                    collections.title,
                    collections.description,
                    collections.date_time_added,
                    users.id user_id,
                    users.username
             FROM collections, users
             WHERE collections.user_id = users.id AND
                   collections.id = ?"""
    result = db.query(sql, [collection_id])
    return result[0] if result else None

def get_photos(collection_id):
    sql = """SELECT photos.id, photos.description
             FROM photos, collection_photos
             WHERE photos.id = collection_photos.photo_id AND
                   collection_photos.collection_id = ?
             ORDER BY collection_photos.position"""
    return db.query(sql, [collection_id])

def get_photo_ids(collection_id):
    return [photo["id"] for photo in get_photos(collection_id)]

def get_single_photo_collections(photo_id):
    sql = """SELECT collections.id, collections.title
             FROM collections, collection_photos
             WHERE collections.id = collection_photos.collection_id AND
                   collection_photos.photo_id = ? AND
                   (SELECT COUNT(*) FROM collection_photos
                    WHERE collection_id = collections.id) = 1"""
    return db.query(sql, [photo_id])

def collection_count():
    sql = "SELECT COUNT(*) FROM collections"
    return db.query(sql)[0][0]

def get_collections(page, page_size):
    sql = "SELECT " + LIST_COLUMNS + """
             FROM collections, users
             WHERE collections.user_id = users.id
             ORDER BY collections.date_time_added DESC, collections.id DESC
             LIMIT ? OFFSET ?"""
    limit = page_size
    offset = page_size * (page - 1)
    return db.query(sql, [limit, offset])

def user_collection_count(user_id):
    sql = "SELECT COUNT(*) FROM collections WHERE user_id = ?"
    return db.query(sql, [user_id])[0][0]

def get_user_collections(user_id):
    sql = "SELECT " + LIST_COLUMNS + """
             FROM collections, users
             WHERE collections.user_id = users.id AND
                   collections.user_id = ?
             ORDER BY collections.date_time_added DESC, collections.id DESC"""
    return db.query(sql, [user_id])

def find_count(query):
    sql = """SELECT COUNT(*)
             FROM collections
             WHERE title LIKE ? OR description LIKE ?"""
    like = "%" + query + "%"
    return db.query(sql, [like, like])[0][0]

def find_collections(query, page, page_size):
    sql = "SELECT " + LIST_COLUMNS + """
             FROM collections, users
             WHERE collections.user_id = users.id AND
                   (collections.title LIKE ? OR collections.description LIKE ?)
             ORDER BY collections.date_time_added DESC, collections.id DESC
             LIMIT ? OFFSET ?"""
    like = "%" + query + "%"
    limit = page_size
    offset = page_size * (page - 1)
    return db.query(sql, [like, like, limit, offset])
