
from flask import Flask, request, render_template, redirect, url_for, session, flash
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
import config
import psycopg2
import asyncio

# إعداد Flask
app = Flask(__name__)
app.secret_key = "your-secret-key"

# إعداد البوت
bot = Bot(token=config.TOKEN)
dispatcher = Dispatcher(bot, update_queue=None, use_context=True)

# ----- Telegram Commands -----
def start(update, context):
    update.message.reply_text("مرحبًا بك في البوت الجامعي 👋")

dispatcher.add_handler(CommandHandler("start", start))

# ----- Webhook Endpoint -----
@app.route(f"/webhook/{config.TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "✅ البوت واللوحة يعملان معًا!"

# ----- واجهة تسجيل الدخول -----
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = psycopg2.connect(config.DB_URI)
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

# ----- لوحة التحكم -----
@app.route("/dashboard")
def dashboard():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", admin=session["username"], role=session["role"])

# (💡 لاحقًا: يمكن إضافة بقية الصفحات بنفس الشكل)

# ----- تفعيل Webhook -----
if __name__ == "__main__":
    bot.set_webhook(url=f"{config.BASE_URL}/webhook/{config.TOKEN}")
    app.run(host="0.0.0.0", port=10000)
