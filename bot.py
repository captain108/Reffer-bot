import asyncio
from aiohttp import web
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

TOKEN = "8073731661:AAEnHItKmA-Xo0bSXzb95UrGrsql-QaZEo0"
REQUIRED_CHANNELS = [
    "@ultracashonline",
    "@westbengalnetwork2",
    "@ui_zone",
    "https://t.me/+L4ek5JLdYu0zZDg1"
]
ADMIN_ID = 5944513375

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

users_data = {}
WAITING_FOR_GMAIL = range(1)

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

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    await query.answer()

    if user_id not in users_data:
        users_data[user_id] = {"points": 0, "referrals": set(), "last_bonus": None}
    user_data = users_data[user_id]

    missing = await get_missing_channels(user_id, context)
    if missing and query.data != "check_join":
        join_buttons = [[
            InlineKeyboardButton(
                f"Join @{ch.strip('@')}",
                url=f"https://t.me/{ch.strip('@')}"
            )
        ] for ch in missing]
        join_buttons.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_join")])

        for referrer_id, data in users_data.items():
            if user_id in data.get("referrals", set()):
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=(
                        f"⚠️ *Referral Update*\n"
                        f"Your referral [{escape_markdown(user.first_name)}](tg://user?id={user_id}) "
                        f"has unsubscribed from required channels and is no longer eligible."
                    ),
                    parse_mode="Markdown"
                )
                break

        await query.edit_message_text(
            "❗ You must join *all required public channels* to continue.",
            reply_markup=InlineKeyboardMarkup(join_buttons),
            parse_mode="Markdown"
        )
        return
