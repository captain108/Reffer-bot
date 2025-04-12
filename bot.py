import logging
import random
from datetime import datetime, timedelta

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)

# === CONFIGURATION ===
TOKEN = "8037210105:AAFbBznD3Mf1rGgGZdrlYoYXAEijr8JEuSg"
REQUIRED_CHANNELS = ["@ultracashonline", "@westbengalnetwork2"]
ADMIN_ID = 5944513375

# === LOGGING SETUP ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DATABASE ===
users_data = {}
WAITING_FOR_GMAIL = range(1)

# === MENUS ===
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Check Balance", callback_data="balance"),
         InlineKeyboardButton("🔗 Referral Info", callback_data="referral_info")],
        [InlineKeyboardButton("🎁 Redeem", callback_data="redeem"),
         InlineKeyboardButton("✅ Daily Bonus", callback_data="daily_bonus")],
        [InlineKeyboardButton("📘 How to Earn?", callback_data="how_to_earn")]
    ])

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]
    ])

# === CHANNEL CHECK ===
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

# === START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    if user_id not in users_data:
        users_data[user_id] = {"points": 0, "referrals": set(), "last_bonus": None}
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📢 *New User Started!*\n\n"
                f"Name: [{user.first_name}](tg://user?id={user_id})\n"
                f"ID: `{user_id}`\n"
                f"Username: @{user.username or 'N/A'}"
            ),
            parse_mode="Markdown"
        )

    referrer_name = None
    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user_id and user_id not in users_data.get(referrer_id, {}).get("referrals", set()):
                users_data.setdefault(referrer_id, {"points": 0, "referrals": set(), "last_bonus": None})
                users_data[referrer_id]["points"] += 3
                users_data[referrer_id]["referrals"].add(user_id)
                ref_user = await context.bot.get_chat(referrer_id)
                referrer_name = f"[{ref_user.first_name}](tg://user?id={referrer_id})"
        except:
            pass

    owner_chat = await context.bot.get_chat(ADMIN_ID)
    owner_mention = f"[{owner_chat.first_name}](tg://user?id={ADMIN_ID})"

    missing = await get_missing_channels(user_id, context)
    if missing:
        join_buttons = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch.strip('@')}")]
                        for ch in missing]
        join_buttons.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_join")])
        await update.message.reply_text(
            "📢 To use the bot, please join *all* required channels:",
            reply_markup=InlineKeyboardMarkup(join_buttons),
            parse_mode="Markdown"
        )
        return

    welcome = (
        f"👋 *Welcome, {user.first_name}!* \n\n"
        "🎉 You're now part of the *Refer & Earn* program.\n"
        "💸 Invite friends, earn rewards, and enjoy your perks!"
    )
    if referrer_name:
        welcome += f"\n\n🙌 You were invited by {referrer_name} — show them some love!"
    welcome += f"\n\n🛠️ For help or support, contact {owner_mention}."

    await update.message.reply_text(welcome, reply_markup=main_menu(), parse_mode="Markdown")

