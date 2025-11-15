import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

import os
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# DB Init
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees(
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    balance REAL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    vendor TEXT,
    amount REAL,
    account TEXT,
    status TEXT DEFAULT 'pending'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    reason TEXT
)
""")
conn.commit()

def ensure_user(user):
    cursor.execute("SELECT user_id FROM employees WHERE user_id=?", (user.id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO employees (user_id, name) VALUES (?,?)",
                       (user.id, user.full_name))
        conn.commit()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.reply("Bot is running!")

@dp.message(Command("add_funds"))
async def add_funds(message: types.Message):
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("Usage: /add_funds @user amount")

    if not message.entities or len(message.entities) < 2:
        return await message.reply("Tag the user properly.")

    amount = float(parts[2])
    target = message.entities[1].user
    ensure_user(target)

    cursor.execute("UPDATE employees SET balance = balance + ? WHERE user_id=?",
                   (amount, target.id))
    conn.commit()

    await message.reply(f"Added ₹{amount} to {target.full_name}'s balance.")

@dp.message(Command("add_payment"))
async def add_payment(message: types.Message):
    parts = message.text.split()
    if len(parts) != 5:
        return await message.reply("Usage: /add_payment @user vendor amount account")

    target = message.entities[1].user
    vendor = parts[2]
    amount = float(parts[3])
    account = parts[4]

    cursor.execute("INSERT INTO payments (user_id, vendor, amount, account) VALUES (?,?,?,?)",
                   (target.id, vendor, amount, account))
    conn.commit()

    await message.reply("Payment created.")

@dp.message(Command("paid"))
async def paid(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        return await message.reply("Usage: /paid payment_id")

    pid = int(parts[1])
    cursor.execute("SELECT user_id, amount FROM payments WHERE id=? AND status='pending'", (pid,))
    row = cursor.fetchone()

    if not row:
        return await message.reply("Invalid payment ID")

    user_id, amount = row

    cursor.execute("UPDATE payments SET status='complete' WHERE id=?", (pid,))
    cursor.execute("UPDATE employees SET balance = balance - ? WHERE user_id=?",
                   (amount, user_id))
    conn.commit()

    await message.reply("Payment marked as PAID.")

@dp.message(Command("pending"))
async def pending(message: types.Message):
    cursor.execute("SELECT id, vendor, amount, account FROM payments WHERE status='pending'")
    rows = cursor.fetchall()

    if not rows:
        return await message.reply("No pending payments.")

    text = "Pending Payments:\n\n"
    for r in rows:
        text += f"ID {r[0]} | Vendor: {r[1]} | Amount: {r[2]} | Account: {r[3]}\n"

    await message.reply(text)

async def main():
    await dp.start_polling(bot)

asyncio.run(main())
