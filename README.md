# Heard it from him (Flask demo)

A lightweight Flask app inspired by "The tea app"—but scoped for campus *stories from guys about their dating experiences*.  
It demonstrates basic CRUD-ish flows, reactions, search, filters, file uploads, and (intentionally) **one minor input validation flaw** for your Software Security assignment.

> ⚠️ **Ethics & Safety:** This demo ships with a **Report** flow and an **About/Rules** page. Please moderate responsibly, avoid harassment/defamation, and keep posts respectful and anonymized.

## Features & Routes

- `GET|POST /search` — search by name with optional city/school filters
- `GET|POST /submit` — submit a story with optional image upload and metadata
- `GET /stories` — browse the feed with sort (new/liked/viewed) and tag filters
- `POST /like/<id>` — react/like via AJAX-friendly endpoint
- `GET /story/<id>` — story detail with related items
- Extras: `/about`, `/report`, `/tag/<tag>`

## App Structure

```
heard_it_from_him/
├─ app.py
├─ app.db                # created automatically on first run
├─ templates/
│  ├─ base.html
│  ├─ search.html
│  ├─ submit.html
│  ├─ stories.html
│  ├─ story_detail.html
│  ├─ about.html
│  ├─ report.html
│  ├─ 404.html
|  ├─ delete_confirm.html
|  ├─ home.html
└─ static/
   └─ uploads/   
       └─ images 
```

## Intentional Minor Vulnerability

- **Filename-only image validation**: in `allowed_file()` we only check the file extension and do **not** verify MIME type or magic bytes.  
  - Location: `app.py` → `allowed_file()` and `/submit` upload flow.
  - Risk: a non-image payload could be uploaded if renamed with an allowed extension. In a real deployment, you should validate MIME and file headers (Pillow, `imghdr`, or explicit magic-bytes checks) and store outside of web root or use signed download URLs.

## Security Practices Demonstrated

- Parameterized queries for search and inserts (SQLite + parameters)
- `secure_filename` for uploads
- CSRF-lite: POST-only for like/report actions (for full CSRF, add WTForms/Flask-WTF)
- Output encoding via Jinja templates (autoescape enabled)

## Quickstart

1. Create and activate a venv, then install Flask:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install flask
   ```
2. Run the app:
   ```bash
   python app.py
   ```
3. Open http://127.0.0.1:5000

