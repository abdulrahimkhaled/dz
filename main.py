
from flask import Flask, request, render_template, redirect, url_for, session, flash
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
import config
import psycopg2
import spacy
from sentence_transformers import SentenceTransformer, util
import torch
import re
from spell_correction_module import correct_text

app = Flask(__name__)
app.secret_key = "your-secret-key"

bot = Bot(token=config.TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

# NLP Models
nlp = spacy.load("xx_ent_wiki_sm")
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

user_context = {}
user_registering_courses = {}

def get_connection():
    return psycopg2.connect(config.DB_URI)

def get_question_type(text):
    if any(w in text for w in ["متى", "الساعة", "موعد", "وقت"]): return "time"
    if any(w in text for w in ["أين", "القاعة", "مكان", "مكانها"]): return "location"
    if any(w in text for w in ["يوم", "تاريخ"]): return "day"
    if any(w in text for w in ["بريد", "email", "إيميل"]): return "email"
    if any(w in text for w in ["مكتب"]): return "office"
    if any(w in text for w in ["قسم"]): return "department"
    if any(w in text for w in ["استشارة"]): return "consultation"
    if any(w in text for w in ["استاذ", "تدريس", "معلم", "دكتور", "من يدرس", "أستاذ", "مدرس"]): return "profe"
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

async def start(update: Update, context):
    await update.message.reply_text("مرحبًا بك! اسألني عن المحاضرات، الامتحانات، الأساتذة أو أي سؤال عام.")

async def start_course_registration(update: Update, context):
    user_id = str(update.effective_user.id)
    user_registering_courses[user_id] = True
    await update.message.reply_text("يرجى إدخال أسماء المواد التي تريد تسجيلها (مفصولة بفواصل).")

async def handle_user(update: Update, context):
    await update.message.reply_text("✅ تم استلام رسالتك، وسيتم معالجتها.")  # Placeholder
    await handle_message(update, context)

async def handle_message(update: Update, context):
    await update.message.reply_text("🤖 جاري تحليل رسالتك وإعطائك الرد المناسب...")  # Placeholder

# Telegram Commands registration
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("register", start_course_registration))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook endpoint
@app.route(f"/webhook/{config.TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "✅ البوت واللوحة يعملان معًا!"

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

if __name__ == "__main__":
    bot.set_webhook(url=f"{config.BASE_URL}/webhook/{config.TOKEN}")
    app.run(host="0.0.0.0", port=10000)
