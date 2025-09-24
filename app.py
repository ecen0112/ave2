from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import uuid
import json
from functools import wraps
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure secret key for production

# Define a custom Jinja2 filter for datetime formatting
@app.template_filter('datetime')
def format_datetime(value):
    if value:
        try:
            return datetime.fromisoformat(value).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f"Error parsing datetime: {value} at {datetime.now().strftime('%H:%M:%S')}")
            return value
    return value

# Upload folder setup
UPLOAD_FOLDER = "static/uploads"
MEMORIES_PHOTO_FOLDER = "static/memories"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MEMORIES_PHOTO_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MEMORIES_PHOTO_FOLDER"] = MEMORIES_PHOTO_FOLDER

# DB file paths
DB_FILE = "data.json"
MUSIC_FILE = "music.json"

# Function to save the main database to a JSON file
def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        print(f"Database saved to {DB_FILE} at {datetime.now().strftime('%H:%M:%S')}")
        return True
    except Exception as e:
        print(f"Error saving database: {e} at {datetime.now().strftime('%H:%M:%S')}")
        flash(f"Failed to save database: {e}", "error")
        return False

# Function to load the main database from a JSON file
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                loaded_db = json.load(f)
                if isinstance(loaded_db.get("ideas", []), list) and all(isinstance(i, str) for i in loaded_db.get("ideas", [])):
                    loaded_db["ideas"] = [{"text": i, "status": "Planned"} for i in loaded_db["ideas"]]
                return loaded_db
        except json.JSONDecodeError as e:
            print(f"Error decoding {DB_FILE}: {e}. Using default data at {datetime.now().strftime('%H:%M:%S')}")
    return {
        "users": [
            {"username": "BUNBUN", "password": "09132025", "role": "erl"},
            {"username": "BUNNY", "password": "09132025", "role": "love"}
        ],
        "ideas": [{"text": "Go for a picnic", "status": "Planned"}, {"text": "Watch a movie together", "status": "Planned"}],
        "memories": [{"text": "Our first date", "category": "Romantic", "timestamp": "2025-09-13T12:00:00", "photo": ""}],
        "notes": [{"text": "Don’t forget the anniversary gift!", "timestamp": datetime.now().isoformat()}, {"text": "Plan next weekend", "timestamp": datetime.now().isoformat()}],
        "gallery": []
    }

# Load existing images from disk on startup
def load_gallery():
    files = os.listdir(app.config["UPLOAD_FOLDER"])
    gallery = []
    for filename in sorted(files, reverse=True):
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


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or not session['username']:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        print(f"Authenticated user: {session['username']}, Role: {session.get('role')} at {datetime.now().strftime('%H:%M:%S')}")
        return f(*args, **kwargs)
    return decorated_function

# ---------- Auth Routes ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if 'username' in session and session['username']:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        session.clear()
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        for user in db["users"]:
            if user["username"] == u and user["password"] == p:
                session["username"] = u
                session["role"] = user["role"]
                flash(f"Signed in as {u} ({user['role']})", "success")
                print(f"Login success: {u}, Role: {user['role']} at {datetime.now().strftime('%H:%M:%S')}")
                return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")  # Changed from "danger" to "error"
        print(f"Login failed for username: {u} at {datetime.now().strftime('%H:%M:%S')}")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# ---------- Debug and Diagnose Routes ----------
@app.route("/debug")
@login_required  # Added login_required for security
def debug():
    return f"Session: {dict(session)}<br>DB Users: {db['users']}<br>Memories: {db['memories']}<br>Gallery: {db['gallery']}"

@app.route("/diagnose")
@login_required
def diagnose():
    return (
        f"Time: {datetime.now().strftime('%H:%M:%S')}<br>"
        f"User: {session.get('username')}<br>"
        f"Role: {session.get('role')}<br>"
        f"Memories Count: {len(db['memories'])}<br>"
        f"Gallery Length: {len(db['gallery'])}<br>"
        f"DB File Exists: {os.path.exists(DB_FILE)}<br>"
        f"Music File Exists: {os.path.exists(MUSIC_FILE)}<br>"
        f"Upload Folder Exists: {os.path.exists(UPLOAD_FOLDER)}<br>"
        f"Memories Folder Exists: {os.path.exists(MEMORIES_PHOTO_FOLDER)}<br>"
        f"DB Write Test: {save_db()}"
    )

