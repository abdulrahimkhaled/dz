
from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import config
import os

app = Flask(__name__)
app.secret_key = "your-secret-key"

def get_connection():
    return psycopg2.connect(config.DB_URI)

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT role FROM admins WHERE username = %s AND password_hash = %s", (username, password))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            session["username"] = username
            session["role"] = result[0]
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="بيانات الدخول غير صحيحة")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/subjects")
def subjects():
    if "username" not in session:
        return redirect("/login")
    return render_template("subjects.html")

@app.route("/professors")
def professors():
    if "username" not in session:
        return redirect("/login")
    return render_template("professors.html")

@app.route("/faq")
def faq():
    if "username" not in session:
        return redirect("/login")
    return render_template("faq.html")

@app.route("/lectures")
def lectures():
    if "username" not in session:
        return redirect("/login")
    return render_template("lectures.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
