
from flask import Flask, render_template, request, redirect, session, flash
import psycopg2
import config
import bcrypt
import os

app = Flask(__name__)
app.secret_key = "your-secret-key"

def get_db_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres.yejjnjtxqeguwelcrngz",
        password="dzireedzireE01",
        host="aws-0-eu-central-1.pooler.supabase.com",
        port="6543"
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash, role FROM admins WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
            session['user_id'] = user[0]
            session['role'] = user[2]
            return redirect('/dashboard')
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
            return redirect('/login')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return "أهلاً بك في لوحة التحكم!"
    return redirect('/login')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
