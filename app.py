import math
import secrets
import sqlite3
import urllib.parse

from flask import Flask
from flask import abort, flash, make_response, redirect, render_template, request, session

import config
import photo_collections
import photos
import tags
import users

MAX_IMAGE_SIZE = 50 * 1024 * 1024
MAX_PHOTOS_PER_USER = 500
PAGE_SIZE = 20

app = Flask(__name__)
app.secret_key = config.secret_key
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_SIZE + 1024 * 1024

def require_login():
    if "user_id" not in session:
        abort(403)

def check_csrf():
    if "csrf_token" not in request.form:
        abort(403)
    if request.form["csrf_token"] != session["csrf_token"]:
        abort(403)

def start_session(user_id, username):
    session.pop("collection_draft", None)
    session["user_id"] = user_id
    session["username"] = username
    session["csrf_token"] = secrets.token_hex(16)

def get_back_url(back):
    if back.endswith("?"):
        back = back[:-1]
    if not back.startswith("/") or back.startswith("//") or "\\" in back:
        return "/"
    return back

def get_own_photo(photo_id):
    photo = photos.get_photo(photo_id)
    if not photo:
        abort(404)
    if photo["user_id"] != session["user_id"]:
        abort(403)
    return photo

def get_own_collection(collection_id):
    collection = photo_collections.get_collection(collection_id)
    if not collection:
        abort(404)
    if collection["user_id"] != session["user_id"]:
        abort(403)
    return collection

def get_page_count(count):
    return max(math.ceil(count / PAGE_SIZE), 1)

def parse_id(value):
    try:
        return int(value)
    except ValueError:
        abort(403)

@app.template_filter()
def show_date(date_time):
    return date_time[:10]

@app.template_filter()
def show_number(number):
    return f"{number:g}"

@app.template_filter()
def show_shutter_speed(shutter_speed):
    if shutter_speed > 1:
        return "1/" + show_number(shutter_speed) + " s"
    return show_number(round(1 / shutter_speed, 1)) + " s"

@app.route("/")
def index():
    return render_template("index.html", query="")

@app.route("/search")
def search():
    query = request.args.get("query", "").strip()
    if not query:
        return redirect("/")

    results = photos.find_photos(query)
    if not results:
        flash("No photos found")
        return render_template("index.html", query=query)

    return render_template("search.html", query=query, photos=results)

@app.route("/latest")
@app.route("/latest/<int:page>")
def latest(page=1):
    page_count = get_page_count(photos.photo_count())

    if page < 1:
        return redirect("/latest/1")
    if page > page_count:
        return redirect("/latest/" + str(page_count))

    latest_photos = photos.get_photos(page, PAGE_SIZE)
    return render_template("latest.html", page=page, page_count=page_count,
                           page_url="/latest/", suffix="", photos=latest_photos)

@app.route("/collections")
@app.route("/collections/<int:page>")
def latest_collections(page=1):
    query = request.args.get("query", "").strip()
    if query:
        count = photo_collections.find_count(query)
        suffix = "?query=" + urllib.parse.quote(query)
    else:
        count = photo_collections.collection_count()
        suffix = ""
    page_count = get_page_count(count)

    if page < 1:
        return redirect("/collections/1" + suffix)
    if page > page_count:
        return redirect("/collections/" + str(page_count) + suffix)

    if query:
        results = photo_collections.find_collections(query, page, PAGE_SIZE)
    else:
        results = photo_collections.get_collections(page, PAGE_SIZE)
    return render_template("collections.html", query=query, page=page,
                           page_count=page_count, page_url="/collections/",
                           suffix=suffix, collections=results)

@app.route("/my_photos")
def my_photos():
    require_login()
    user_photos = photos.get_user_photos(session["user_id"])
    return render_template("my_photos.html", photos=user_photos)

@app.route("/my_collections")
def my_collections():
    require_login()
    user_collections = photo_collections.get_user_collections(session["user_id"])
    return render_template("my_collections.html", collections=user_collections)

@app.route("/collection/<int:collection_id>")
def show_collection(collection_id):
    collection = photo_collections.get_collection(collection_id)
    if not collection:
        abort(404)
    collection_photos = photo_collections.get_photos(collection_id)
    return render_template("show_collection.html", collection=collection,
                           photos=collection_photos)

