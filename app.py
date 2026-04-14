from flask import Flask, request, render_template, redirect, session, jsonify
import sqlite3
import traceback

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ---------------- #

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname  TEXT,
        dob       TEXT,
        age       INTEGER,
        education TEXT,
        username  TEXT UNIQUE,
        email     TEXT,
        password  TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        username       TEXT,
        income         REAL    DEFAULT 0,
        loan           REAL    DEFAULT 0,
        age            INTEGER DEFAULT 0,
        employment     TEXT    DEFAULT 'Salaried',
        credit_history INTEGER DEFAULT 0,
        status         TEXT    DEFAULT 'Pending',
        submitted_on   TEXT    DEFAULT (date('now'))
    )
    """)

    # ✅ ROBUST MIGRATION: check existing columns before altering
    cursor.execute("PRAGMA table_info(applications)")
    existing_cols = [row[1] for row in cursor.fetchall()]

    if "submitted_on" not in existing_cols:
        # ❌ OLD (caused error)
        # cursor.execute("ALTER TABLE applications ADD COLUMN submitted_on TEXT DEFAULT (date('now'))")

        # ✅ FIXED (ONLY CHANGE)
        cursor.execute("ALTER TABLE applications ADD COLUMN submitted_on TEXT")

        # Backfill existing rows
        cursor.execute("UPDATE applications SET submitted_on = date('now') WHERE submitted_on IS NULL")

    conn.commit()
    conn.close()

init_db()

# ---------------- HELPERS ---------------- #

def is_logged_in():
    return "user" in session

def is_admin():
    return session.get("admin")

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def safe_int(val, default=0):
    try:
        return int(val) if val not in (None, '', 'None') else default
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    try:
        return float(val) if val not in (None, '', 'None') else default
    except (ValueError, TypeError):
        return default

def safe_str(val, default=''):
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default

# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return render_template("home.html")

# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/user-form")
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")

# ---------------- SIGNUP ---------------- #

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        fullname  = request.form.get("fullname", "").strip()
        dob       = request.form.get("dob", "")
        age       = safe_int(request.form.get("age"), 0)
        education = request.form.get("education", "").strip()
        username  = request.form.get("username", "").strip()
        email     = request.form.get("email", "").strip()
        password  = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("signup.html", error="Username and password are required")

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO users (fullname, dob, age, education, username, email, password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (fullname, dob, age, education, username, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("signup.html", error="Username already exists. Please choose another.")
        conn.close()
        return redirect("/login")

    return render_template("signup.html")

# ---------------- USER FORM ---------------- #

@app.route("/user-form")
def user_form():
    if not is_logged_in():
        return redirect("/login")
    return render_template("user_form.html")

# ---------------- SUBMIT FORM ---------------- #

@app.route("/submit-form", methods=["POST"])
def submit_form():
    if not is_logged_in():
        return redirect("/login")

    try:
        income         = safe_float(request.form.get("income"), 0.0)
        loan           = safe_float(request.form.get("loan"), 0.0)
        age            = safe_int(request.form.get("age"), 30)
        employment     = safe_str(request.form.get("employment_type"), "Salaried")
        credit_history = safe_int(request.form.get("credit_score"), 0)
        username       = session["user"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO applications (username, income, loan, age, employment, credit_history, status, submitted_on)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', date('now'))
        """, (username, income, loan, age, employment, credit_history))
        conn.commit()
        conn.close()

        return redirect("/dashboard")

    except Exception as e:
        traceback.print_exc()
        return "Form submission error: " + str(e), 500

# ---------------- USER DASHBOARD ---------------- #

@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, income, loan, age, employment, credit_history, status,
               COALESCE(submitted_on, 'N/A') as submitted_on
        FROM applications
        WHERE username=?
        ORDER BY id DESC
    """, (session["user"],))
    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "id":             row["id"],
            "username":       safe_str(row["username"]),
            "income":         safe_float(row["income"]),
            "loan":           safe_float(row["loan"]),
            "age":            safe_int(row["age"]),
            "employment":     safe_str(row["employment"], "N/A"),
            "credit_history": safe_int(row["credit_history"]),
            "status":         safe_str(row["status"], "Pending"),
            "submitted_on":   safe_str(row["submitted_on"], "N/A"),
        })

    return render_template("dashboard.html", data=data)

# ---------------- ADMIN LOGIN ---------------- #

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == "admin" and request.form.get("password") == "admin123":
            session["admin"] = True
            return redirect("/admin-dashboard")
        else:
            return render_template("admin.html", error="Invalid Admin Credentials")
    return render_template("admin.html")

# ---------------- ADMIN DASHBOARD PAGE ---------------- #

@app.route("/admin-dashboard")
def admin_dashboard():
    if not is_admin():
        return redirect("/admin")
    return render_template("admin_dashboard.html")

# ---------------- API: GET ALL APPLICATIONS ---------------- #

@app.route("/api/applications")
def api_applications():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                a.id,
                a.username,
                a.income,
                a.loan,
                a.age          AS app_age,
                a.employment,
                a.credit_history,
                a.status,
                COALESCE(a.submitted_on, 'N/A') AS submitted_on,
                u.fullname,
                u.dob,
                u.age          AS user_age,
                u.education,
                u.email
            FROM applications a
            LEFT JOIN users u ON a.username = u.username
            ORDER BY a.id DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            income = safe_float(row["income"])
            loan   = safe_float(row["loan"])
            age    = safe_int(row["app_age"]) or safe_int(row["user_age"]) or 30
            cibil  = safe_int(row["credit_history"])
            emp    = safe_str(row["employment"], "Salaried")
            fname  = safe_str(row["fullname"]) or safe_str(row["username"]) or "Unknown"

            if income < 10000:
                income_range = "0-10K"
            elif income < 50000:
                income_range = "10K-50K"
            elif income < 100000:
                income_range = "50K-1L"
            else:
                income_range = "1L+"

            result.append({
                "id":          int(row["id"]),
                "app_id":      "SBI-" + str(1000 + int(row["id"])),
                "username":    safe_str(row["username"]),
                "fullName":    fname,
                "dob":         safe_str(row["dob"]),
                "age":         age,
                "education":   safe_str(row["education"]),
                "email":       safe_str(row["email"]),
                "income":      income,
                "incomeRange": income_range,
                "loan":        loan,
                "loanAmount":  str(int(loan)),
                "loanType":    emp,
                "employment":  emp,
                "cibil":       cibil,
                "status":      safe_str(row["status"], "Pending"),
                "submittedOn": safe_str(row["submitted_on"], "N/A"),
            })

        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ---------------- API: UPDATE STATUS ---------------- #

@app.route("/api/update-status", methods=["POST"])
def api_update_status():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data   = request.get_json(force=True)
        app_id = data.get("id")
        status = data.get("status")

        allowed = ["Pending", "Approved", "Rejected", "Under Review"]
        if status not in allowed:
            return jsonify({"error": "Invalid status"}), 400

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "id": app_id, "status": status})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ---------------- RESULT PAGE ---------------- #

@app.route("/result")
def result():
    return render_template("result.html")

# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

@app.route("/admin-logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/")

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)