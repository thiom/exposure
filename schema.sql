CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT
);

CREATE TABLE photos (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users,
    image BLOB,
    description TEXT,
    camera TEXT,
    lens TEXT,
    focal_length REAL,
    aperture REAL,
    shutter_speed REAL,
    date_time_added TEXT
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    title TEXT UNIQUE
);

CREATE TABLE photo_tags (
    id INTEGER PRIMARY KEY,
    photo_id INTEGER REFERENCES photos,
    tag_id INTEGER REFERENCES tags,
    UNIQUE (photo_id, tag_id)
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    photo_id INTEGER REFERENCES photos,
    user_id INTEGER REFERENCES users,
    content TEXT,
    sent_at TEXT
);

CREATE TABLE collections (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users,
    title TEXT,
    description TEXT
);

CREATE TABLE collection_photos (
    id INTEGER PRIMARY KEY,
    collection_id INTEGER REFERENCES collections,
    photo_id INTEGER REFERENCES photos,
    position INTEGER,
    UNIQUE (collection_id, photo_id)
);

CREATE INDEX idx_user_photos ON photos (user_id);
CREATE INDEX idx_photos_added ON photos (date_time_added);
CREATE INDEX idx_tag_photos ON photo_tags (tag_id);
CREATE INDEX idx_photo_comments ON comments (photo_id);
CREATE INDEX idx_collection_photos ON collection_photos (collection_id);
