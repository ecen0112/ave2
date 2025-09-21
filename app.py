from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Define a custom Jinja2 filter for datetime formatting
@app.template_filter('datetime')
def format_datetime(value):
    if value:
        return datetime.fromisoformat(value).strftime('%Y-%m-%d %H:%M:%S')
    return value

# Upload folder setup
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# DB file path
DB_FILE = "data.json"

# Function to save the database to a JSON file
def save_db():
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=4)
        print(f"Database saved to {DB_FILE} at {datetime.now().strftime('%H:%M:%S')}")
        return True
    except Exception as e:
        print(f"Error saving database: {e} at {datetime.now().strftime('%H:%M:%S')}")
        flash(f"Failed to save database: {e}", "error")
        return False

# Function to load the database from a JSON file
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding {DB_FILE}: {e}. Using default data at {datetime.now().strftime('%H:%M:%S')}")
            return {
                "users": [
                    {"username": "BUNBUN", "password": "BUNBUN", "role": "erl"},
                    {"username": "BUNNY", "password": "BUNNY", "role": "love"}
                ],
                "ideas": ["Go for a picnic", "Watch a movie together"],
                "memories": ["Our first date", "Trip to the beach"],
                "notes": ["Don’t forget the anniversary gift!", "Plan next weekend"],
                "gallery": []
            }
    return {
        "users": [
            {"username": "BUNBUN", "password": "BUNBUN", "role": "erl"},
            {"username": "BUNNY", "password": "BUNNY", "role": "love"}
        ],
        "ideas": ["Go for a picnic", "Watch a movie together"],
        "memories": ["Our first date", "Trip to the beach"],
        "notes": ["Don’t forget the anniversary gift!", "Plan next weekend"],
        "gallery": []
    }

# Load existing images from disk on startup
def load_gallery():
    files = os.listdir(app.config["UPLOAD_FOLDER"])
    gallery = []
    for filename in sorted(files, reverse=True):  # newest first
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.isfile(filepath):
            gallery.append({
                "filename": filename,
                "uploaded_at": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                "note": ""
            })
    return gallery

# Load the database on startup
db = load_db()
db["gallery"] = load_gallery()

# Login required decorator with debugging
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or not session['username']:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        print(f"Authenticated user: {session['username']}, Role: {session.get('role')} at {datetime.now().strftime('%H:%M:%S')}")
        return f(*args, **kwargs)
    return decorated_function

# ---------- Auth ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()  # Clear any existing session before attempting login
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        for user in db["users"]:
            if user["username"] == u and user["password"] == p:
                session["username"] = u
                session["role"] = user["role"]
                flash(f"Signed in as {u} ({user['role']})", "success")
                print(f"Login success: {u}, Role: {user['role']} at {datetime.now().strftime('%H:%M:%S')}")
                return redirect(url_for("dashboard"))
        flash("Invalid credentials. Use BUNBUN/BUNBUN or BUNNY/BUNNY.", "danger")
        print(f"Login failed for username: {u} at {datetime.now().strftime('%H:%M:%S')}")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# ---------- Debug and Diagnose Routes (remove in production) ----------
@app.route("/debug")
def debug():
    return f"Session: {dict(session)}<br>DB Users: {db['users']}<br>Gallery: {db['gallery']}"

@app.route("/diagnose")
@login_required
def diagnose():
    return (
        f"Time: {datetime.now().strftime('%H:%M:%S')}<br>"
        f"User: {session.get('username')}<br>"
        f"Role: {session.get('role')}<br>"
        f"Gallery Length: {len(db['gallery'])}<br>"
        f"DB File Exists: {os.path.exists(DB_FILE)}<br>"
        f"Upload Folder Exists: {os.path.exists(UPLOAD_FOLDER)}<br>"
        f"DB Write Test: {save_db()}"
    )