# ---------- Dashboard ----------
@app.route("/")
@app.route("/dashboard")
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
    relationship_start_str = "2025-09-13"
    relationship_start = datetime.strptime(relationship_start_str, "%Y-%m-%d")
    days_together = (datetime.now() - relationship_start).days
    anniv_month = relationship_start.month
    anniv_day = relationship_start.day
    today = datetime.now()
    next_anniv = datetime(today.year, anniv_month, anniv_day)
    if next_anniv < today:
        if anniv_month == 12:
            next_anniv = datetime(today.year + 1, 1, anniv_day)
        else:
            next_anniv = datetime(today.year, anniv_month + 1, anniv_day)
    gallery_preview = [{"idx": i, "filename": img["filename"]} for i, img in enumerate(db["gallery"][:6])]
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
@login_required
def ideas():
    if request.method == "POST":
        role = session.get("role")
        if not role or role not in ["erl", "love"]:
            flash("Only admins can add ideas.", "warning")
            return redirect(url_for("ideas"))
        idea = request.form.get("idea", "").strip()
        status = request.form.get("status", "Planned").strip()
        if idea:
            db["ideas"].insert(0, {"text": idea, "status": status})
            if save_db():
                flash("Idea added successfully!", "success")
            else:
                flash("Failed to save idea. Please try again.", "error")
        else:
            flash("Idea cannot be empty.", "warning")
    return render_template("ideas.html", ideas=db["ideas"])

