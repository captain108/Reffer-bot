import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InputFile
from aiogram.utils.exceptions import ChatNotFound
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
CHANNEL_IDS = [int(x) for x in os.getenv("CHANNEL_IDS", "").split(",")]  # Required public channels
PRIVATE_CHANNEL_ID = int(os.getenv("PRIVATE_CHANNEL_ID"))  # Optional private channel
REDEMPTION_LOG_CHANNEL = int(os.getenv("REDEMPTION_LOG_CHANNEL"))  # Where bot posts official redemption message

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("referral_bot.db")
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referred_by INTEGER,
    verified INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0
)''')
conn.commit()

def add_user(user_id, referred_by=None):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, referred_by))
    conn.commit()

def get_points(user_id):
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def add_points(user_id, amount):
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def mark_verified(user_id):
    cursor.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def mark_unverified(user_id):
    cursor.execute("UPDATE users SET verified = 0 WHERE user_id = ?", (user_id,))
    conn.commit()

def is_verified(user_id):
    cursor.execute("SELECT verified FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] == 1

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    referred_by = int(args) if args.isdigit() and int(args) != user_id else None

    add_user(user_id, referred_by)

    if referred_by:
        add_points(referred_by, 30)
        await bot.send_message(referred_by, f"{message.from_user.full_name} joined using your referral link! You earned 30 points.")
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, f"New user {message.from_user.full_name} joined via referral link of {referred_by}.")

    await message.answer("Welcome! Please verify your channel membership by sending /verify")

@dp.message_handler(commands=['verify'])
async def verify_cmd(message: types.Message):
    user_id = message.from_user.id
    failed = []

    for channel_id in CHANNEL_IDS:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                failed.append(channel_id)
        except ChatNotFound:
            failed.append(channel_id)

    if failed:
        await message.reply("You must join all required public channels to verify.")
        mark_unverified(user_id)
    else:
        mark_verified(user_id)
        await message.reply("Verification successful!")

@dp.message_handler(commands=['redeem'])
async def redeem_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_verified(user_id):
        return await message.reply("You're not verified. Join required channels and use /verify.")

    points = get_points(user_id)
    if points < 30:
        return await message.reply("You need at least 30 points to redeem.")

    add_points(user_id, -30)
    await message.reply("Your redemption request has been sent to the admins. Please wait for approval or contact support.")

    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"User {message.from_user.full_name} ({user_id}) has redeemed 30 points!")

    # Send official message to log channel with trophy image
    trophy_image = InputFile("trophy.jpg")  # Make sure this file exists in your folder
    await bot.send_photo(
        chat_id=REDEMPTION_LOG_CHANNEL,
        photo=trophy_image,
        caption=f"{message.from_user.full_name} just redeemed 30 points! Congratulations!"
    )

@dp.message_handler(commands=['check'])
async def check_cmd(message: types.Message):
    user_id = message.from_user.id
    points = get_points(user_id)
    await message.reply(f"You have {points} points.")

@dp.message_handler(commands=['recheck'])
async def recheck_cmd(message: types.Message):
    user_id = message.from_user.id
    failed = []

    for channel_id in CHANNEL_IDS:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                failed.append(channel_id)
        except:
            failed.append(channel_id)

    if failed:
        mark_unverified(user_id)
        await message.reply("You left required public channels. Please rejoin and use /verify.")
    else:
        await message.reply("You're still verified.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
