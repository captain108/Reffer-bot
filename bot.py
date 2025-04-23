import asyncio
from aiohttp import web
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)
from dotenv import load_dotenv

# === CONFIGURATION ===
load_dotenv()
TOKEN = os.getenv("7836593462:AAGwMG4vTpOWE6DVapZaRKTUml6D5iSgkhc")
REQUIRED_CHANNELS = ["@ultracashonline", "@westbengalnetwork2"]
PRIVATE_CHANNELS = ["@privateexamplechannel"]
ADMINS = [5944513375, 1808053774]  # Replace with actual admin IDs
FOLDER_LINK = "https://t.me/addlist/RlzqLqKxFOk2NGVl"
REDEMPTION_CHANNEL = "@earnxcaptain"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DATABASE ===
conn = sqlite3.connect("referral_bot.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    referred_by INTEGER,
    last_bonus TEXT,
    verified INTEGER DEFAULT 0
)""")
c.execute("""CREATE TABLE IF NOT EXISTS referrals (
    referrer_id INTEGER,
    referred_id INTEGER,
    PRIMARY KEY (referrer_id, referred_id)
)""")
conn.commit()

WAITING_FOR_CODE = range(1)

# === UI ===
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Check Balance", callback_data="balance"),
         InlineKeyboardButton("🔗 Referral Info", callback_data="referral_info")],
        [InlineKeyboardButton("🎁 Redeem Code", callback_data="redeem")],
        [InlineKeyboardButton("📘 How to Earn?", callback_data="how_to_earn")]
    ])

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]
    ])

# === UTILS ===
def get_user(user_id):
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return c.fetchone()

def update_verification(user_id, status):
    c.execute("UPDATE users SET verified = ? WHERE user_id = ?", (status, user_id))
    conn.commit()

# === CHANNEL VERIFICATION ===
async def get_missing_channels(user_id, context):
    missing = []
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                missing.append(channel)
        except:
            missing.append(channel)
    return missing

async def verify_membership(user_id, context):
    missing = await get_missing_channels(user_id, context)
    if not missing:
        update_verification(user_id, 1)
    else:
        update_verification(user_id, 0)
    return missing

# === START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    if not get_user(user_id):
        c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        for admin in ADMINS:
            await context.bot.send_message(
                chat_id=admin,
                text=f"📢 *New User Joined!*\nName: [{user.first_name}](tg://user?id={user_id})\nID: `{user_id}`\nUsername: @{user.username or 'N/A'}",
                parse_mode="Markdown"
            )

    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user_id:
                c.execute("SELECT 1 FROM referrals WHERE referrer_id = ? AND referred_id = ?", (referrer_id, user_id))
                if not c.fetchone():
                    c.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
                    c.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
                    c.execute("UPDATE users SET points = points + 3 WHERE user_id = ?", (referrer_id,))
                    conn.commit()
                    ref_user = await context.bot.get_chat(referrer_id)
                    await context.bot.send_message(referrer_id, f"🎉 Your referral [{user.first_name}](tg://user?id={user_id}) joined using your link!", parse_mode="Markdown")
                    for admin in ADMINS:
                        await context.bot.send_message(admin, f"✅ [{user.first_name}](tg://user?id={user_id}) joined via [{ref_user.first_name}](tg://user?id={referrer_id})", parse_mode="Markdown")
        except:
            pass

    missing = await verify_membership(user_id, context)
    if missing:
        join_buttons = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch.strip('@')}")] for ch in missing]
        join_buttons.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_join")])
        await update.message.reply_text(
            f"📢 Please join *all* required channels to use the bot:\n\n{FOLDER_LINK}",
            reply_markup=InlineKeyboardMarkup(join_buttons),
            parse_mode="Markdown"
        )
        return

    welcome = (
        f"👋 *Welcome, {user.first_name}!* You're now part of the *Refer & Earn* program.\n"
        f"💸 Refer friends and redeem rewards.\n\n"
        f"📂 Folder link: {FOLDER_LINK}\n"
        f"🛠️ For help, contact [Admin](tg://user?id={ADMINS[0]})"
    )
    await update.message.reply_text(welcome, reply_markup=main_menu(), parse_mode="Markdown")

# === CALLBACKS ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    await query.answer()

    user_data = get_user(user_id)
    if not user_data:
        return await query.edit_message_text("⚠️ Start the bot first using /start.")

    if query.data == "check_join":
        missing = await verify_membership(user_id, context)
        if not missing:
            await query.edit_message_text("✅ You're verified!", reply_markup=main_menu())
        else:
            join_buttons = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch.strip('@')}")] for ch in missing]
            join_buttons.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_join")])
            await query.edit_message_text("❗ You're still missing some channels:", reply_markup=InlineKeyboardMarkup(join_buttons), parse_mode="Markdown")

    elif query.data == "menu":
        await query.edit_message_text("🏠 *Main Menu*", reply_markup=main_menu(), parse_mode="Markdown")

    elif query.data == "balance":
        await query.edit_message_text(f"💰 Your Balance: `{user_data[1]} points`", reply_markup=back_button(), parse_mode="Markdown")

    elif query.data == "referral_info":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        c.execute("SELECT referred_id FROM referrals WHERE referrer_id = ?", (user_id,))
        referrals = c.fetchall()
        referral_list = "\n".join([f"• [{(await context.bot.get_chat(uid)).first_name}](tg://user?id={uid})" for (uid,) in referrals]) if referrals else "No referrals yet."
        await query.edit_message_text(
            f"🔗 Your Referral Link:\n`{link}`\n\n"
            f"👥 Total Referrals: `{len(referrals)}`\n\n"
            f"{referral_list}",
            reply_markup=back_button(), parse_mode="Markdown"
        )

    elif query.data == "redeem":
        if user_data[1] >= 30:
            await query.edit_message_text("🎁 *Please send your code to redeem*", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
            return WAITING_FOR_CODE
        else:
            await query.edit_message_text(f"⚠️ Not enough points. You need 30, but you have `{user_data[1]}`.", reply_markup=back_button(), parse_mode="Markdown")

    elif query.data == "how_to_earn":
        await query.edit_message_text("📘 *Earn Points By:*\n• Referring friends: +3 points\n• Redeem at 30 points", reply_markup=back_button(), parse_mode="Markdown")

# === REDEEM CODE ===
async def handle_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    code = update.message.text.strip()

    c.execute("UPDATE users SET points = points - 30 WHERE user_id = ?", (user_id,))
    conn.commit()

    await update.message.reply_text(f"✅ *Code received:* `{code}`\nOur team will verify it soon.\nFor support, contact [Admin](tg://user?id={ADMINS[0]}).", parse_mode="Markdown", reply_markup=main_menu())

    trophy_img = InputFile("trophy.jpg")
    caption = f"🏆 *Redemption Request*\n\nUser: [{user.first_name}](tg://user?id={user_id})\nCode: `{code}`\nPoints Left: `{get_user(user_id)[1]}`"
    await context.bot.send_photo(chat_id=REDEMPTION_CHANNEL, photo=trophy_img, caption=caption, parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Redemption cancelled.", reply_markup=main_menu())
    return ConversationHandler.END

# === WEB SERVER (OPTIONAL) ===
async def handle(request):
    return web.Response(text="Bot running")

async def run_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

async def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    redeem_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^redeem$")],
        states={WAITING_FOR_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code_input)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(redeem_handler)
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot is running...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

async def main_all():
    await asyncio.gather(run_webserver(), run_bot())

if __name__ == "__main__":
    asyncio.run(main_all())