# ---------- Dashboard ----------
@app.route("/")
@login_required
def dashboard():
    username = session.get("username")
    if not username:
        flash("Session error: No username found.", "error")
        return redirect(url_for("login"))
    profile = {
        "name": username,
        "bio": "A curated place for our memories, ideas and photos.",
        "profile_pic": None
    }

    # relationship start (example)
    relationship_start_str = "2025-09-13"
    relationship_start = datetime.strptime(relationship_start_str, "%Y-%m-%d")
    days_together = (datetime.now() - relationship_start).days

    # next anniversary calculation
    anniv_month = relationship_start.month
    anniv_day = relationship_start.day
    today = datetime.now()
    next_anniv = datetime(today.year, anniv_month, anniv_day)
    if next_anniv < today:
        if anniv_month == 12:
            next_anniv = datetime(today.year + 1, 1, anniv_day)
        else:
            next_anniv = datetime(today.year, anniv_month + 1, anniv_day)

    # gallery preview
    gallery_preview = []
    for i, img in enumerate(db["gallery"][:6]):
        gallery_preview.append({"idx": i, "filename": img["filename"]})

    return render_template(
        "dashboard.html",
        profile=profile,
        relationship_start=relationship_start_str,
        days_text=f"{days_together} days{'s' if days_together != 1 else ''} together 💕",
        next_anniversary=next_anniv.strftime("%Y-%m-%d %H:%M:%S"),
        gallery=gallery_preview
    )

# ---------- Ideas ----------
@app.route("/ideas", methods=["GET", "POST"])
@login_required
def ideas():
    if request.method == "POST":
        role = session.get("role")
        if not role or role != "erl":
            flash("Only users with 'erl' role can add ideas.", "warning")
            return redirect(url_for("ideas"))
        idea = request.form.get("idea", "").strip()
        if idea:
            db["ideas"].insert(0, idea)
            save_db()
            flash("Idea added.", "success")
    return render_template("ideas.html", ideas=db["ideas"])

@app.route("/delete_idea/<int:idx>", methods=["POST"])
@login_required
def delete_idea(idx):
    role = session.get("role")
    if not role or role != "erl":
        flash("Only users with 'erl' role can delete ideas.", "warning")
        return redirect(url_for("ideas"))
    if 0 <= idx < len(db["ideas"]):
        db["ideas"].pop(idx)
        save_db()
        flash("Idea deleted.", "info")
    return redirect(url_for("ideas"))

# ---------- Memories ----------
@app.route("/memories", methods=["GET", "POST"])
@login_required
def memories():
    if request.method == "POST":
        role = session.get("role")
        if not role or role != "erl":
            flash("Only users with 'erl' role can add memories.", "warning")
            return redirect(url_for("memories"))
        memory = request.form.get("memory", "").strip()
        if memory:
            db["memories"].insert(0, memory)
            save_db()
            flash("Memory added.", "success")
    return render_template("memories.html", memories=db["memories"])

@app.route("/delete_memory/<int:idx>", methods=["POST"])
@login_required
def delete_memory(idx):
    role = session.get("role")
    if not role or role != "erl":
        flash("Only users with 'erl' role can delete memories.", "warning")
        return redirect(url_for("memories"))
    if 0 <= idx < len(db["memories"]):
        db["memories"].pop(idx)
        save_db()
        flash("Memory deleted.", "info")
    return redirect(url_for("memories"))

# ---------- Notes ----------
@app.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    if request.method == "POST":
        role = session.get("role")
        if not role or role != "erl":
            flash("Only users with 'erl' role can add notes.", "warning")
            return redirect(url_for("notes"))
        note = request.form.get("note", "").strip()
        if note:
            db["notes"].insert(0, note)
            save_db()
            flash("Note added.", "success")
    return render_template("notes.html", notes=db["notes"])

