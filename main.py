
from flask import Flask, request, render_template, redirect, url_for, session, flash
import config
import psycopg2
import os


app = Flask(__name__)
app.secret_key = "d71f3b3e1d5a499f8f87cbb721e9f83e37a2f7dbb1c946efbc7ed308a4161e29"




def get_connection():
    return psycopg2.connect(config.DB_URI)



@app.route("/")
def index():
    return "✅ التطبيق يعمل بنجاح"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, role FROM admins WHERE username=%s AND password=%s", (username, password))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            session["admin_id"] = row[0]
            session["username"] = username
            session["role"] = row[1]
            return redirect(url_for("dashboard"))
        else:
            flash("بيانات الدخول غير صحيحة", "error")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", admin=session["username"], role=session["role"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/subjects", methods=["GET", "POST"])
def subjects():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        cur.execute("INSERT INTO subjects (subject_name, subject_code, credit_hours) VALUES (%s, %s, %s)", (
            request.form["subject_name"], request.form["subject_code"], request.form["credit_hours"]))
        conn.commit()
    cur.execute("SELECT * FROM subjects")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("subjects.html", subjects=data, role=session["role"])

@app.route("/professors", methods=["GET", "POST"])
def professors():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        cur.execute("INSERT INTO professors (name, department, email, office, consultation) VALUES (%s, %s, %s, %s, %s)", (
            request.form["name"], request.form["department"], request.form["email"], request.form["office"], request.form["consultation"]))
        conn.commit()
    cur.execute("SELECT * FROM professors")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("professors.html", professors=data, role=session["role"])

@app.route("/faq", methods=["GET", "POST"])
def faq():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        cur.execute("INSERT INTO faq (question, answer) VALUES (%s, %s)", (
            request.form["question"], request.form["answer"]))
        conn.commit()
    cur.execute("SELECT * FROM faq")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("faq.html", faqs=data, role=session["role"])

@app.route("/lectures", methods=["GET", "POST"])
def lectures():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        cur.execute("INSERT INTO lectures (subject_code, day, time, room, professor_id) VALUES (%s, %s, %s, %s, %s)", (
            request.form["subject_code"], request.form["day"], request.form["time"], request.form["room"], request.form["professor_id"]))
        conn.commit()
    cur.execute("SELECT l.*, s.subject_name, p.name FROM lectures l JOIN subjects s ON l.subject_code = s.subject_code LEFT JOIN professors p ON l.professor_id = p.id")
    data = cur.fetchall()
    cur.execute("SELECT subject_code, subject_name FROM subjects")
    subjects = cur.fetchall()
    cur.execute("SELECT id, name FROM professors")
    professors = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("lectures.html", lectures=data, subjects=subjects, professors=professors, role=session["role"])

@app.route("/exams", methods=["GET", "POST"])
def exams():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        cur.execute("INSERT INTO exams (subject_code, exam_date, exam_time, location) VALUES (%s, %s, %s, %s)", (
            request.form["subject_code"], request.form["exam_date"], request.form["exam_time"], request.form["location"]))
        conn.commit()
    cur.execute("SELECT e.*, s.subject_name FROM exams e JOIN subjects s ON e.subject_code = s.subject_code")
    data = cur.fetchall()
    cur.execute("SELECT subject_code, subject_name FROM subjects")
    subjects = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("exams.html", exams=data, subjects=subjects, role=session["role"])

@app.route("/user_courses")
def user_courses():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT uc.user_id, s.subject_name FROM user_courses uc JOIN subjects s ON uc.subject_code = s.subject_code")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("user_courses.html", user_courses=data, role=session["role"])

@app.route("/roles", methods=["GET", "POST"])
def roles():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        cur.execute("UPDATE admins SET role = %s WHERE id = %s", (
            request.form["role"], request.form["admin_id"]))
        conn.commit()
    cur.execute("SELECT id, username, role FROM admins ORDER BY id")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("roles.html", admins=data, role=session["role"])

if __name__ == "__main__":
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
