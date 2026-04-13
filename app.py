from flask import Flask, request, render_template, redirect, session

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return render_template("home.html")

# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Dummy login (no DB yet)
        username = request.form.get("username")
        password = request.form.get("password")

        if username and password:
            session["user"] = username
            return redirect("/user-form")
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

# ---------------- SIGNUP ---------------- #

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # Dummy signup (no DB yet)
        username = request.form.get("username")
        password = request.form.get("password")

        if username and password:
            return redirect("/login")
        else:
            return render_template("signup.html", error="Fill all fields")

    return render_template("signup.html")

# ---------------- USER FORM ---------------- #

@app.route("/user-form")
def user_form():
    if "user" not in session:
        return redirect("/login")
    return render_template("user_form.html")

# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    # Static dummy data for now
    data = [
        {
            "id": 1,
            "income": 50000,
            "loan": 200000,
            "status": "Pending"
        }
    ]

    return render_template("dashboard.html", data=data)

# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)