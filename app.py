import os
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import (
    Flask, request, redirect, url_for, render_template,
    send_from_directory, flash, abort, jsonify
)
from werkzeug.utils import secure_filename

# ---------- Setup ----------
BASE_DIR = os.path.dirname(__file__)
# Save to the persistent volume folder!
# Check if the /data folder exists (Docker). If not, use local folder.
if os.path.exists("/data"):
    DB_PATH = "/data/app.db"
else:
    DB_PATH = os.path.join(BASE_DIR, "app.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.secret_key = "dev-key"
# Simple delete protection (change this!)
app.config["DELETE_CODE"] = os.getenv("DELETE_CODE", "naomi")

# ---------- DB Helpers ----------
def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            girl_name TEXT NOT NULL,
            story TEXT NOT NULL,
            tags TEXT,
            age TEXT,
            location TEXT,
            how_met TEXT,
            username TEXT,
            image_filename TEXT,
            likes INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            laugh_count INTEGER DEFAULT 0,
            shock_count INTEGER DEFAULT 0,
            skull_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
    """)
    con.commit()
    con.close()

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS

@app.before_request
def _setup():
    init_db()

# ---------- Time-ago Filter (NY Time) ----------
NY_TZ = ZoneInfo("America/New_York")

@app.template_filter("timeago")
def timeago(iso_str: str) -> str:
    """Convert UTC ISO timestamp to 'x days ago' in New York time."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00")).astimezone(NY_TZ)
    except Exception:
        dt = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(NY_TZ)

    now = datetime.now(NY_TZ)
    delta = now - dt
    s = int(delta.total_seconds())
    
    if s < 60:
        return "just now"
    m = s // 60
    if m < 60:
        return f"{m} minute{'s' if m!=1 else ''} ago"
    h = m // 60
    if h < 24:
        return f"{h} hour{'s' if h!=1 else ''} ago"
    d = h // 24
    if d < 7:
        return f"{d} day{'s' if d!=1 else ''} ago"
    w = d // 7
    if w < 5:
        return f"{w} week{'s' if w!=1 else ''} ago"
    mo = d // 30
    if mo < 12:
        return f"{mo} month{'s' if mo!=1 else ''} ago"
    y = d // 365
    return f"{y} year{'s' if y!=1 else ''} ago"

# ---------- Routes ----------
@app.route("/")
def home():
    return render_template("home.html")

# --- Search ---
@app.route("/search", methods=["GET", "POST"])
def search():
    results, query = [], ""
    if request.method == "POST":
        query = (request.form.get("girl_name") or "").strip()
        city = (request.form.get("city") or "").strip()
        school = (request.form.get("school") or "").strip()
        
        sql = "SELECT * FROM posts WHERE girl_name LIKE ?"
        params = [f"%{query}%"]
        
        if city:
            sql += " AND location LIKE ?"
            params.append(f"%{city}%")
        if school:
            sql += " AND how_met LIKE ?"
            params.append(f"%{school}%")
            
        con = get_db()
        results = con.execute(sql, params).fetchall()
        con.close()
    return render_template("search.html", results=results, query=query)

# --- Submit ---
@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        girl_name = (request.form.get("girl_name") or "").strip()
        story = (request.form.get("story") or "").strip()
        tags = (request.form.get("tags") or "").strip()
        age = (request.form.get("age") or "").strip()
        location = (request.form.get("location") or "").strip()
        how_met = (request.form.get("how_met") or "").strip()
        username = (request.form.get("username") or "").strip() or "Anonymous"
        
        if not girl_name or not story:
            flash("Name and story are required.")
            return redirect(url_for("submit"))

        filename = None
        file = request.files.get("image")
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path = os.path.join(UPLOAD_DIR, filename)
                
                # Avoid duplicate filenames
                if os.path.exists(path):
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{int(datetime.now().timestamp())}{ext}"
                    path = os.path.join(UPLOAD_DIR, filename)
                
                file.save(path)
            else:
                flash("Unsupported image type.")
                return redirect(url_for("submit"))

        con = get_db()
        con.execute("""
            INSERT INTO posts
            (girl_name, story, tags, age, location, how_met, username, image_filename, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (girl_name, story, tags, age, location, how_met, username, filename,
              datetime.now(NY_TZ).isoformat()))
        con.commit()
        con.close()
        flash("Story posted!")
        return redirect(url_for("stories"))
    return render_template("submit.html")

# --- Feed / Stories ---
@app.route("/stories")
def stories():
    sort = request.args.get("sort", "new")
    tag = (request.args.get("tag") or "").strip()
    
    order = {
        "new": "created_at DESC",
        "liked": "likes DESC, created_at DESC",
        "viewed": "views DESC, created_at DESC"
    }.get(sort, "created_at DESC")
    
    con = get_db()
    if tag:
        rows = con.execute(f"SELECT * FROM posts WHERE tags LIKE ? ORDER BY {order}", (f"%{tag}%",)).fetchall()
    else:
        rows = con.execute(f"SELECT * FROM posts ORDER BY {order}").fetchall()
    con.close()
    return render_template("stories.html", rows=rows, sort=sort, tag=tag)

# --- Story detail ---
@app.route("/story/<int:post_id>")
def story_detail(post_id):
    con = get_db()
    row = con.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    if not row:
        con.close()
        return render_template("404.html"), 404
    
    # Increment view count
    con.execute("UPDATE posts SET views = views + 1 WHERE id=?", (post_id,))
    con.commit()
    
    related = []
    if row["tags"]:
        key = row["tags"].split(",")[0].strip()
        related = con.execute(
            "SELECT * FROM posts WHERE id<>? AND tags LIKE ? LIMIT 6",
            (post_id, f"%{key}%")
        ).fetchall()
    con.close()
    return render_template("story_detail.html", row=row, related=related)

# --- React (emojis + heart) ---
@app.route("/react/<int:post_id>", methods=["POST"])
def react(post_id):
    kind = (request.form.get("kind") or "").lower()
    col_map = {
        "heart": "likes",
        "laugh": "laugh_count",
        "shock": "shock_count",
        "skull": "skull_count",
    }
    col = col_map.get(kind)
    if not col:
        abort(400)
    
    con = get_db()
    cur = con.execute(f"UPDATE posts SET {col} = {col} + 1 WHERE id=?", (post_id,))
    con.commit()
    con.close()
    
    if cur.rowcount == 0:
        abort(404)
    return ("", 204)

# --- About & Report ---
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        flash("Thanks for reporting. A moderator will review.")
        return redirect(url_for("stories"))
    return render_template("report.html")

# --- Delete Post ---
@app.route("/delete/<int:post_id>", methods=["GET", "POST"])
def delete_post(post_id):
    """
    GET: show confirm form
    POST: verify code, delete row + image, redirect to /stories with a flash
    """
    con = get_db()
    row = con.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    
    if not row:
        con.close()
        flash("Post not found.")
        return redirect(url_for("stories"))

    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        if code != app.config["DELETE_CODE"]:
            con.close()
            flash("Invalid delete code.")
            return redirect(url_for("delete_post", post_id=post_id))

        # Delete image file if present
        img = row["image_filename"]
        if img:
            img_path = os.path.join(UPLOAD_DIR, img)
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception:
                pass

        # Delete row
        con.execute("DELETE FROM posts WHERE id=?", (post_id,))
        con.commit()
        con.close()
        flash(f"Post #{post_id} deleted.")
        return redirect(url_for("stories"))

    con.close()
    return render_template("delete_confirm.html", row=row)

# --- Serve uploads ---
@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)




