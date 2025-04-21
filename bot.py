import asyncio
import logging
import random
from datetime import datetime, timedelta

from aiohttp import web
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)

TOKEN = "8124555249:AAF398xj13BSYzAOIQe3fXgDZUURmGbyOYE"
REQUIRED_CHANNELS = [
    "@ultracashonline",
    "@westbengalnetwork2",
    "@ui_zone",
    "https://t.me/+L4ek5JLdYu0zZDg1",
    "https://t.me/+x5WHZ8PJfxE3Yjll",
    "https://t.me/capxpremium",
    "https://t.me/earnxcaptain"
]
ADMIN_ID = 5944513375
users_data = {}
WAITING_FOR_GMAIL = range(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def escape_markdown(text):
    return text.replace("_", "\\_")


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


async def get_missing_channels(user_id, context):
    missing = []
    for channel in REQUIRED_CHANNELS:
        if channel.startswith("https://"):
            continue
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                missing.append(channel)
        except:
            missing.append(channel)
    return missing


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    if user_id not in users_data:
        users_data[user_id] = {"points": 0, "referrals": set(), "last_bonus": None}
        await context.bot.send_message(
            ADMIN_ID,
            f"📢 *New User Started!*\n\nName: [{escape_markdown(user.first_name)}](tg://user?id={user_id})\n"
            f"ID: `{user_id}`\nUsername: @{escape_markdown(user.username or 'N/A')}",
            parse_mode="Markdown"
        )

    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user_id:
                users_data[user_id]["pending_referrer"] = referrer_id
                users_data[user_id]["was_referred"] = True
        except:
            pass

    owner = await context.bot.get_chat(ADMIN_ID)
    missing = await get_missing_channels(user_id, context)
    if missing:
        join_buttons = [[
            InlineKeyboardButton(f"Join @{ch.strip('@')}", url=f"https://t.me/{ch.strip('@')}")
        ] for ch in missing]
        join_buttons.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_join")])
        await update.message.reply_text(
            "📢 To use the bot, please join *all* required public channels:",
            reply_markup=InlineKeyboardMarkup(join_buttons),
            parse_mode="Markdown"
        )
        return

    welcome = f"👋 *Welcome, {escape_markdown(user.first_name)}!* \n\n🎉 You're now part of the *Refer & Earn* program.\n" \
              "💸 Invite friends, earn rewards, and enjoy your perks!\n\n" \
              f"🛠️ For help or support, contact [{escape_markdown(owner.first_name)}](tg://user?id={ADMIN_ID})."
    await update.message.reply_text(welcome, reply_markup=main_menu(), parse_mode="Markdown")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    await query.answer()

    if user_id not in users_data:
        users_data[user_id] = {"points": 0, "referrals": set(), "last_bonus": None}
    user_data = users_data[user_id]

    if query.data != "check_join":
        missing = await get_missing_channels(user_id, context)
        if missing:
            join_buttons = [[
                InlineKeyboardButton(f"Join @{ch.strip('@')}", url=f"https://t.me/{ch.strip('@')}")
            ] for ch in missing]
            join_buttons.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_join")])
            await query.edit_message_text(
                "❗ You must join *all required public channels* to continue.",
                reply_markup=InlineKeyboardMarkup(join_buttons),
                parse_mode="Markdown"
            )
            return

    if query.data == "check_join":
        missing = await get_missing_channels(user_id, context)
        if not missing:
            ref = users_data[user_id].pop("pending_referrer", None)
            if ref and user_id not in users_data.get(ref, {}).get("referrals", set()):
                if not users_data.get(ref, {}).get("was_referred", False):
                    users_data.setdefault(ref, {"points": 0, "referrals": set(), "last_bonus": None})
                    users_data[ref]["points"] += 3
                    users_data[ref]["referrals"].add(user_id)
                    await context.bot.send_message(
                        chat_id=ref,
                        text=f"🎉 Your referral [{escape_markdown(user.first_name)}](tg://user?id={user_id}) just joined and earned you 3 points!",
                        parse_mode="Markdown"
                    )
            await query.edit_message_text("✅ You've joined all public channels!", reply_markup=main_menu())
        else:
            await query.edit_message_text("❗ Still missing some channels.", reply_markup=main_menu())
        return

    if query.data == "balance":
        await query.edit_message_text(f"💰 Your balance: `{user_data['points']} points`", parse_mode="Markdown",
                                      reply_markup=back_button())

    elif query.data == "referral_info":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        refs = "\n".join(
            f"• [{escape_markdown(await context.bot.get_chat(uid).first_name)}](tg://user?id={uid})"
            for uid in user_data["referrals"]
        ) or "No referrals yet."
        await query.edit_message_text(
            f"🔗 *Your Referral Link:*\n`{link}`\n\n👥 *Referrals: {len(user_data['referrals'])}*\n\n{refs}",
            parse_mode="Markdown", reply_markup=back_button())

    elif query.data == "redeem":
        if user_data["points"] >= 30:
            await query.edit_message_text("🎁 Please send your *Gmail address* to redeem your reward.",
                                          parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
            return WAITING_FOR_GMAIL
        else:
            await query.edit_message_text("⚠️ Not enough points! You need at least 30.", reply_markup=back_button(),
                                          parse_mode="Markdown")

    elif query.data == "daily_bonus":
        now = datetime.utcnow()
        if not user_data["last_bonus"] or now - user_data["last_bonus"] >= timedelta(days=1):
            dice = await context.bot.send_dice(chat_id=user_id, emoji="🎲")
            rolled = dice.dice.value
            user_data["points"] += rolled
            user_data["last_bonus"] = now
            await query.message.delete()
            await context.bot.send_message(user_id, f"🎉 You rolled a {rolled} and earned +{rolled} points!",
                                           reply_markup=back_button(), parse_mode="Markdown")
        else:
            next_bonus = user_data["last_bonus"] + timedelta(days=1)
            hours_left = int((next_bonus - now).total_seconds() // 3600)
            await query.edit_message_text(f"⏳ Bonus already claimed. Try again in {hours_left} hours.",
                                          reply_markup=back_button(), parse_mode="Markdown")

    elif query.data == "how_to_earn":
        await query.edit_message_text("📘 *Earn Points:*\n\n• +3 per referral\n• +1–6 daily bonus\n• 30 to redeem",
                                      parse_mode="Markdown", reply_markup=back_button())

    elif query.data == "menu":
        await query.edit_message_text("🏠 Main Menu", reply_markup=main_menu(), parse_mode="Markdown")


async def handle_gmail_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    gmail = update.message.text.strip()
    users_data[user_id]["points"] -= 30
    await update.message.reply_text("✅ Gmail received. Our team will contact you shortly.",
                                    reply_markup=main_menu())
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 *Redeem Request:*\n\nUser: `{user_id}`\nGmail: `{gmail}`\nPoints Left: {users_data[user_id]['points']}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Redeem cancelled.", reply_markup=main_menu())
    return ConversationHandler.END


async def run_webserver():
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()


async def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()

    redeem_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^redeem$")],
        states={WAITING_FOR_GMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gmail_input)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(redeem_conv)
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot is running...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(asyncio.gather(run_webserver(), run_bot()))
