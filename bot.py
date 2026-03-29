import telebot
import sqlite3
from datetime import datetime
import os
from flask import Flask
from threading import Thread

# ================== BOT TOKEN FROM RENDER ==================
bot = telebot.TeleBot(os.environ["BOT_TOKEN"])

# ================== DATABASE ==================
conn = sqlite3.connect('expenses.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    type TEXT,
    amount REAL,
    category TEXT,
    date TEXT
)
''')
conn.commit()

# ================== KEYBOARD ==================
def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('➕ Add Income', '➖ Add Expense')
    markup.row('💰 Balance', '📜 History')
    return markup

# ================== KEEP RENDER ALIVE ==================
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ Expense Bot is running on Render!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask, daemon=True).start()

# ================== START COMMAND ==================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "👋 Hi! Your simple Expense Tracker is ready.\n"
        "Use the buttons below 👇", 
        reply_markup=main_keyboard())

# ================== ADD INCOME ==================
@bot.message_handler(func=lambda m: m.text == '➕ Add Income')
def add_income(message):
    msg = bot.reply_to(message, "Enter income amount (number only):")
    bot.register_next_step_handler(msg, process_income)

def process_income(message):
    try:
        amount = float(message.text)
        msg = bot.reply_to(message, "Category/Source? (e.g. Salary, Freelance)")
        bot.register_next_step_handler(msg, lambda m: save_transaction(m, "income", amount))
    except:
        bot.reply_to(message, "❌ Please send a number only.")

# ================== ADD EXPENSE ==================
@bot.message_handler(func=lambda m: m.text == '➖ Add Expense')
def add_expense(message):
    msg = bot.reply_to(message, "Enter expense amount (number only):")
    bot.register_next_step_handler(msg, process_expense)

def process_expense(message):
    try:
        amount = float(message.text)
        msg = bot.reply_to(message, "What did you spend on? (e.g. Food, Transport, Rent)")
        bot.register_next_step_handler(msg, lambda m: save_transaction(m, "expense", amount))
    except:
        bot.reply_to(message, "❌ Please send a number only.")

# ================== SAVE TRANSACTION ==================
def save_transaction(message, trans_type, amount):
    category = message.text
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cursor.execute(
        "INSERT INTO transactions (user_id, type, amount, category, date) VALUES (?, ?, ?, ?, ?)",
        (message.from_user.id, trans_type, amount, category, date)
    )
    conn.commit()

    emoji = "➕" if trans_type == "income" else "➖"
    bot.reply_to(message, 
        f"{emoji} Saved successfully!\n"
        f"{trans_type.capitalize()}: ރ{amount:,.0f}\n"
        f"Category: {category}\n"
        f"Date: {date}", 
        reply_markup=main_keyboard())

# ================== BALANCE (with MVR ރ) ==================
@bot.message_handler(func=lambda m: m.text == '💰 Balance')
def show_balance(message):
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as inc,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as exp
        FROM transactions 
        WHERE user_id = ?
    """, (message.from_user.id,))
    result = cursor.fetchone()
    income = result[0] or 0
    expense = result[1] or 0
    balance = income - expense

    bot.reply_to(message, 
        f"💰 Your Balance\n\n"
        f"Income   : +ރ{income:,.0f}\n"
        f"Expense  : -ރ{expense:,.0f}\n"
        f"──────────────\n"
        f"Balance  : ރ{balance:,.0f}", 
        reply_markup=main_keyboard())

# ================== HISTORY ==================
@bot.message_handler(func=lambda m: m.text == '📜 History')
def show_history(message):
    cursor.execute("""
        SELECT type, amount, category, date 
        FROM transactions 
        WHERE user_id = ? 
        ORDER BY id DESC LIMIT 10
    """, (message.from_user.id,))
    
    rows = cursor.fetchall()
    if not rows:
        bot.reply_to(message, "No transactions yet.", reply_markup=main_keyboard())
        return

    text = "📜 Last 10 transactions:\n\n"
    for row in rows:
        emoji = "➕" if row[0] == "income" else "➖"
        text += f"{emoji} {row[3]}\n{row[0].capitalize()}: ރ{row[1]:,.0f} - {row[2]}\n\n"

    bot.reply_to(message, text, reply_markup=main_keyboard())

# ================== START BOT ==================
print("🚀 Expense Bot started on Render!")
bot.infinity_polling()