# === CALLBACK HANDLER ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    await query.answer()

    if user_id not in users_data:
        users_data[user_id] = {"points": 0, "referrals": set(), "last_bonus": None}
    user_data = users_data[user_id]

    if query.data == "check_join":
        missing = await get_missing_channels(user_id, context)
        if not missing:
            await query.edit_message_text("✅ You've joined all channels!", reply_markup=main_menu())

            # Notify referrer
            for referrer_id, data in users_data.items():
                if user_id in data.get("referrals", set()):
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=(
                            f"🎉 *Your Referral Joined!*\n\n"
                            f"Name: [{user.first_name}](tg://user?id={user_id})\n"
                            f"ID: `{user_id}`\n"
                            f"Username: @{user.username or 'N/A'}\n"
                            "has joined all required channels and started the bot!"
                        ),
                        parse_mode="Markdown"
                    )
                    break
        else:
            join_buttons = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch.strip('@')}")]
                            for ch in missing]
            join_buttons.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_join")])
            await query.edit_message_text(
                "❗ You're not in all required channels. Please join them:",
                reply_markup=InlineKeyboardMarkup(join_buttons),
                parse_mode="Markdown"
            )
        return

    if query.data == "menu":
        await query.edit_message_text("🏠 *Main Menu*", reply_markup=main_menu(), parse_mode="Markdown")

    elif query.data == "balance":
        await query.edit_message_text(
            f"💰 *Your Balance:*\n`{user_data['points']} points`",
            reply_markup=back_button(), parse_mode="Markdown"
        )

    elif query.data == "referral_info":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        referrals = user_data["referrals"]
        count = len(referrals)

        if referrals:
            referral_text = ""
            for ref_id in referrals:
                try:
                    ref_user = await context.bot.get_chat(ref_id)
                    referral_text += f"• [{ref_user.first_name}](tg://user?id={ref_id})\n"
                except:
                    referral_text += f"• User ID: `{ref_id}`\n"
        else:
            referral_text = "No referrals yet."

        await query.edit_message_text(
            f"🔗 *Your Referral Link:*\n`{link}`\n\n"
            f"👥 *Total Referrals:* `{count}`\n\n"
            f"📄 *Referral Users:*\n{referral_text}\n"
            "_Share your link to earn 3 points per referral!_",
            reply_markup=back_button(), parse_mode="Markdown"
        )

    elif query.data == "redeem":
        if user_data["points"] >= 30:
            await query.edit_message_text(
                "🎁 *Redeem Request Initiated!*\n\nPlease send your *Gmail address* to continue.",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
            return WAITING_FOR_GMAIL
        else:
            await query.edit_message_text(
                f"⚠️ *Not enough points!*\nYou need 30 points to redeem.\n"
                f"Your balance: `{user_data['points']} points`",
                reply_markup=back_button(), parse_mode="Markdown"
            )

    elif query.data == "daily_bonus":
        now = datetime.utcnow()
        last = user_data.get("last_bonus")
        if not last or now - last >= timedelta(days=1):
            dice_msg = await context.bot.send_dice(chat_id=user_id, emoji="🎲")
            rolled = dice_msg.dice.value
            user_data["points"] += rolled
            user_data["last_bonus"] = now
            await query.message.delete()
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 *Bonus Claimed!*\nYou rolled a *{rolled}* and earned *+{rolled} points*!",
                reply_markup=back_button(),
                parse_mode="Markdown"
            )
        else:
            next_time = last + timedelta(days=1)
            hours_left = int((next_time - now).total_seconds() // 3600)
            await query.edit_message_text(
                f"⏳ *Bonus Already Claimed!*\nNext bonus in *{hours_left} hours*.",
                reply_markup=back_button(), parse_mode="Markdown"
            )

    elif query.data == "how_to_earn":
        await query.edit_message_text(
            "📘 *How to Earn Points:*\n\n"
            "• Refer friends — *+3 points each*\n"
            "• Claim daily bonus — *+1 to 6 points every 24h*\n"
            "• Redeem with *30 points*",
            reply_markup=back_button(), parse_mode="Markdown"
        )

# === HANDLE GMAIL ===
async def handle_gmail_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    gmail = update.message.text.strip()
    user_data = users_data[user_id]
    user_data["points"] -= 30

    await update.message.reply_text(
        f"✅ *Gmail Received!* We got: `{gmail}`\nOur team will contact you soon.",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"📬 *New Redemption Request*\n\n"
            f"User: [{user.first_name}](tg://user?id={user_id})\n"
            f"Gmail: `{gmail}`\n"
            f"Remaining Points: `{user_data['points']}`"
        ),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# === CANCEL ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Redeem cancelled.", reply_markup=main_menu())
    return ConversationHandler.END

# === MAIN ===
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    redeem_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^redeem$")],
        states={WAITING_FOR_GMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gmail_input)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(redeem_handler)
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
