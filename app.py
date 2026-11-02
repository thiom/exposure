import math
import secrets
import sqlite3

from flask import Flask
from flask import abort, flash, make_response, redirect, render_template, request, session

import config
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
    session["user_id"] = user_id
    session["username"] = username
    session["csrf_token"] = secrets.token_hex(16)

def get_back_url():
    back = request.args.get("back", "")
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
    page_count = math.ceil(photos.photo_count() / PAGE_SIZE)
    page_count = max(page_count, 1)

    if page < 1:
        return redirect("/latest/1")
    if page > page_count:
        return redirect("/latest/" + str(page_count))

    latest_photos = photos.get_photos(page, PAGE_SIZE)
    return render_template("latest.html", page=page, page_count=page_count,
                           photos=latest_photos)

@app.route("/my_photos")
def my_photos():
    require_login()
    user_photos = photos.get_user_photos(session["user_id"])
    return render_template("my_photos.html", photos=user_photos)

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
    return render_template("show_photo.html", photo=photo, tags=photo_tags,
                           back=get_back_url())

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
    return render_template("new_photo.html")

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

    photo_id = photos.add_photo(user_id, image, description, tag_titles)
    return redirect("/tags/" + str(photo_id))

@app.route("/edit_photo/<int:photo_id>")
def edit_photo(photo_id):
    require_login()
    photo = get_own_photo(photo_id)
    photo_tags = tags.get_tags(photo_id)
    return render_template("edit_photo.html", photo=photo, tags=photo_tags)

@app.route("/update_photo", methods=["POST"])
def update_photo():
    require_login()
    check_csrf()

    photo_id = request.form["photo_id"]
    get_own_photo(photo_id)

    description = request.form["description"]
    if not description.strip() or len(description) > 200:
        abort(403)

    photos.update_photo(photo_id, description)
    return redirect("/photo/" + str(photo_id))

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
        return render_template("remove_photo.html", photo=photo)

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
    return redirect("/")
