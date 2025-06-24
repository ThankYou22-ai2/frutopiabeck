import os
import json
import threading
import sqlite3
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from flask_cors import CORS

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN", "7861578831:AAGz893TBI6dVi09qAgx6hn3ZjZJ0WOzS3c")  # DON'T hard-code in prod
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://aquamarine-semifreddo-d23b16.netlify.app/index.html")  # URL где размещён index.html (https!)
DB_PATH = os.getenv("DB_PATH", "progress.db")

# =============== DATABASE ===============
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS progress (
    user_id INTEGER PRIMARY KEY,
    data TEXT
)""")
conn.commit()

def get_progress(uid: int):
    row = cur.execute("SELECT data FROM progress WHERE user_id=?", (uid,)).fetchone()
    return json.loads(row[0]) if row else None

def save_progress(uid: int, data: dict):
    cur.execute("INSERT OR REPLACE INTO progress(user_id,data) VALUES (?,?)", (uid, json.dumps(data)))
    conn.commit()

# =============== FLASK ===============
app = Flask(__name__)
CORS(app,
     origins=["https://aquamarine-semifreddo-d23b16.netlify.app"],
     methods=["GET", "POST", "OPTIONS"],
     allow_headers="*")

@app.get("/api/progress/<int:uid>")
def api_get(uid):
    return jsonify(get_progress(uid))

@app.post("/api/progress/<int:uid>")
def api_post(uid):
    save_progress(uid, request.json)
    return "ok"

@app.get("/")
def root():
    return "Frutopia backend running"

@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"] = "https://aquamarine-semifreddo-d23b16.netlify.app"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

# =============== TELEGRAM BOT ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(text="Play", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text("🍒 Frutopia", reply_markup=InlineKeyboardMarkup(kb))

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = json.loads(update.message.web_app_data.data)
    save_progress(user_id, data)
    await update.message.reply_text("✔️ Progress saved!")

def run_api():
    # Flask API server
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

def main():
    # запускаем Flask в отдельном потоке
    threading.Thread(target=run_api, daemon=True).start()

    # запускаем Telegram-бот в главном потоке (чтобы работали сигнал-хендлеры)
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))

    # stop_signals по умолчанию (SIGINT/SIGTERM) работают только в main thread ‑ нам и нужно
    application.run_polling(drop_pending_updates=True)

# =============== ENTRY ===============
if __name__ == "__main__":
    main() 