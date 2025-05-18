
from flask import Flask, render_template, request, redirect, session, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor
import config
import bcrypt
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def get_db_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres.yejjnjtxqeguwelcrngz",
        password="dzireedzireE01",
        host="aws-0-eu-central-1.pooler.supabase.com",
        port="6543"
    )


@app.route('/', methods=['GET', 'POST'])
def login():
    if 'admin' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cur.fetchone()
        cur.close()
        conn.close()

        try:
            if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
                session['role'] = admin['role']
                session['admin'] = admin['username']
                return redirect(url_for('dashboard'))
            else:
                flash('بيانات الدخول غير صحيحة.', 'danger')
        except ValueError:
            flash('⚠️ يوجد خطأ في تخزين كلمة المرور. يرجى حذف هذا المستخدم وإعادة تسجيله بشكل صحيح.', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', admin=session['admin'], role=session.get('role', 'view'))

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/register_admin', methods=['GET', 'POST'])
def register_admin():
    if 'admin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
        existing = cur.fetchone()

        if existing:
            flash('اسم المستخدم موجود مسبقًا.', 'error')
        else:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()
            cur.execute("INSERT INTO admins (username, password_hash) VALUES (%s, %s)", (username, hashed))
            conn.commit()
            flash('✅ تم تسجيل المشرف بنجاح.', 'success')

        cur.close()
        conn.close()

    return render_template('register_admin.html')

@app.route('/professors', methods=['GET', 'POST'])
def professors():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        name = request.form['name']
        dept = request.form['department']
        email = request.form['email']
        office = request.form['office']
        consultation = request.form['consultation']
        cur.execute("INSERT INTO professors (name, department, email, office, consultation) VALUES (%s, %s, %s, %s, %s)", (name, dept, email, office, consultation))
        conn.commit()
    cur.execute("SELECT * FROM professors ORDER BY name")
    professors = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('professors.html', professors=professors)

@app.route('/professors/edit/<int:professor_id>', methods=['POST'])
def edit_professor(professor_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    name = request.form['name']
    dept = request.form['department']
    email = request.form['email']
    office = request.form['office']
    consultation = request.form['consultation']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE professors SET name = %s, department = %s, email = %s, office = %s, consultation = %s WHERE id = %s",
                (name, dept, email, office, consultation, professor_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('professors'))

@app.route('/professors/delete/<int:professor_id>')
def delete_professor(professor_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM professors WHERE id = %s", (professor_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('professors'))


@app.route('/lectures', methods=['GET', 'POST'])
def lectures():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        subject_code = request.form['subject_code']
        professor_id = request.form['professor_id']
        day = request.form['day']
        time = request.form['time']
        room = request.form['room']
        cur.execute("INSERT INTO lectures (subject_code, professor_id, day, time, room) VALUES (%s, %s, %s, %s, %s)",
                    (subject_code, professor_id, day, time, room))
        conn.commit()

    cur.execute("SELECT * FROM subjects ORDER BY subject_name")
    subjects = cur.fetchall()
    cur.execute("SELECT * FROM professors ORDER BY name")
    professors = cur.fetchall()
    cur.execute("SELECT * FROM lectures")
    lectures = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('lectures.html', lectures=lectures, subjects=subjects, professors=professors)

@app.route('/lectures/edit/<int:lecture_id>', methods=['POST'])
def edit_lecture(lecture_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    subject_code = request.form['subject_code']
    professor_id = request.form['professor_id']
    day = request.form['day']
    time = request.form['time']
    room = request.form['room']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE lectures SET subject_code=%s, professor_id=%s, day=%s, time=%s, room=%s WHERE id=%s",
                (subject_code, professor_id, day, time, room, lecture_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('lectures'))

@app.route('/lectures/delete/<int:lecture_id>')
def delete_lecture(lecture_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM lectures WHERE id = %s", (lecture_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('lectures'))


@app.route('/exams', methods=['GET', 'POST'])
def exams():
    if 'admin' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        subject_code = request.form['subject_code']
        exam_date = request.form['exam_date']
        exam_time = request.form['exam_time']
        location = request.form['location']
        cur.execute("INSERT INTO exams (subject_code, exam_date, exam_time, location) VALUES (%s, %s, %s, %s)",
                    (subject_code, exam_date, exam_time, location))
        conn.commit()

    cur.execute("SELECT * FROM subjects ORDER BY subject_name")
    subjects = cur.fetchall()
    cur.execute("SELECT * FROM exams ORDER BY exam_date, exam_time")
    exams = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('exams.html', exams=exams, subjects=subjects)

@app.route('/exams/edit/<int:exam_id>', methods=['POST'])
def edit_exam(exam_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    subject_code = request.form['subject_code']
    exam_date = request.form['exam_date']
    exam_time = request.form['exam_time']
    location = request.form['location']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE exams SET subject_code = %s, exam_date = %s, exam_time = %s, location = %s WHERE id = %s",
                (subject_code, exam_date, exam_time, location, exam_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('exams'))

@app.route('/exams/delete/<int:exam_id>')
def delete_exam(exam_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM exams WHERE id = %s", (exam_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('exams'))


@app.route('/faq', methods=['GET', 'POST'])
def faq():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer']
        cur.execute("INSERT INTO faq (question, answer) VALUES (%s, %s)", (question, answer))
        conn.commit()

    cur.execute("SELECT * FROM faq ORDER BY id")
    faqs = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('faq.html', faqs=faqs)

@app.route('/faq/edit/<int:faq_id>', methods=['POST'])
def edit_faq(faq_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    question = request.form['question']
    answer = request.form['answer']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE faq SET question = %s, answer = %s WHERE id = %s", (question, answer, faq_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('faq'))

@app.route('/faq/delete/<int:faq_id>')
def delete_faq(faq_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM faq WHERE id = %s", (faq_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('faq'))


@app.route('/user_courses')
def user_courses():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT uc.user_id, s.subject_name
        FROM user_courses uc
        JOIN subjects s ON uc.subject_code = s.subject_code
        ORDER BY uc.user_id
    """)
    user_courses = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('user_courses.html', user_courses=user_courses)


@app.route('/roles', methods=['GET', 'POST'])
def roles():
    if 'admin' not in session or session.get('role') != 'full':
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        admin_id = request.form['admin_id']
        role = request.form['role']
        cur.execute("UPDATE admins SET role = %s WHERE id = %s", (role, admin_id))
        conn.commit()

    cur.execute("SELECT id, username, role FROM admins ORDER BY id")
    admins = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('roles.html', admins=admins)


@app.route('/subjects', methods=['GET', 'POST'])
def subjects():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST' and session.get('role') != 'view':
        name = request.form['subject_name']
        code = request.form['subject_code']
        credit = request.form['credit_hours']
        cur.execute("INSERT INTO subjects (subject_name, subject_code, credit_hours) VALUES (%s, %s, %s)", (name, code, credit))
        conn.commit()
    cur.execute("SELECT * FROM subjects ORDER BY subject_name")
    subjects = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('subjects.html', subjects=subjects, role=session.get('role', 'view'))

@app.route('/subjects/edit/<subject_code>', methods=['POST'])
def edit_subject(subject_code):
    if 'admin' not in session:
        return redirect(url_for('login'))
    name = request.form['subject_name']
    credit = request.form['credit_hours']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE subjects SET subject_name = %s, credit_hours = %s WHERE subject_code = %s", (name, credit, subject_code))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('subjects'))

@app.route('/subjects/delete/<subject_code>')
def delete_subject(subject_code):
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM subjects WHERE subject_code = %s", (subject_code,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('subjects'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
