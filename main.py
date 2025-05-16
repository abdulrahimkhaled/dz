
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import config
import psycopg2

app = Flask(__name__)
bot = Bot(token=config.TOKEN)
dispatcher = Dispatcher(bot, update_queue=None, use_context=True)

def start(update, context):
    update.message.reply_text("مرحبًا! البوت يعمل بنجاح على Render 🌐")

dispatcher.add_handler(CommandHandler("start", start))

@app.route("/")
def index():
    return "البوت يعمل ✅"

@app.route(f"/webhook/{config.TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

if __name__ == "__main__":
    bot.set_webhook(url=f"{config.BASE_URL}/webhook/{config.TOKEN}")
    app.run(host="0.0.0.0", port=10000)