@app.route("/new_collection")
def new_collection():
    require_login()
    user_id = session["user_id"]
    if photo_collections.user_collection_count(user_id) >= photo_collections.MAX_COLLECTIONS_PER_USER:
        flash("You have reached the maximum of "
              + str(photo_collections.MAX_COLLECTIONS_PER_USER) + " collections")
        return redirect("/my_collections")

    session["collection_draft"] = {
        "collection_id": None,
        "title": "",
        "description": "",
        "photo_ids": [],
    }
    return redirect("/collection_draft")

@app.route("/edit_collection/<int:collection_id>")
def edit_collection(collection_id):
    require_login()
    collection = get_own_collection(collection_id)
    session["collection_draft"] = {
        "collection_id": collection_id,
        "title": collection["title"],
        "description": collection["description"],
        "photo_ids": photo_collections.get_photo_ids(collection_id),
    }
    return redirect("/collection_draft")

@app.route("/collection_draft")
def show_collection_draft():
    require_login()
    draft = session.get("collection_draft")
    if not draft:
        return redirect("/my_collections")

    user_photos = photos.get_user_photos(session["user_id"])
    photos_by_id = {photo["id"]: photo for photo in user_photos}
    selected = [photos_by_id[photo_id] for photo_id in draft["photo_ids"]
                if photo_id in photos_by_id]
    available = [photo for photo in user_photos if photo["id"] not in draft["photo_ids"]]

    if draft["collection_id"]:
        cancel_url = "/collection/" + str(draft["collection_id"])
    else:
        cancel_url = "/my_collections"

    return render_template("collection_form.html", draft=draft, selected=selected,
                           available=available, cancel_url=cancel_url,
                           has_photos=bool(user_photos),
                           max_photos=photo_collections.MAX_PHOTOS_PER_COLLECTION)

@app.route("/update_collection_draft", methods=["POST"])
def update_collection_draft():
    require_login()
    check_csrf()

    draft = session.get("collection_draft")
    if not draft:
        return redirect("/my_collections")

    title = request.form["title"]
    description = request.form["description"]
    if len(title) > photo_collections.MAX_TITLE_LENGTH:
        abort(403)
    if len(description) > photo_collections.MAX_DESCRIPTION_LENGTH:
        abort(403)
    draft["title"] = title
    draft["description"] = description

    photo_ids = draft["photo_ids"]
    if "add" in request.form:
        photo_id = parse_id(request.form["add"])
        get_own_photo(photo_id)
        if photo_id not in photo_ids:
            if len(photo_ids) >= photo_collections.MAX_PHOTOS_PER_COLLECTION:
                flash("A collection can have at most "
                      + str(photo_collections.MAX_PHOTOS_PER_COLLECTION) + " photos")
            else:
                photo_ids.append(photo_id)
    elif "remove" in request.form:
        photo_id = parse_id(request.form["remove"])
        if photo_id in photo_ids:
            photo_ids.remove(photo_id)
    elif "up" in request.form or "down" in request.form:
        move = "up" if "up" in request.form else "down"
        photo_id = parse_id(request.form[move])
        if photo_id in photo_ids:
            index = photo_ids.index(photo_id)
            other = index - 1 if move == "up" else index + 1
            if 0 <= other < len(photo_ids):
                photo_ids[index], photo_ids[other] = photo_ids[other], photo_ids[index]

    session["collection_draft"] = draft

    if "save" in request.form:
        return save_collection_draft(draft)
    return redirect("/collection_draft#selected")

def save_collection_draft(draft):
    user_id = session["user_id"]

    title = draft["title"].strip()
    description = draft["description"].strip()
    if not title:
        flash("The collection needs a title")
        return redirect("/collection_draft")

    own_ids = [photo["id"] for photo in photos.get_user_photos(user_id)]
    photo_ids = [photo_id for photo_id in draft["photo_ids"] if photo_id in own_ids]
    if not photo_ids:
        flash("Add at least one photo to the collection")
        return redirect("/collection_draft")

    collection_id = draft["collection_id"]
    if collection_id:
        get_own_collection(collection_id)
        photo_collections.update_collection(collection_id, title, description, photo_ids)
    else:
        if photo_collections.user_collection_count(user_id) >= photo_collections.MAX_COLLECTIONS_PER_USER:
            flash("You have reached the maximum of "
                  + str(photo_collections.MAX_COLLECTIONS_PER_USER) + " collections")
            return redirect("/my_collections")
        collection_id = photo_collections.add_collection(user_id, title, description, photo_ids)

    del session["collection_draft"]
    return redirect("/collection/" + str(collection_id))

