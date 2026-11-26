import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps

import click
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "demo.sqlite3"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-secret-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"
csrf = CSRFProtect(app)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS login_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            success INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            ip_hint TEXT
        );
    """)
    demo_email = "annie@gmail.com"
    demo_password = os.environ.get("DEMO_PASSWORD", "DemoPass123!")
    conn.execute(
        "INSERT OR IGNORE INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
        (demo_email, generate_password_hash(demo_password), now())
    )

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if admin_email and admin_password:
        conn.execute(
            "INSERT OR IGNORE INTO admins (email, password_hash, created_at) VALUES (?, ?, ?)",
            (admin_email, generate_password_hash(admin_password), now())
        )

    conn.commit()
    conn.close()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


@app.cli.command("init-db")
def init_db_command():
    """Create the local SQLite database and a fictional demo account."""
    init_db()
    click.echo("Database ready. Fictional demo account: annie@gmail.com")
    click.echo("Demo password is set by DEMO_PASSWORD, or defaults to DemoPass123! for local testing.")


@app.cli.command("create-admin")
@click.argument("email")
@click.password_option()
def create_admin(email, password):
    """Create an administrator account: flask --app app create-admin EMAIL"""
    init_db()
    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute(
            "INSERT INTO admins (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email.strip().lower(), generate_password_hash(password), now())
        )
        conn.commit()
        click.echo("Administrator account created.")
    except sqlite3.IntegrityError:
        raise click.ClickException("An administrator with that email already exists.")
    finally:
        conn.close()


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; img-src 'self' data:; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    return response


@app.route("/", methods=["GET", "POST"])
def login():
    init_db()
    if request.method == "POST":
        email = "annie@gmail.com"
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        success = bool(user and check_password_hash(user["password_hash"], password))
        # Record the outcome only. Never save the submitted password.
        ip_hint = request.remote_addr or ""
        db().execute(
            "INSERT INTO login_events (email, success, created_at, ip_hint) VALUES (?, ?, ?, ?)",
            (email, int(success), now(), ip_hint[:64])
        )
        db().commit()
        if success:
            session.clear()
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            return redirect(url_for("welcome"))
        flash("That demo password did not match. Try the fictional test password shown in the README.", "error")
    return render_template("login.html")


@app.route("/welcome")
def welcome():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("welcome.html", email=session.get("user_email"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    init_db()
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        admin = db().execute("SELECT * FROM admins WHERE email = ?", (email,)).fetchone()
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_email"] = admin["email"]
            return redirect(url_for("admin_dashboard"))
        flash("Administrator sign-in failed.", "error")
    return render_template("admin_login.html")


@app.route("/admin")
@admin_required
def admin_dashboard():
    events = db().execute(
        "SELECT id, email, success, created_at, ip_hint FROM login_events ORDER BY id DESC LIMIT 100"
    ).fetchall()
    users = db().execute(
        "SELECT id, email, created_at FROM users ORDER BY id"
    ).fetchall()
    return render_template("admin.html", events=events, users=users)


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    db().execute("DELETE FROM users WHERE id = ?", (user_id,))
    db().commit()
    flash("Demo account deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/events/clear", methods=["POST"])
@admin_required
def clear_events():
    db().execute("DELETE FROM login_events")
    db().commit()
    flash("Login activity cleared.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
