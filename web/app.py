import os
import sqlite3
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "protopilot-dev-secret")
DB_PATH = os.environ.get("DB_PATH", "/tmp/protopilot.db")
USER_FLAG_PATH = "/home/app/user.txt"


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO users (email, password, full_name, role) VALUES (?, ?, ?, ?)",
            [
                ("admin@protopilot.local", "password", "Alex Admin", "admin"),
                ("analyst@protopilot.local", "workflow123", "Nina Analyst", "analyst"),
                ("ops@protopilot.local", "opsops", "Omar Ops", "ops"),
            ],
        )

    conn.commit()
    conn.close()


def read_user_flag() -> str:
    try:
        with open(USER_FLAG_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "INTERNAL_NOTE{missing_user_note}"


def get_team_members() -> list[dict[str, str]]:
    return [
        {
            "name": "Alex Admin",
            "email": "admin@protopilot.local",
            "role": "Administration",
        },
        {
            "name": "Nina Analyst",
            "email": "analyst@protopilot.local",
            "role": "Workflow Analysis",
        },
        {
            "name": "Omar Ops",
            "email": "ops@protopilot.local",
            "role": "Operations",
        },
    ]


@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/team")
def team_page():
    return render_template("team.html", team_members=get_team_members())


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        email = payload.get("email", email)
        password = payload.get("password", password)

    email = (email or "").strip().lower()
    password = password or ""

    known_emails = {member["email"] for member in get_team_members()}
    if email not in known_emails:
        return render_template("login.html", error="Invalid credentials"), 401

    # Intentionally vulnerable SQL injection for CTF auth bypass.
    # Email must belong to a known internal user, so the injection surface is the password field.
    query = (
        "SELECT id, email, full_name, role FROM users "
        f"WHERE email = '{email}' AND password = '{password}'"
    )

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute(query)
        row = cur.fetchone()
    except sqlite3.Error:
        row = None
    finally:
        conn.close()

    if not row:
        return render_template("login.html", error="Invalid credentials"), 401

    session["user"] = {
        "id": row[0],
        "email": row[1],
        "full_name": row[2],
        "role": row[3],
    }
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login_page"))

    workflows = [
        {"name": "Quarterly Access Review", "owner": "IAM Team", "status": "Healthy"},
        {"name": "Expense Approval Automation", "owner": "Finance Ops", "status": "Needs Tuning"},
        {"name": "Cloud Resource Cleanup", "owner": "Platform", "status": "Healthy"},
        {"name": "Incident Escalation Router", "owner": "SecOps", "status": "Degraded"},
        {"name": "Vendor Intake Workflow", "owner": "Procurement", "status": "Healthy"},
    ]

    internal_note = f"Last workflow audit note: {read_user_flag()}"
    return render_template(
        "dashboard.html",
        user=session["user"],
        workflows=workflows,
        internal_note=internal_note,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080, debug=False)