@app.route("/remove_collection/<int:collection_id>", methods=["GET", "POST"])
def remove_collection(collection_id):
    require_login()
    collection = get_own_collection(collection_id)

    if request.method == "GET":
        return render_template("remove_collection.html", collection=collection)

    if request.method == "POST":
        check_csrf()
        draft = session.get("collection_draft")
        if "remove" in request.form:
            photo_collections.remove_collection(collection_id)
            if draft and draft["collection_id"] == collection_id:
                del session["collection_draft"]
            return redirect("/my_collections")
        else:
            if draft and draft["collection_id"] == collection_id:
                return redirect("/collection_draft")
            return redirect("/collection/" + str(collection_id))

@app.route("/tag/<int:tag_id>")
def show_tag(tag_id):
    tag = tags.get_tag(tag_id)
    if not tag:
        abort(404)
    tag_photos = tags.get_photos(tag_id)
    return render_template("show_tag.html", tag=tag, photos=tag_photos)

@app.route("/photo/<int:photo_id>")
def show_photo(photo_id):
    photo = photos.get_photo(photo_id)
    if not photo:
        abort(404)
    photo_tags = tags.get_tags(photo_id)
    comments = photos.get_comments(photo_id)
    return render_template("show_photo.html", photo=photo, tags=photo_tags,
                           comments=comments, back=get_back_url(request.args.get("back", "")),
                           max_comments=photos.MAX_COMMENTS_PER_PHOTO)

@app.route("/image/<int:photo_id>")
def show_image(photo_id):
    image = photos.get_image(photo_id)
    if not image:
        abort(404)

    response = make_response(bytes(image))
    response.headers.set("Content-Type", "image/jpeg")
    return response

@app.route("/new_photo")
def new_photo():
    require_login()
    if photos.user_photo_count(session["user_id"]) >= MAX_PHOTOS_PER_USER:
        flash("You have reached the maximum of " + str(MAX_PHOTOS_PER_USER) + " photos")
        return redirect("/my_photos")
    return render_template("new_photo.html", photo={})

@app.route("/create_photo", methods=["POST"])
def create_photo():
    require_login()
    check_csrf()

    user_id = session["user_id"]
    if photos.user_photo_count(user_id) >= MAX_PHOTOS_PER_USER:
        abort(403)

    description = request.form["description"]
    if not description.strip() or len(description) > 200:
        abort(403)

    try:
        details = photos.parse_details(request.form)
    except ValueError as error:
        flash(str(error))
        return redirect("/new_photo")

    tag_titles = tags.parse_titles(request.form.get("tags", ""))
    if tag_titles is None:
        flash("Tags may contain only letters, numbers, spaces and hyphens "
              "and be at most " + str(tags.MAX_TITLE_LENGTH) + " characters long")
        return redirect("/new_photo")
    if len(tag_titles) > tags.MAX_TAGS_PER_PHOTO:
        flash("A photo can have at most " + str(tags.MAX_TAGS_PER_PHOTO) + " tags")
        return redirect("/new_photo")

    file = request.files.get("image")
    if not file or not file.filename.lower().endswith((".jpg", ".jpeg")):
        flash("The image must be a .jpg or .jpeg file")
        return redirect("/new_photo")

    image = file.read()
    if len(image) > MAX_IMAGE_SIZE:
        flash("The image is too large (max 50 MB)")
        return redirect("/new_photo")
    if not image.startswith(b"\xff\xd8\xff"):
        flash("The image is not a valid JPEG file")
        return redirect("/new_photo")

    photo_id = photos.add_photo(user_id, image, description, details, tag_titles)
    return redirect("/tags/" + str(photo_id))

@app.route("/edit_photo/<int:photo_id>")
def edit_photo(photo_id):
    require_login()
    photo = get_own_photo(photo_id)
    photo_tags = tags.get_tags(photo_id)
    comments = photos.get_comments(photo_id)
    return render_template("edit_photo.html", photo=photo, tags=photo_tags,
                           comments=comments, redirect="/edit_photo/" + str(photo_id),
                           max_comments=photos.MAX_COMMENTS_PER_PHOTO)

@app.route("/update_photo", methods=["POST"])
def update_photo():
    require_login()
    check_csrf()

    photo_id = request.form["photo_id"]
    get_own_photo(photo_id)

    description = request.form["description"]
    if not description.strip() or len(description) > 200:
        abort(403)

    try:
        details = photos.parse_details(request.form)
    except ValueError as error:
        flash(str(error))
        return redirect("/edit_photo/" + str(photo_id))

    photos.update_photo(photo_id, description, details)
    return redirect("/photo/" + str(photo_id))