@app.route("/delete_note/<int:idx>", methods=["POST"])
@login_required
def delete_note(idx):
    role = session.get("role")
    if not role or role != "erl":
        flash("Only users with 'erl' role can delete notes.", "warning")
        return redirect(url_for("view_image", idx=idx))
    if 0 <= idx < len(db["gallery"]):
        if db["gallery"][idx].get("note"):
            db["gallery"][idx]["note"] = ""
            if save_db():
                flash("Note deleted successfully.", "success")
                print(f"Note deleted from image {idx} at {datetime.now().strftime('%H:%M:%S')}")
            else:
                flash("Failed to delete note (database not saved).", "error")
        else:
            flash("No note to delete.", "warning")
    else:
        flash("Invalid image index.", "warning")
    return redirect(url_for("view_image", idx=idx))

@app.route("/delete_image/<int:idx>", methods=["POST"])
@login_required
def delete_image(idx):
    role = session.get("role")
    if not role or role != "erl":
        flash("Only users with 'erl' role can delete images.", "warning")
        print(f"Role check failed for {session.get('username')} at {datetime.now().strftime('%H:%M:%S')}")
        return redirect(url_for("gallery" if request.referrer and "gallery" in request.referrer else "view_image", idx=idx))
    if not (0 <= idx < len(db["gallery"])):
        flash("Invalid image index.", "warning")
        print(f"Invalid index {idx} for gallery length {len(db['gallery'])} at {datetime.now().strftime('%H:%M:%S')}")
        return redirect(url_for("gallery" if request.referrer and "gallery" in request.referrer else "view_image", idx=idx))
    try:
        image_to_delete = db["gallery"][idx]
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], image_to_delete["filename"])
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Deleted file {filepath} at {datetime.now().strftime('%H:%M:%S')}")
        db["gallery"].pop(idx)
        if save_db():
            flash("Image deleted successfully.", "success")
            print(f"Image deleted at index {idx} at {datetime.now().strftime('%H:%M:%S')}")
        else:
            flash("Image deletion failed (database not saved).", "error")
            print(f"Database save failed at {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        flash(f"Failed to delete image: {e}", "error")
        print(f"Error deleting image: {e} at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("gallery" if request.referrer and "gallery" in request.referrer else "view_image", idx=idx))

@app.route("/gallery", methods=["GET", "POST"])
@login_required
def gallery():
    if request.method == "POST":
        role = session.get("role")
        if not role or role != "erl":
            flash("Only users with 'erl' role can upload images.", "warning")
            return redirect(url_for("gallery"))
        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            file.save(filepath)
            db["gallery"].insert(0, {"filename": unique_filename, "uploaded_at": datetime.now().isoformat(), "note": ""})
            save_db()
            flash("Image uploaded successfully.", "success")
    return render_template("gallery.html", gallery=db["gallery"])

@app.route("/image/<int:idx>", methods=["GET", "POST"])
@login_required
def view_image(idx):
    if not (0 <= idx < len(db["gallery"])):
        flash("Image not found.", "warning")
        return redirect(url_for("gallery"))
    image = db["gallery"][idx]
    if request.method == "POST":
        role = session.get("role")
        if not role or role != "erl":
            flash("Only users with 'erl' role can add notes.", "warning")
            return redirect(url_for("view_image", idx=idx))
        note = request.form.get("note", "").strip()
        if note:
            try:
                image["note"] = note
                if not save_db():
                    raise Exception("Database save failed")
                flash("Note added successfully.", "success")
                print(f"Note added to image {idx}: {note} at {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                flash(f"Failed to add note: {e}", "error")
                print(f"Error adding note: {e} at {datetime.now().strftime('%H:%M:%S')}")
    return render_template("image_view.html", image=image, idx=idx)

# ---------- Games ----------
@app.route("/game")
@login_required
def game():
    return render_template("crossy_road.html")

@app.route("/chicken-game")
@login_required
def chicken_game():
    return render_template("chicken_game.html")

@app.route("/fireworks")
@login_required
def fireworks():
    return render_template("fireworks.html")

@app.route("/butterfly")
@login_required
def butterfly():
    return render_template("butterfly.html")

@app.route("/snake-game")
@login_required
def snake_game():
    return render_template("snake-game.html")

@app.route("/arrow-game")
@login_required
def arrow_game():
    return render_template("arrow-game.html")

if __name__ == "__main__":
    app.run(debug=True)