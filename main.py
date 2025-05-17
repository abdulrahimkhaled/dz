
from flask import Flask, request, render_template, redirect, url_for, session, flash
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
import config
import psycopg2
import spacy
import spacy.cli
spacy.cli.download("xx_ent_wiki_sm")
from sentence_transformers import SentenceTransformer, util
import torch

app = Flask(__name__)
app.secret_key = "d71f3b3e1d5a499f8f87cbb721e9f83e37a2f7dbb1c946efbc7ed308a4161e29"

bot = Bot(token=config.TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

nlp = spacy.load("xx_ent_wiki_sm")
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def get_connection():
    return psycopg2.connect(config.DB_URI)

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="bot_db_final",
        user="postgres",
        password="dzireedzireE01@"
    )



user_context = {}

def get_question_type(text):
    if any(w in text for w in ["متى", "الساعة", "موعد", "وقت"]): return "time"
    if any(w in text for w in ["أين", "القاعة", "مكان", "مكانها"]): return "location"
    if any(w in text for w in ["يوم", "تاريخ"]): return "day"
    if any(w in text for w in ["بريد", "email", "إيميل"]): return "email"
    if any(w in text for w in ["مكتب"]): return "office"
    if any(w in text for w in ["قسم"]): return "department"
    if any(w in text for w in ["استشارة"]): return "consultation"
    if any(w in text for w in ["استاذ" , "تدريس" , "معلم", "دكتور" , "من يدرس", "أستاذ", "مدرس"]): return "profe"
    if any(w in text for w in ["وحدة","وحدات","وحده"]): return "credit_hours"
    if any(w in text for w in ["رمزها","رمز","كودها","الكود","رقم","كود"]): return "subject_code"
    return None