@app.route("/create_comment", methods=["POST"])
def create_comment():
    require_login()
    check_csrf()

    photo_id = request.form["photo_id"]
    photo = photos.get_photo(photo_id)
    if not photo:
        abort(404)

    content = request.form["content"]
    if not content.strip() or len(content) > 200:
        abort(403)

    url = request.form.get("redirect", "")
    if url != "/edit_photo/" + str(photo_id):
        back = get_back_url(request.form.get("back", ""))
        url = "/photo/" + str(photo_id) + "?back=" + urllib.parse.quote(back)

    if photos.comment_count(photo_id) >= photos.MAX_COMMENTS_PER_PHOTO:
        flash("This photo already has the maximum of "
              + str(photos.MAX_COMMENTS_PER_PHOTO) + " comments")
        return redirect(url)

    photos.add_comment(photo_id, session["user_id"], content.strip())
    return redirect(url + "#comments")

@app.route("/tags/<int:photo_id>")
def edit_tags(photo_id):
    require_login()
    photo = get_own_photo(photo_id)
    photo_tags = tags.get_tags(photo_id)

    query = request.args.get("query", "")
    suggestions = []
    new_title = None
    if query.strip():
        matches = tags.find_tags(query)
        current_ids = [tag["id"] for tag in photo_tags]
        suggestions = [tag for tag in matches if tag["id"] not in current_ids]
        new_title = tags.normalize_title(query)
        if new_title in [tag["title"] for tag in matches]:
            new_title = None

    return render_template("edit_tags.html", photo=photo, tags=photo_tags, query=query,
                           suggestions=suggestions, new_title=new_title,
                           max_tags=tags.MAX_TAGS_PER_PHOTO)

@app.route("/add_tag", methods=["POST"])
def add_tag():
    require_login()
    check_csrf()

    photo_id = request.form["photo_id"]
    get_own_photo(photo_id)

    title = tags.normalize_title(request.form["title"])
    if not title:
        flash("Tags may contain only letters, numbers, spaces and hyphens "
              "and be at most " + str(tags.MAX_TITLE_LENGTH) + " characters long")
        return redirect("/tags/" + str(photo_id))

    photo_tags = tags.get_tags(photo_id)
    if title not in [tag["title"] for tag in photo_tags]:
        if len(photo_tags) >= tags.MAX_TAGS_PER_PHOTO:
            flash("A photo can have at most " + str(tags.MAX_TAGS_PER_PHOTO) + " tags")
            return redirect("/tags/" + str(photo_id))
        tags.add_tag(photo_id, title)

    return redirect("/tags/" + str(photo_id))

@app.route("/remove_tag", methods=["POST"])
def remove_tag():
    require_login()
    check_csrf()

    photo_id = request.form["photo_id"]
    get_own_photo(photo_id)

    tags.remove_tag(photo_id, request.form["tag_id"])
    return redirect("/tags/" + str(photo_id))

@app.route("/remove_photo/<int:photo_id>", methods=["GET", "POST"])
def remove_photo(photo_id):
    require_login()
    photo = get_own_photo(photo_id)

    if request.method == "GET":
        single_photo_collections = photo_collections.get_single_photo_collections(photo_id)
        return render_template("remove_photo.html", photo=photo,
                               collections=single_photo_collections)

    if request.method == "POST":
        check_csrf()
        if "remove" in request.form:
            photos.remove_photo(photo_id)
            return redirect("/my_photos")
        else:
            return redirect("/edit_photo/" + str(photo_id))

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/create", methods=["POST"])
def create():
    username = request.form["username"]
    password1 = request.form["password1"]
    password2 = request.form["password2"]
    if not username.strip() or len(username) > 30:
        flash("Username must be 1-30 characters long")
        return redirect("/register")
    if len(password1) < 10 or len(password1) > 30:
        flash("Password must be 10-30 characters long")
        return redirect("/register")
    if password1 != password2:
        flash("Passwords do not match")
        return redirect("/register")

    try:
        user_id = users.create_user(username, password1)
    except sqlite3.IntegrityError:
        flash("Username already in use, pick another one")
        return redirect("/register")

    start_session(user_id, username)
    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user_id = users.check_login(username, password)
        if user_id:
            start_session(user_id, username)
            return redirect("/")
        else:
            flash("Wrong username or password")
            return redirect("/login")

@app.route("/logout")
def logout():
    if "user_id" in session:
        del session["user_id"]
        del session["username"]
        del session["csrf_token"]
    session.pop("collection_draft", None)
    return redirect("/")