@app.route("/edit_idea/<int:idx>", methods=["POST"])
@login_required
def edit_idea(idx):
    role = session.get("role")
    if not role or role not in ["erl", "love"]:
        flash("Only admins can edit ideas.", "warning")
        return redirect(url_for("ideas"))
    if 0 <= idx < len(db["ideas"]):
        new_text = request.form.get("new_text", "").strip()
        if new_text and new_text != db["ideas"][idx]["text"]:
            db["ideas"][idx]["text"] = new_text
            db["ideas"][idx]["timestamp"] = datetime.now().isoformat()
            if save_db():
                flash("Idea updated successfully!", "success")
            else:
                flash("Failed to update idea. Please try again.", "error")
        else:
            flash("New text cannot be empty or unchanged.", "warning")
    else:
        flash("Invalid idea index.", "warning")
        print(f"Error: Invalid index {idx} for edit_idea at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("ideas"))

@app.route("/delete_idea/<int:idx>", methods=["POST"])
@login_required
def delete_idea(idx):
    role = session.get("role")
    if not role or role != "erl":
        flash("Only admins can delete ideas.", "warning")
        return redirect(url_for("ideas"))
    if 0 <= idx < len(db["ideas"]):
        db["ideas"].pop(idx)
        if save_db():
            flash("Idea deleted successfully.", "info")
        else:
            flash("Failed to delete idea. Please try again.", "error")
    else:
        flash("Invalid idea index.", "warning")
        print(f"Error: Invalid index {idx} for delete_idea at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("ideas"))

@app.route("/toggle_idea_status/<int:idx>", methods=["POST"])
@login_required
def toggle_idea_status(idx):
    role = session.get("role")
    if not role or role not in ["erl", "love"]:
        flash("Only admins can toggle idea status.", "warning")
        return redirect(url_for("ideas"))
    if 0 <= idx < len(db["ideas"]):
        new_status = request.form.get("new_status", "Planned").strip()
        if new_status in ["Planned", "Completed"]:
            if isinstance(db["ideas"][idx], str):
                db["ideas"][idx] = {"text": db["ideas"][idx], "status": "Planned"}
            db["ideas"][idx]["status"] = new_status
            if save_db():
                flash(f"Idea marked as {new_status} successfully!", "success")
            else:
                flash("Failed to update status. Please try again.", "error")
        else:
            flash("Invalid status value.", "warning")
    else:
        flash("Invalid idea index.", "warning")
        print(f"Error: Invalid index {idx} for toggle_idea_status at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("ideas"))

# ---------- Memories ----------
@app.route("/memories", methods=["GET", "POST"])
@login_required
def memories():
    if request.method == "POST":
        role = session.get("role")
        if not role or role not in ["erl", "love"]:
            flash("Only admins can add memories.", "warning")
            return redirect(url_for("memories"))
        memory_text = request.form.get("memory", "").strip()
        category = request.form.get("category", "Uncategorized").strip()
        photo_filename = ""
        file = request.files.get("photo")
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(app.config["MEMORIES_PHOTO_FOLDER"], unique_filename)
            try:
                file.save(filepath)
                photo_filename = unique_filename
            except Exception as e:
                flash(f"Failed to save photo: {e}", "error")
                print(f"Error saving photo: {e} at {datetime.now().strftime('%H:%M:%S')}")
                return redirect(url_for("memories"))
        if memory_text:
            db["memories"].insert(0, {
                "text": memory_text,
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "photo": photo_filename
            })
            if save_db():
                flash("Memory added successfully!", "success")
            else:
                flash("Failed to save memory. Please try again.", "error")
        else:
            flash("Memory text cannot be empty.", "warning")
    return render_template("memories.html", memories=db["memories"])

@app.route("/edit_memory/<int:idx>", methods=["POST"])
@login_required
def edit_memory(idx):
    role = session.get("role")
    if not role or role not in ["erl", "love"]:
        flash("Only admins can edit memories.", "warning")
        return redirect(url_for("memories"))
    if 0 <= idx < len(db["memories"]):
        new_text = request.form.get("new_text", "").strip()
        if new_text and new_text != db["memories"][idx]["text"]:
            db["memories"][idx]["text"] = new_text
            db["memories"][idx]["timestamp"] = datetime.now().isoformat()
            if save_db():
                flash("Memory updated successfully!", "success")
            else:
                flash("Failed to update memory. Please try again.", "error")
        else:
            flash("New text cannot be empty or unchanged.", "warning")
    else:
        flash("Invalid memory index.", "warning")
        print(f"Error: Invalid index {idx} for edit_memory at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("memories"))

@app.route("/delete_memory/<int:idx>", methods=["POST"])
@login_required
def delete_memory(idx):
    role = session.get("role")
    if not role or role != "erl":
        flash("Only admins can delete memories.", "warning")
        return redirect(url_for("memories"))
    if 0 <= idx < len(db["memories"]):
        photo = db["memories"][idx].get("photo")
        if photo:
            filepath = os.path.join(app.config["MEMORIES_PHOTO_FOLDER"], photo)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Error deleting photo {photo}: {e} at {datetime.now().strftime('%H:%M:%S')}")
        db["memories"].pop(idx)
        if save_db():
            flash("Memory deleted successfully.", "info")
        else:
            flash("Failed to delete memory. Please try again.", "error")
    else:
        flash("Invalid memory index.", "warning")
        print(f"Error: Invalid index {idx} for delete_memory at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("memories"))

# ---------- Notes ----------
@app.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    if request.method == "POST":
        role = session.get("role")
        if not role or role not in ["erl", "love"]:
            flash("Only admins can add notes.", "warning")
            return redirect(url_for("notes"))
        note = request.form.get("note", "").strip()
        if note:
            db["notes"].insert(0, {"text": note, "timestamp": datetime.now().isoformat()})
            if save_db():
                flash("Note added successfully!", "success")
            else:
                flash("Failed to save note. Please try again.", "error")
        else:
            flash("Note cannot be empty.", "warning")
    return render_template("notes.html", notes=db["notes"])

@app.route("/delete_note/<int:idx>", methods=["POST"])
@login_required
def delete_note(idx):
    role = session.get("role")
    if not role or role != "erl":
        flash("Only admins can delete notes.", "warning")
        return redirect(url_for("notes"))
    if 0 <= idx < len(db["notes"]):
        db["notes"].pop(idx)
        if save_db():
            flash("Note deleted successfully.", "info")
        else:
            flash("Failed to delete note. Please try again.", "error")
    else:
        flash("Invalid note index.", "warning")
        print(f"Error: Invalid index {idx} for delete_note at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("notes"))

@app.route("/delete_image_note/<int:idx>", methods=["POST"])
@login_required
def delete_image_note(idx):
    role = session.get("role")
    if not role or role not in ["erl", "love"]:
        flash("Only admins can delete image notes.", "warning")
        return redirect(url_for("view_image", idx=idx))
    if 0 <= idx < len(db["gallery"]):
        db["gallery"][idx]["note"] = ""
        if save_db():
            flash("Image note deleted successfully.", "info")
        else:
            flash("Failed to delete image note. Please try again.", "error")
    else:
        flash("Invalid image index.", "warning")
        print(f"Error: Invalid index {idx} for delete_image_note at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("view_image", idx=idx))

# ---------- Gallery ----------
@app.route("/gallery", methods=["GET", "POST"])
@login_required
def gallery():
    if request.method == "POST":
        role = session.get("role")
        if not role or role not in ["erl", "love"]:
            flash("Only admins can upload images.", "warning")
            return redirect(url_for("gallery"))
        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            try:
                file.save(filepath)
                db["gallery"].insert(0, {"filename": unique_filename, "uploaded_at": datetime.now().isoformat(), "note": ""})
                if save_db():
                    flash("Image uploaded successfully!", "success")
                else:
                    flash("Failed to save image. Please try again.", "error")
            except Exception as e:
                flash(f"Failed to save image: {e}", "error")
                print(f"Error saving image: {e} at {datetime.now().strftime('%H:%M:%S')}")
        else:
            flash("No image selected.", "warning")
    return render_template("gallery.html", gallery=db["gallery"])

@app.route("/image/<int:idx>", methods=["GET", "POST"])
@login_required
def view_image(idx):
    if not (0 <= idx < len(db["gallery"])):
        flash("Image not found.", "warning")
        print(f"Error: Invalid index {idx} for view_image at {datetime.now().strftime('%H:%M:%S')}")
        return redirect(url_for("gallery"))
    image = db["gallery"][idx]
    if request.method == "POST":
        role = session.get("role")
        if not role or role not in ["erl", "love"]:
            flash("Only admins can add notes.", "warning")
            return redirect(url_for("view_image", idx=idx))
        note = request.form.get("note", "").strip()
        if note:
            try:
                old_note = image.get("note", "")
                image["note"] = note
                if save_db():
                    if old_note:
                        flash("Note updated successfully!", "success")
                    else:
                        flash("Note added successfully!", "success")
                else:
                    raise Exception("Database save failed")
            except Exception as e:
                flash(f"Failed to save note: {e}. Please try again.", "error")
                print(f"Error adding note: {e} at {datetime.now().strftime('%H:%M:%S')}")
        else:
            flash("Note cannot be empty.", "warning")
    return render_template("image_view.html", image=image, idx=idx)

@app.route("/delete_image/<int:idx>", methods=["POST"])
@login_required
def delete_image(idx):
    role = session.get("role")
    if not role or role != "erl":
        flash("Only admins can delete images.", "warning")
        return redirect(url_for("gallery"))
    if 0 <= idx < len(db["gallery"]):
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], db["gallery"][idx]["filename"])
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error deleting image {filepath}: {e} at {datetime.now().strftime('%H:%M:%S')}")
        db["gallery"].pop(idx)
        if save_db():
            flash("Image deleted successfully.", "info")
        else:
            flash("Failed to delete image. Please try again.", "error")
    else:
        flash("Invalid image index.", "warning")
        print(f"Error: Invalid index {idx} for delete_image at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("gallery"))

# ---------- Music Routes ----------
# ... (other imports and code from your app.py remain unchanged) ...

# ... (other imports and code from your app.py remain unchanged) ...

# Music data handling
def load_music():
    if os.path.exists(MUSIC_FILE):
        try:
            with open(MUSIC_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    print(f"Error: {MUSIC_FILE} contains invalid data format, expected list at {datetime.now().strftime('%H:%M:%S')}")
                    return []
                sanitized_data = []
                for item in data:
                    if not isinstance(item, dict):
                        print(f"Error: Invalid item in {MUSIC_FILE}: {item} at {datetime.now().strftime('%H:%M:%S')}")
                        continue
                    item.setdefault("song", "")
                    item.setdefault("artist", "")
                    item.setdefault("url", None)
                    item.setdefault("thumbnail", None)
                    item.setdefault("placement", "General")
                    sanitized_data.append(item)
                print(f"Loaded {len(sanitized_data)} music items from {MUSIC_FILE} at {datetime.now().strftime('%H:%M:%S')}")
                return sanitized_data
        except json.JSONDecodeError as e:
            print(f"Error decoding {MUSIC_FILE}: {e}. Using empty list at {datetime.now().strftime('%H:%M:%S')}")
            return []
        except Exception as e:
            print(f"Unexpected error loading {MUSIC_FILE}: {e} at {datetime.now().strftime('%H:%M:%S')}")
            return []
    print(f"{MUSIC_FILE} not found, using empty list at {datetime.now().strftime('%H:%M:%S')}")
    return []

def save_music(music_items):
    try:
        with open(MUSIC_FILE, "w", encoding="utf-8") as f:
            json.dump(music_items, f, indent=4, ensure_ascii=False)
        print(f"Music database saved to {MUSIC_FILE} with {len(music_items)} items at {datetime.now().strftime('%H:%M:%S')}")
        return True
    except Exception as e:
        print(f"Error saving music database: {e} at {datetime.now().strftime('%H:%M:%S')}")
        flash(f"Failed to save music database: {e}", "error")
        return False

def is_valid_youtube_url(url):
    pattern = r'^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$'
    return bool(re.match(pattern, url))

def convert_youtube_url(url):
    if not url or not is_valid_youtube_url(url):
        return None
    if "watch?v=" in url:
        return url.replace("watch?v=", "embed/")
    elif "youtu.be/" in url:
        return url.replace("youtu.be/", "youtube.com/embed/")
    return url

def extract_thumbnail(url):
    if not url or not is_valid_youtube_url(url):
        return None
    video_id = None
    if "watch?v=" in url:
        video_id = url.split("watch?v=")[-1].split("&")[0]
    elif "embed/" in url:
        video_id = url.split("embed/")[-1].split("?")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[-1].split("?")[0]
    if video_id:
        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    return None

@app.route("/music", methods=["GET", "POST"])
@login_required
def music():
    music_items = load_music()
    if request.method == "POST":
        role = session.get("role")
        if not role or role not in ["erl", "love"]:
            flash("Only admins can add music.", "warning")
            return redirect(url_for("music"))
        song = request.form.get("song", "").strip()
        artist = request.form.get("artist", "").strip()
        url = request.form.get("url", "").strip()
        placement = request.form.get("placement", "General").strip()
        custom = request.form.get("custom_placement", "").strip()

        if not (song and artist and url):
            flash("Song, artist, and URL are required.", "warning")
            return redirect(url_for("music"))
        if not is_valid_youtube_url(url):
            flash("Invalid YouTube URL.", "warning")
            return redirect(url_for("music"))

        if placement == "Custom" and custom.strip():
            placement = custom

        embed_url = convert_youtube_url(url)
        thumbnail = extract_thumbnail(url)

        music_items.append({
            "song": song,
            "artist": artist,
            "url": embed_url,
            "thumbnail": thumbnail,
            "placement": placement
        })
        if save_music(music_items):
            flash("Music added successfully!", "success")
        else:
            flash("Failed to save music. Please try again.", "error")
        return redirect(url_for("music"))

    grouped_items = {}
    for global_index, item in enumerate(music_items):
        placement = item.get("placement", "General")
        if placement not in grouped_items:
            grouped_items[placement] = []
        item_copy = item.copy()
        item_copy["global_index"] = global_index
        grouped_items[placement].append(item_copy)

    print(f"Rendering music.html with {len(music_items)} items: {grouped_items} at {datetime.now().strftime('%H:%M:%S')}")
    return render_template("music.html", grouped_items=grouped_items)

@app.route("/remove_music/<int:index>", methods=["POST"])
@login_required
def remove_music(index):
    music_items = load_music()
    role = session.get("role")
    if not role or role != "erl":
        flash("Only admins can delete music.", "warning")
        return redirect(url_for("music"))
    if 0 <= index < len(music_items):
        music_items.pop(index)
        if save_music(music_items):
            flash("Music removed successfully.", "info")
        else:
            flash("Failed to remove music. Please try again.", "error")
    else:
        flash("Invalid music index.", "warning")
        print(f"Error: Invalid index {index} for remove_music at {datetime.now().strftime('%H:%M:%S')}")
    return redirect(url_for("music"))

@app.route("/edit_music/<int:index>", methods=["GET", "POST"])
@login_required
def edit_music(index):
    music_items = load_music()
    role = session.get("role")
    if not role or role not in ["erl", "love"]:
        flash("Only admins can edit music.", "warning")
        return redirect(url_for("music"))

    if not (0 <= index < len(music_items)):
        flash("Invalid music index.", "warning")
        print(f"Error: Invalid index {index} for edit_music, music_items length: {len(music_items)} at {datetime.now().strftime('%H:%M:%S')}")
        return redirect(url_for("music"))

    # Ensure item has all required fields
    item = music_items[index]
    item.setdefault("song", "")
    item.setdefault("artist", "")
    item.setdefault("url", None)
    item.setdefault("thumbnail", None)
    item.setdefault("placement", "General")

    if request.method == "POST":
        song = request.form.get("song", "").strip()
        artist = request.form.get("artist", "").strip()
        url = request.form.get("url", "").strip()
        placement = request.form.get("placement", "General").strip()
        custom = request.form.get("custom_placement", "").strip()

        if not (song and artist and url):
            flash("Song, artist, and URL are required.", "warning")
            return redirect(url_for("edit_music", index=index))
        if not is_valid_youtube_url(url):
            flash("Invalid YouTube URL.", "warning")
            return redirect(url_for("edit_music", index=index))

        if placement == "Custom" and custom.strip():
            placement = custom

        embed_url = convert_youtube_url(url)
        new_thumbnail = extract_thumbnail(url) if url != item.get("url") else item.get("thumbnail")

        try:
            music_items[index] = {
                "song": song,
                "artist": artist,
                "url": embed_url,
                "thumbnail": new_thumbnail,
                "placement": placement
            }
            if save_music(music_items):
                flash("Music updated successfully!", "success")
            else:
                flash("Failed to update music. Please try again.", "error")
        except Exception as e:
            flash(f"Error updating music: {e}", "error")
            print(f"Error updating music: {e} at {datetime.now().strftime('%H:%M:%S')}")
        return redirect(url_for("music"))

    print(f"Rendering edit_music.html with item: {item}, index: {index} at {datetime.now().strftime('%H:%M:%S')}")
    return render_template("edit_music.html", item=item, index=index)

# ... (rest of your app.py remains unchanged) ...
# ... (rest of your app.py remains unchanged) ...
# ---------- Game Routes ----------
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

@app.route("/flower")
@login_required
def flower():
    return render_template("flower.html")

@app.route("/heart")
@login_required
def heart():
    return render_template("heart.html")

if __name__ == "__main__":
    app.run(debug=True)