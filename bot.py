
import os
import re
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.helpers import escape_markdown
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
REDEMPTION_LOG_CHANNEL = "@capxpremium"  # Log redemptions here
IMAGE_PATH = "/mnt/data/file-ELmLXV23qaHUztbxNNjMya"  # Redemption image

# Channel join check (replace with actual channel ID for private one)
REQUIRED_CHANNELS = [
    "@earnxcaptain",
    "@capxpremium",
    "-1002120123969",
    "westbengalnetwork2"# Use your bot's actual private channel ID
]

# SQLite setup
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    points INTEGER DEFAULT 0,
    referred_by INTEGER,
    gmail TEXT
)''')
conn.commit()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "N/A"
    referred_by = int(context.args[0]) if context.args and context.args[0].isdigit() else None

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, points, referred_by) VALUES (?, ?, 0, ?)",
                       (user_id, username, referred_by))
        conn.commit()
        if referred_by:
            cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (referred_by,))
            conn.commit()
    await update.message.reply_text("✅ Welcome! Use /points to check your balance or /redeem to redeem points.")

# /points command
async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        await update.message.reply_text(f"💰 You have {row[0]} points.")
    else:
        await update.message.reply_text("❌ You are not registered. Use /start to begin.")

# /redeem command
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "N/A"

    # Require Gmail argument
    if not context.args:
        return await update.message.reply_text("❗ Usage: /redeem your_gmail@gmail.com")
    gmail = context.args[0]

    # Validate Gmail
    if not re.fullmatch(r"[a-zA-Z0-9_.+-]+@gmail\.com", gmail):
        return await update.message.reply_text("❌ Invalid Gmail. Please use a valid @gmail.com address.")

    # Check channel membership
    for ch in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return await update.message.reply_text("❗ You must join all required channels before redeeming.")
        except Exception as e:
            return await update.message.reply_text(f"❗ Error checking channel {ch}. Please make sure you're joined.")

    # Check points
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or row[0] < 5:
        return await update.message.reply_text("⚠️ You need at least 5 points to redeem.")

    # Deduct points and store Gmail
    new_points = row[0] - 5
    cursor.execute("UPDATE users SET points = ?, gmail = ? WHERE user_id = ?", (new_points, gmail, user_id))
    conn.commit()

    await update.message.reply_text(f"✅ Redemption successful for {gmail}. Points left: {new_points}")

    # Post to log channel with image
    with open(IMAGE_PATH, "rb") as img:
        await context.bot.send_photo(
            chat_id=REDEMPTION_LOG_CHANNEL,
            photo=img,
            caption=(
                f"🎉 *New Redemption!*\n\n"
                f"User: [{escape_markdown(user.first_name)}](tg://user?id={user.id})\n"
                f"Username: @{username}\n"
                f"Gmail: `{gmail}`\n"
                f"Points Left: {new_points}"
            ),
            parse_mode="Markdown"
        )

# Main entry
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("redeem", redeem))
    print("Bot is running...")
    app.run_polling()
