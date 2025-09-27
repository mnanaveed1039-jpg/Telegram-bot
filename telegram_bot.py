import os
import sqlite3
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# 🔹 Railway / Hosting Environment Variables
BOT_TOKEN  = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
ADMIN_ID   = int(os.environ.get("ADMIN_ID"))

# 🔹 Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Database (SQLite)
conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    invited_by INTEGER
)
""")
conn.commit()

# ---------------- Functions ---------------- #

def get_balance(uid): 
    cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()
    return row[0] if row else 0

def add_balance(uid, username, amount):
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 0)", (uid, username))
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()

# ---------------- Commands ---------------- #

def start(update: Update, ctx: CallbackContext):
    user = update.effective_user
    args = ctx.args  

    # Save user if not exists
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 0)", (user.id, user.username or ""))
    conn.commit()

    # Referral check
    if args:
        try:
            inviter_id = int(args[0])
            if inviter_id != user.id:  # self-invite nahi
                # Check agar pehle se invited_by nahi set
                cur.execute("SELECT invited_by FROM users WHERE user_id=?", (user.id,))
                invited_by = cur.fetchone()[0]
                if invited_by is None:
                    cur.execute("UPDATE users SET invited_by=? WHERE user_id=?", (inviter_id, user.id))
                    conn.commit()
                    add_balance(inviter_id, "", 1.0)  # Reward 1 USDT
                    ctx.bot.send_message(
                        inviter_id,
                        f"🎉 New referral joined!\n"
                        f"💵 You got +1.00 USDT\n"
                        f"Current Balance: {get_balance(inviter_id):.2f} USDT"
                    )
        except:
            pass

    bal = get_balance(user.id)
    update.message.reply_text(
        f"👋 Hi {user.first_name}!\n"
        f"💵 Balance: {bal:.2f} USDT\n"
        "Use /verify to claim reward after joining the channel.\n\n"
        "Invite friends with /invite to earn 1 USDT each!"
    )

def invite(update: Update, ctx: CallbackContext):
    user = update.effective_user
    link = f"https://t.me/{ctx.bot.username}?start={user.id}"
    update.message.reply_text(
        f"👥 Invite Friends & Earn 1 USDT each!\n"
        f"Your Referral Link:\n{link}"
    )

def verify(update: Update, ctx: CallbackContext):
    user = update.effective_user
    try:
        member = ctx.bot.get_chat_member(CHANNEL_ID, user.id)
    except:
        update.message.reply_text("❌ Bot ko channel admin banao taake verify kar sake.")
        return
    
    if member.status in ("member", "administrator", "creator"):
        add_balance(user.id, user.username or "", 0.10)
        update.message.reply_text(
            f"✅ 0.10 USDT added!\n"
            f"💵 Balance: {get_balance(user.id):.2f} USDT"
        )
    else:
        update.message.reply_text("❌ Pehle channel join karo!")

def balance(update: Update, ctx: CallbackContext):
    update.message.reply_text(f"💵 Balance: {get_balance(update.effective_user.id):.2f} USDT")

def withdraw(update: Update, ctx: CallbackContext):
    user = update.effective_user
    bal = get_balance(user.id)
    if bal < 10:
        update.message.reply_text(f"❌ Minimum 10 USDT chahiye. Tumhara balance {bal:.2f} USDT")
    else:
        update.message.reply_text("✅ Withdrawal request admin ko bhej di gayi.")
        ctx.bot.send_message(
            ADMIN_ID,
            f"📢 Withdrawal Request!\n"
            f"👤 User: @{user.username}\n"
            f"🆔 ID: {user.id}\n"
            f"💵 Balance: {bal:.2f} USDT"
        )

# ---------------- Main ---------------- #

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("invite", invite))
    dp.add_handler(CommandHandler("verify", verify))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CommandHandler("withdraw", withdraw))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
