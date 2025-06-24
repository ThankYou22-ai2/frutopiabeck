import os
import json
import threading
import sqlite3
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN", "7861578831:AAGz893TBI6dVi09qAgx6hn3ZjZJ0WOzS3c")  # DON'T hard-code in prod
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com")  # URL где размещён index.html (https!)
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

# =============== TELEGRAM BOT ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(text="Play", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text("🍒 Frutopia", reply_markup=InlineKeyboardMarkup(kb))

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = json.loads(update.message.web_app_data.data)
    save_progress(user_id, data)
    await update.message.reply_text("✔️ Progress saved!")


def run_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    application.run_polling()

# =============== ENTRY ===============
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000))) 