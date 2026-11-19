# Starts the application for the Robot Framework tests.
#
# The tests use their own database (robot_test.db) and never touch the real
# one. The route /reset_db, which empties the database and the session, exists
# only in this test server, not in the application itself.
#
# Usage: python story_tests/server.py [port]

import os
import sqlite3
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# pylint: disable=wrong-import-position
from flask import redirect, session

import config
from app import app

DATABASE = os.path.join(ROOT_DIR, "robot_test.db")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5002

def create_database():
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
    con = sqlite3.connect(DATABASE)
    with open(os.path.join(ROOT_DIR, "schema.sql"), encoding="utf-8") as file:
        con.executescript(file.read())
    con.close()

@app.route("/reset_db")
def reset_db():
    create_database()
    session.clear()
    return redirect("/")

config.database = DATABASE
create_database()
app.run(host="127.0.0.1", port=PORT)
