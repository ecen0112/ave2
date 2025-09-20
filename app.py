from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import json

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Upload folder setup
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# DB file path
DB_FILE = "data.json"

# Function to save the database to a JSON file
def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

# Function to load the database from a JSON file
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {
        "users": [
            {"username": "admin", "password": "admin", "role": "admin"},
            {"username": "guest", "password": "guest", "role": "guest"}
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
                "uploaded_at": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
            })
    return gallery

# Load the database on startup
db = load_db()
db["gallery"] = load_gallery()

# ---------- Auth ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        for user in db["users"]:
            if user["username"] == u and user["password"] == p:
                session["username"] = u
                session["role"] = user["role"]
                flash(f"Signed in as {u}", "success")
                return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

# ---------- Dashboard ----------
@app.route("/")
def dashboard():
    username = session.get("username", "Guest")
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
        days_text=f"{days_together} day{'s' if days_together != 1 else ''} together 💕",
        next_anniversary=next_anniv.strftime("%Y-%m-%d %H:%M:%S"),
        gallery=gallery_preview
    )

# ---------- Ideas ----------
@app.route("/ideas", methods=["GET", "POST"])
def ideas():
    if request.method == "POST":
        if session.get("role") != "admin":
            flash("Only admin can add ideas.", "warning")
            return redirect(url_for("ideas"))
        idea = request.form.get("idea", "").strip()
        if idea:
            db["ideas"].insert(0, idea)
            save_db()
            flash("Idea added.", "success")
    return render_template("ideas.html", ideas=db["ideas"])

@app.route("/delete_idea/<int:idx>", methods=["POST"])
def delete_idea(idx):
    if session.get("role") != "admin":
        flash("Only admin can delete ideas.", "warning")
        return redirect(url_for("ideas"))
    if 0 <= idx < len(db["ideas"]):
        db["ideas"].pop(idx)
        save_db()
        flash("Idea deleted.", "info")
    return redirect(url_for("ideas"))

# ---------- Memories ----------
@app.route("/memories", methods=["GET", "POST"])
def memories():
    if request.method == "POST":
        if session.get("role") != "admin":
            flash("Only admin can add memories.", "warning")
            return redirect(url_for("memories"))
        memory = request.form.get("memory", "").strip()
        if memory:
            db["memories"].insert(0, memory)
            save_db()
            flash("Memory added.", "success")
    return render_template("memories.html", memories=db["memories"])

@app.route("/delete_memory/<int:idx>", methods=["POST"])
def delete_memory(idx):
    if session.get("role") != "admin":
        flash("Only admin can delete memories.", "warning")
        return redirect(url_for("memories"))
    if 0 <= idx < len(db["memories"]):
        db["memories"].pop(idx)
        save_db()
        flash("Memory deleted.", "info")
    return redirect(url_for("memories"))

# ---------- Notes ----------
@app.route("/notes", methods=["GET", "POST"])
def notes():
    if request.method == "POST":
        if session.get("role") != "admin":
            flash("Only admin can add notes.", "warning")
            return redirect(url_for("notes"))
        note = request.form.get("note", "").strip()
        if note:
            db["notes"].insert(0, note)
            save_db()
            flash("Note added.", "success")
    return render_template("notes.html", notes=db["notes"])

@app.route("/delete_note/<int:idx>", methods=["POST"])
def delete_note(idx):
    if session.get("role") != "admin":
        flash("Only admin can delete notes.", "warning")
        return redirect(url_for("notes"))
    if 0 <= idx < len(db["notes"]):
        db["notes"].pop(idx)
        save_db()
        flash("Note deleted.", "info")
    return redirect(url_for("notes"))

# ---------- Gallery ----------
@app.route("/gallery", methods=["GET", "POST"])
def gallery():
    if request.method == "POST":
        if session.get("role") != "admin":
            flash("Only admin can upload images.", "warning")
            return redirect(url_for("gallery"))
        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            file.save(filepath)
            db["gallery"].insert(0, {"filename": unique_filename, "uploaded_at": datetime.now().isoformat()})
            save_db()
            flash("Image uploaded.", "success")
    return render_template("gallery.html", gallery=db["gallery"])

@app.route("/delete_image/<int:idx>", methods=["POST"])
def delete_image(idx):
    if session.get("role") != "admin":
        flash("Only admin can delete images.", "warning")
        return redirect(url_for("gallery"))
    if 0 <= idx < len(db["gallery"]):
        filename = db["gallery"][idx]["filename"]
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db["gallery"].pop(idx)
        save_db()
        flash("Image deleted.", "info")
    return redirect(url_for("gallery"))

@app.route("/image/<int:idx>")
def view_image(idx):
    if 0 <= idx < len(db["gallery"]):
        image = db["gallery"][idx]
        return render_template("image_view.html", image=image, idx=idx)
    flash("Image not found.", "warning")
    return redirect(url_for("gallery"))

# ---------- Games ----------
@app.route("/game")
def game():
    return render_template("crossy_road.html")   # separate template for Crossy Road

@app.route("/chicken-game")
def chicken_game():
    return render_template("chicken_game.html")
@app.route("/fireworks")
def fireworks():
    return render_template("fireworks.html")
@app.route("/butterfly")
def butterfly():
    return render_template("butterfly.html")
@app.route("/snake-game")
def snake_game():
    return render_template("snake-game.html")
@app.route("/arrow-game")
def arrow_game():
    return render_template("arrow-game.html")
if __name__ == "__main__":
    app.run(debug=True)
