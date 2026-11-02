from difflib import SequenceMatcher

import db

MAX_TITLE_LENGTH = 20
MAX_TAGS_PER_PHOTO = 20
FUZZY_THRESHOLD = 0.6

def normalize_title(title):
    title = " ".join(title.split()).lower()
    if not title or len(title) > MAX_TITLE_LENGTH:
        return None
    for char in title:
        if not (char.isalnum() or char in " -"):
            return None
    return title

def parse_titles(text):
    titles = []
    for entry in text.split(","):
        if not entry.strip():
            continue
        title = normalize_title(entry)
        if not title:
            return None
        if title not in titles:
            titles.append(title)
    return titles

def get_tag(tag_id):
    sql = "SELECT id, title FROM tags WHERE id = ?"
    result = db.query(sql, [tag_id])
    return result[0] if result else None

def get_tags(photo_id):
    sql = """SELECT tags.id, tags.title
             FROM tags, photo_tags
             WHERE tags.id = photo_tags.tag_id AND
                   photo_tags.photo_id = ?
             ORDER BY tags.title"""
    return db.query(sql, [photo_id])

def get_photos(tag_id):
    sql = """SELECT photos.id, photos.description
             FROM photos, photo_tags
             WHERE photos.id = photo_tags.photo_id AND
                   photo_tags.tag_id = ?
             ORDER BY photos.date_time_added DESC, photos.id DESC"""
    return db.query(sql, [tag_id])

def add_tag(photo_id, title):
    sql = "INSERT OR IGNORE INTO tags (title) VALUES (?)"
    db.execute(sql, [title])

    sql = "SELECT id FROM tags WHERE title = ?"
    tag_id = db.query(sql, [title])[0][0]

    sql = "INSERT OR IGNORE INTO photo_tags (photo_id, tag_id) VALUES (?, ?)"
    db.execute(sql, [photo_id, tag_id])

def remove_tag(photo_id, tag_id):
    sql = "DELETE FROM photo_tags WHERE photo_id = ? AND tag_id = ?"
    db.execute(sql, [photo_id, tag_id])
    remove_unused_tags()

def remove_unused_tags():
    sql = """DELETE FROM tags
             WHERE id NOT IN (SELECT tag_id FROM photo_tags)"""
    db.execute(sql)

def similarity(query, title):
    if title.startswith(query):
        return 1.0
    if query in title:
        return 0.9
    return SequenceMatcher(None, query, title).ratio()

def find_tags(query, limit=10):
    query = " ".join(query.split()).lower()
    if not query:
        return []

    sql = "SELECT id, title FROM tags"
    matches = []
    for tag in db.query(sql):
        score = similarity(query, tag["title"])
        if score >= FUZZY_THRESHOLD:
            matches.append((-score, tag["title"], tag))

    matches.sort()
    return [tag for _, _, tag in matches[:limit]]
