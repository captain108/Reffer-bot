import logging
import random
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

# === CONFIGURATION ===
TOKEN = "8089419300:AAHVOIMdV_UtdpXZpNjx1GDuZTMUOe3kmRw"  # Replace with your bot token
REQUIRED_CHANNELS = ["@ultracashonline", "@westbengalnetwork2"]  # Replace with your channels
ADMIN_ID = 5944513375  # Replace with your Telegram user ID

# === LOGGING SETUP ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === IN-MEMORY DATABASE ===
users_data = {}

# === INLINE KEYBOARDS ===
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

# === CHECK IF USER JOINED ALL CHANNELS ===
async def has_joined_all_channels(user_id, context):
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False
    return True

# === /START COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    if user_id not in users_data:
        users_data[user_id] = {"points": 0, "referrals": set(), "last_bonus": None}

    # Referral logic
    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user_id and user_id not in users_data.get(referrer_id, {}).get("referrals", set()):
                users_data.setdefault(referrer_id, {"points": 0, "referrals": set(), "last_bonus": None})
                users_data[referrer_id]["points"] += 3
                users_data[referrer_id]["referrals"].add(user_id)
        except ValueError:
            pass

    # Check channel join
    if not await has_joined_all_channels(user_id, context):
        join_buttons = [[InlineKeyboardButton(f"Join {channel}", url=f"https://t.me/{channel.strip('@')}")]
                        for channel in REQUIRED_CHANNELS]
        join_buttons.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_join")])
        await update.message.reply_text(
            "To use the bot, please join *all* the required channels:",
            reply_markup=InlineKeyboardMarkup(join_buttons),
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"Welcome, {user.first_name}!\n\n"
        "You're now part of the *Refer & Earn* program.\n"
        "Invite friends, earn rewards, and enjoy your perks!",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

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
        if await has_joined_all_channels(user_id, context):
            await query.edit_message_text("✅ You've joined all channels!", reply_markup=main_menu())
        else:
            join_buttons = [[InlineKeyboardButton(f"Join {channel}", url=f"https://t.me/{channel.strip('@')}")]
                            for channel in REQUIRED_CHANNELS]
            join_buttons.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_join")])
            await query.edit_message_text(
                "You're not in all required channels yet. Please join *each one* to continue.",
                reply_markup=InlineKeyboardMarkup(join_buttons),
                parse_mode="Markdown"
            )
        return

    if query.data == "menu":
        await query.edit_message_text("🏠 *Main Menu*", reply_markup=main_menu(), parse_mode="Markdown")

    elif query.data == "balance":
        await query.edit_message_text(
            f"💰 *Your Balance:*\n`{user_data['points']} points`",
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

    elif query.data == "referral_info":
        ref_link = f"https://t.me/{context.bot.username}?start={user_id}"
        refs = len(user_data["referrals"])
        await query.edit_message_text(
            f"🔗 *Your Referral Link:*\n`{ref_link}`\n\n"
            f"👥 *Successful Referrals:* `{refs}`\n\n"
            "_Share this link to earn 3 points per referral!_",
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

    elif query.data == "redeem":
        if user_data["points"] >= 30:
            user_data["points"] -= 30
            await query.edit_message_text(
                "✅ *Redemption Successful!*\n\n"
                "You've used *30 points* to claim a reward.\n"
                "_Our team will contact you soon._",
                reply_markup=back_button(),
                parse_mode="Markdown"
            )

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"📢 *New Redemption!*\n"
                    f"User: @{user.username or user.first_name}\n"
                    f"ID: `{user_id}`\n"
                    f"Remaining Balance: `{user_data['points']} points`"
                ),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"⚠️ *Insufficient Points!*\nYou need *30 points* to redeem.\n"
                f"Your balance: `{user_data['points']} points`",
                reply_markup=back_button(),
                parse_mode="Markdown"
            )

    elif query.data == "daily_bonus":
        now = datetime.utcnow()
        last_bonus = user_data.get("last_bonus")

        if last_bonus is None or now - last_bonus >= timedelta(days=1):
            bonus_points = random.randint(1, 10)
            user_data["points"] += bonus_points
            user_data["last_bonus"] = now

            # Dice animation
            await context.bot.send_dice(chat_id=user_id, emoji="🎲")
            await query.message.delete()

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 *Daily Bonus Claimed!*\n\n"
                    f"You rolled the dice and earned *+{bonus_points} points* today!\n"
                    "Come back tomorrow for more!"
                ),
                reply_markup=back_button(),
                parse_mode="Markdown"
            )
        else:
            next_claim = last_bonus + timedelta(days=1)
            hours_left = int((next_claim - now).total_seconds() // 3600)
            await query.edit_message_text(
                f"⏳ *Bonus Already Claimed!*\nNext bonus in *{hours_left} hours*.",
                reply_markup=back_button(),
                parse_mode="Markdown"
            )

    elif query.data == "how_to_earn":
        await query.edit_message_text(
            "📘 *How to Earn Points:*\n\n"
            "• Refer friends using your referral link — *+3 points* each\n"
            "• Claim your *daily bonus* — *+1 to 10 points* every 24h\n"
            "• Redeem rewards once you have *30 points*\n\n"
            "Start sharing and start earning!",
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

# === RUN BOT ===
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
