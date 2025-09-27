import os
import sqlite3
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

BOT_TOKEN  = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
ADMIN_ID   = int(os.environ.get("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0
)
""")
conn.commit()

def get_balance(uid): 
    cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()
    return row[0] if row else 0

def add_balance(uid, username, amount):
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 0)", (uid, username))
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()

def start(update: Update, ctx: CallbackContext):
    user = update.effective_user
    bal = get_balance(user.id)
    update.message.reply_text(f"👋 Hi {user.first_name}!\nBalance: {bal:.2f} USDT\nUse /verify to claim reward.")

def verify(update: Update, ctx: CallbackContext):
    user = update.effective_user
    try:
        member = ctx.bot.get_chat_member(CHANNEL_ID, user.id)
    except:
        update.message.reply_text("❌ Bot ko channel admin banao.")
        return
    if member.status in ("member","administrator","creator"):
        add_balance(user.id, user.username or "", 0.10)
        update.message.reply_text(f"✅ 0.10 USDT added!\nBalance: {get_balance(user.id):.2f} USDT")
    else:
        update.message.reply_text("❌ Pehle channel join karo!")

def balance(update: Update, ctx: CallbackContext):
    update.message.reply_text(f"💵 Balance: {get_balance(update.effective_user.id):.2f} USDT")

def withdraw(update: Update, ctx: CallbackContext):
    user = update.effective_user
    bal = get_balance(user.id)
    if bal < 10:
        update.message.reply_text(f"❌ Min 10 USDT chahiye. Tumhara balance {bal:.2f} USDT")
    else:
        update.message.reply_text("✅ Withdrawal request admin ko bhej di gayi.")
        ctx.bot.send_message(ADMIN_ID, f"📢 Withdrawal Request!\nUser: @{user.username}\nID: {user.id}\nBalance: {bal:.2f} USDT")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("verify", verify))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CommandHandler("withdraw", withdraw))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()