def semantic_search(text, records, field_index=0, threshold=0.5):
    if not records:
        return None, -1
    targets = [row[field_index] for row in records]
    embeddings = model.encode(targets, convert_to_tensor=True)
    input_embedding = model.encode(text, convert_to_tensor=True)
    cosine_scores = util.cos_sim(input_embedding, embeddings)[0]
    best_score, best_index = torch.max(cosine_scores, dim=0)
    if best_score >= threshold:
        return records[best_index], best_score.item()
    return None, -1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا بك! اسألني عن المحاضرات، الامتحانات، الأساتذة أو أي سؤال عام.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    raw_msg = update.message.text.strip()
    msg = correct_text(raw_msg)
    lowered = msg.lower()
    q_type = get_question_type(lowered)

    conn = get_connection()
    cur = conn.cursor()


    def save_context(type_, value):
        user_context[user_id] = {"type": type_, "value": value}


    if "وحدات" in lowered or "وحدة" in lowered  or "وحده" in lowered  or "رمزها" in lowered  or "رمز" in lowered  or "كودها" in lowered  or "كود" in lowered :
    # جدول المواد (subjects) - معلومات عن المادة
     cur.execute("SELECT subject_name , subject_code , credit_hours FROM subjects")
     subjects = cur.fetchall()
     match, _ = semantic_search(msg, subjects, field_index=0)
     if match:
        save_context("subject", match[0])
        if q_type == "subject_code":
            await update.message.reply_text(match[1])
        elif q_type == "credit_hours":
            await update.message.reply_text(f"عدد وحدات المادة {match[0]} هو {match[2]}")
        else:
            await update.message.reply_text(match[1])
        return
    
    
 # الامتحانات
    if "امتحان" in lowered or "اختبار" in lowered:
        cur.execute("""SELECT subjects.subject_name, exam_date, exam_time, location FROM exams
JOIN subjects ON exams.subject_code = subjects.subject_code""")
        exams = cur.fetchall()
        match, _ = semantic_search(msg, exams, field_index=0, threshold=0.5)
        if match:
            save_context("exam", match[0])
            if q_type == "time":
                await update.message.reply_text(f"امتحان {match[0]} الساعة {match[2]}")
            elif q_type == "location":
                await update.message.reply_text(f"امتحان {match[0]} في القاعة {match[3]}")
            elif q_type == "day":
                await update.message.reply_text(f"امتحان {match[0]} يوم {match[1]}")
            else:
                await update.message.reply_text(f"امتحان {match[0]} يوم {match[1]} الساعة {match[2]} في {match[3]}")
       
            return


    if user_id in user_context:
        ctx = user_context[user_id]
        if ctx["type"] == "exam":
            cur.execute("""SELECT subjects.subject_name, exam_date, exam_time, location FROM exams
JOIN subjects ON exams.subject_code = subjects.subject_code
WHERE subjects.subject_name = %s""", (ctx["value"],))
            row = cur.fetchone()
            if row:
                if q_type == "time":
                    await update.message.reply_text(f"امتحان {row[0]} الساعة {row[2]}")
                    return
                elif q_type == "location":
                    await update.message.reply_text(f"امتحان {row[0]} في القاعة {row[3]}")
                    return
                elif q_type == "day":
                    await update.message.reply_text(f"امتحان {row[0]} يوم {row[1]}")
                    return
        

    # المحاضرات
    cur.execute("""SELECT subjects.subject_name, day, time, room, professors.name FROM lectures
JOIN subjects ON lectures.subject_code = subjects.subject_code
LEFT JOIN professors ON lectures.professor_id = professors.id""")
    lectures = cur.fetchall()
    match, score = semantic_search(msg, lectures, field_index=0, threshold=0.5)

    if match and match[0] not in msg:
        match = None

    if match:
        save_context("lecture", match[0])
        if q_type == "time":
            await update.message.reply_text(f"محاضرة {match[0]} الساعة {match[2]}")
        elif q_type == "location":
            await update.message.reply_text(f"محاضرة {match[0]} في القاعة {match[3]}")
        elif q_type == "day":
            await update.message.reply_text(f"محاضرة {match[0]} يوم {match[1]}")
        elif q_type == "profe":
            await update.message.reply_text(f"أ. {match[4]} هو أستاذ مادة {match[0]}")
        else:
            await update.message.reply_text(f"محاضرة {match[0]} يوم {match[1]} الساعة {match[2]} في القاعة {match[3]}، ويُدرسها أ. {match[4]}")

        return

    if user_id in user_context:
        ctx = user_context[user_id]
        if ctx["type"] == "lecture":
            cur.execute("""SELECT subjects.subject_name, day, time, room, professors.name FROM lectures
JOIN subjects ON lectures.subject_code = subjects.subject_code
LEFT JOIN professors ON lectures.professor_id = professors.id
WHERE subjects.subject_name = %s""", (ctx["value"],))
            row = cur.fetchone()
            if row:
                if q_type == "time":
                    await update.message.reply_text(f"محاضرة {row[0]} الساعة {row[2]}")
                    return
                elif q_type == "location":
                    await update.message.reply_text(f"محاضرة {row[0]} في القاعة {row[3]}")
                    return
                elif q_type == "day":
                    await update.message.reply_text(f"محاضرة {row[0]} يوم {row[1]}")
                    return
                elif q_type == "profe":
                    await update.message.reply_text(f"أ. {row[4]} هو أستاذ مادة {row[0]}")
                    return

   


    # الأساتذة (مطابقة دقيقة أولًا)
    found = False
    for keyword in ["الدكتور","المدرس" ,"الاستاذ", "أ.", "د.", "أستاذ", "أ."]:
        lowered = lowered.replace(keyword, "")
    cur.execute("SELECT name, department, email, office, consultation FROM professors")
    profs = cur.fetchall()
    for prof in profs:
        if prof[0] and prof[0].split()[-1] in msg:
            match = prof
            found = True
            break

    if not found:
        match, _ = semantic_search(msg, profs, field_index=0, threshold=0.5)

    if match:
        save_context("professor", match[0])
        user_context.pop(user_id, None)
        if q_type == "email":
            await update.message.reply_text(f"بريد {match[0]}: {match[2]}")
        elif q_type == "office":
            await update.message.reply_text(f"مكتب {match[0]}: {match[3]}")
        elif q_type == "department":
            await update.message.reply_text(f"{match[0]} يتبع قسم {match[1]}")
        elif q_type == "consultation":
            await update.message.reply_text(f"أوقات استشارة {match[0]}: {match[4]}")

        return
    




    # في حال لم يجد أستاذ في lectures، fallback إلى professor_subjects
    cur.execute("""
        SELECT s.subject_name, p.name
        FROM professor_subjects ps
        JOIN professors p ON ps.professor_id = p.id
        JOIN subjects s ON ps.subject_code = s.subject_code
    """)
    fallback_professors = cur.fetchall()
    match, _ = semantic_search(msg, fallback_professors, field_index=0)
    if q_type == "profe":
        await update.message.reply_text(f"{match[1]} هو أستاذ مادة {match[0]}")
        return
    
    
         # FAQ
    cur.execute("SELECT question, answer FROM faq")
    faqs = cur.fetchall()
    match, _ = semantic_search(msg, faqs, field_index=0, threshold=0.5)
    if match:
        save_context("faq", match[0])
        await update.message.reply_text(match[1])
        return
    

    await update.message.reply_text("مممم، ما لقيتش إجابة واضحة. ممكن تعيد صياغة سؤالك؟ أو توضح المقصود أكثر؟")
    cur.close()
    conn.close()


user_registering_courses = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا بك! ارسل /تسجيل_المواد لتسجيل المواد التي درستها هذا الفصل.")

async def start_course_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_registering_courses[user_id] = True
    await update.message.reply_text("يرجى إدخال أسماء المواد التي تريد تسجيلها (مفصولة بفواصل).")

async def handle_user(message: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(message.effective_user.id)
    user_input = message.message.text.strip().lower()

    if user_registering_courses.get(user_id):
        user_registering_courses[user_id] = False
        conn = get_connection()
        cur = conn.cursor()

        # جلب المواد الموجودة
        cur.execute("SELECT LOWER(subject_name), subject_code FROM subjects")
        existing_subjects = {row[0]: row[1] for row in cur.fetchall()}

        entered = [c.strip() for c in re.split(r",|،", user_input) if re.search(r"[\u0621-\u064Aa-zA-Z]", c)]
        added = []
        already_registered = []
        ignored = []

        for course in entered:
            course_lower = course.lower()
            if course_lower in existing_subjects:
                subject_code = existing_subjects[course_lower]
                cur.execute("SELECT 1 FROM user_courses WHERE user_id = %s AND subject_code = %s", (user_id, subject_code))
                exists = cur.fetchone()
                if exists:
                    already_registered.append(course)
                else:
                    cur.execute("INSERT INTO user_courses (user_id, subject_code) VALUES (%s, %s)", (user_id, subject_code))
                    added.append(course)
            else:
                ignored.append(course)

        conn.commit()
        cur.close()
        conn.close()

        if added:
            await message.message.reply_text("✅ تم تسجيل المواد بنجاح:\n" + "\n".join(added))
        if already_registered:
            await message.message.reply_text("⚠️ المواد التالية مسجلة بالفعل:\n" + "\n".join(already_registered))
        if ignored:
            await message.message.reply_text("❗️ المواد التالية غير موجودة:\n" + "\n".join(ignored))
        if not (added or already_registered or ignored):
            await message.message.reply_text("❗️ لم يتم العثور على مواد صحيحة للتسجيل.")

        return

    await handle_message(message, context)  # يرجع للبوت العادي

      



async def show_my_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.subject_name, l.day, l.time, l.room
        FROM user_courses uc
        JOIN lectures l ON uc.subject_code = l.subject_code
        JOIN subjects s ON l.subject_code = s.subject_code
        WHERE uc.user_id = %s
    """, (str(user_id),))
    lectures = cur.fetchall()
    cur.close()
    conn.close()

    if lectures:
        response = "📝 محاضراتك:"
        for lecture in lectures:
            response += f"\nمادة {lecture[0]}: يوم {lecture[1]} الساعة {lecture[2]} في القاعة {lecture[3]}\n"
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("❌ لم يتم العثور على محاضرات مسجلة.")

async def show_my_exams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.subject_name, e.exam_date, e.exam_time, e.location
        FROM user_courses uc
        JOIN exams e ON uc.subject_code = e.subject_code
        JOIN subjects s ON e.subject_code = s.subject_code
        WHERE uc.user_id = %s
    """, (str(user_id),))
    exams = cur.fetchall()
    cur.close()
    conn.close()

    if exams:
        response = "📝 امتحاناتك:"
        for exam in exams:
            response += f"\nمادة {exam[0]}: يوم {exam[1]} الساعة {exam[2]} في {exam[3]}\n"
        await update.message.reply_text(response)
    else:  
        await update.message.reply_text("❌ لم يتم العثور على امتحانات مسجلة.")



from telegram.ext import CommandHandler

# عرض المواد المسجلة للمستخدم
async def my_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT s.subject_name FROM user_courses uc JOIN subjects s ON uc.subject_code = s.subject_code WHERE uc.user_id = %s", (user_id,))
    rows = cur.fetchall()
    if rows:
        msg = "المواد المسجلة لديك:" + "\n".join([row[0] for row in rows])
    else:
        msg = "لم تقم بتسجيل أي مواد بعد."
    await update.message.reply_text(msg)
    cur.close()
    conn.close()

# عرض جدول المحاضرات
async def show_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.subject_name, l.day, l.time, l.room, p.name
        FROM lectures l
        JOIN subjects s ON l.subject_code = s.subject_code
        LEFT JOIN professors p ON l.professor_id = p.id
        ORDER BY l.day, l.time
    """)
    rows = cur.fetchall()
    if rows:
        response = "جدول المحاضرات الكامل:\n"
        for row in rows:
            response += f"{row[0]} - {row[1]} - {row[2]} - {row[3]} - {row[4]}\n"
    else:
        response = "لا توجد محاضرات حالياً."
    await update.message.reply_text(response)
    cur.close()
    conn.close()

# عرض جدول الامتحانات
async def show_exams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.subject_name, e.exam_date, e.exam_time, e.location
        FROM exams e
        JOIN subjects s ON e.subject_code = s.subject_code
        ORDER BY e.exam_date, e.exam_time
    """)
    rows = cur.fetchall()
    if rows:
        response = "جدول الامتحانات الكامل:\n"
        for row in rows:
            response += f"{row[0]} - {row[1]} - {row[2]} - {row[3]}\n"
    else:
        response = "لا توجد امتحانات حالياً."
    await update.message.reply_text(response)
    cur.close()
    conn.close()

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("register", start_course_registration))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("البوت يعمل الآن...")
    
    app.add_handler(CommandHandler("l", show_my_lectures))
    app.add_handler(CommandHandler("e", show_my_exams))
    
    app.add_handler(CommandHandler("in", my_info))
    app.add_handler(CommandHandler("viewl", show_lectures))
    app.add_handler(CommandHandler("viewe", show_exams))

    app.run_polling()
    

if __name__ == "__main__":
    main()



@app.route(f"/webhook/{config.TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

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
    bot.set_webhook(url=f"{config.BASE_URL}/webhook/{config.TOKEN}")
    app.run(host="0.0.0.0", port=10000)
