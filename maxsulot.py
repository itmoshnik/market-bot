import telebot
import sqlite3
import logging
from telebot import types

# 1. SOZLAMALAR
#TOKEN = "8529734950:AAE0kXZGJ9eIwwcRB4J6Zbfe27Rm39TfyTM"
#bot = telebot.TeleBot(TOKEN)

import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)




# Terminalda xatolarni ko'rib turish uchun
logging.basicConfig(level=logging.INFO)

# Vaqtinchalik ma'lumotlar ombori (Foydalanuvchi qadamlarini eslab qolish uchun)
user_data = {}

# 2. BAZA BILAN ISHLASH (SQLITE)
def init_db():
    conn = sqlite3.connect('market.db', check_same_thread=False)
    cursor = conn.cursor()
    # Foydalanuvchilar
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (tg_id INTEGER PRIMARY KEY, name TEXT)''')
    # Mahsulotlar (Kategoriyalar bilan boyitilgan)
    cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       title TEXT, 
                       price REAL, 
                       photo_id TEXT,
                       added_by INTEGER)''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# 3. TUGMALAR (REPLY KEYBOARD)
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔍 Qidiruv", "📦 Barcha mahsulotlar")
    markup.add("➕ Mahsulot qo'shish", "👤 Profil")
    return markup

# 4. START BUYRUG'I
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    
    cursor.execute("INSERT OR IGNORE INTO users (tg_id, name) VALUES (?, ?)", (uid, name))
    conn.commit()
    
    text = f"Salom {name}! \nBu bot orqali mahsulotlarni bazaga qo'shishingiz va qidirishingiz mumkin."
    bot.send_message(uid, text, reply_markup=main_menu())

# 5. MAHSULOT QO'SHISH (STEP-BY-STEP LOGIC)
@bot.message_handler(func=lambda m: m.text == "➕ Mahsulot qo'shish")
def add_product_start(message):
    msg = bot.send_message(message.chat.id, "Mahsulot nomini kiriting:")
    bot.register_next_step_handler(msg, process_title)

def process_title(message):
    user_data[message.chat.id] = {'title': message.text}
    msg = bot.send_message(message.chat.id, "Narxini kiriting (masalan: 25000):")
    bot.register_next_step_handler(msg, process_price)

def process_price(message):
    try:
        price = float(message.text)
        user_data[message.chat.id]['price'] = price
        msg = bot.send_message(message.chat.id, "Mahsulot rasm yuboring (file emas, rasm ko'rinishida):")
        bot.register_next_step_handler(msg, process_photo)
    except ValueError:
        msg = bot.send_message(message.chat.id, "⚠️ Narxni faqat raqamda kiriting:")
        bot.register_next_step_handler(msg, process_price)

def process_photo(message):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "⚠️ Iltimos, rasm yuboring!")
        bot.register_next_step_handler(msg, process_photo)
        return
    
    photo_id = message.photo[-1].file_id
    data = user_data[message.chat.id]
    
    cursor.execute("INSERT INTO products (title, price, photo_id, added_by) VALUES (?, ?, ?, ?)",
                   (data['title'], data['price'], photo_id, message.chat.id))
    conn.commit()
    
    bot.send_message(message.chat.id, "✅ Mahsulot muvaffaqiyatli saqlandi!", reply_markup=main_menu())

# 6. KO'RISH VA QIDIRUV
@bot.message_handler(func=lambda m: m.text == "📦 Barcha mahsulotlar")
def show_all(message):
    cursor.execute("SELECT title, price, photo_id FROM products")
    items = cursor.fetchall()
    
    if not items:
        bot.send_message(message.chat.id, "Hozircha baza bo'sh.")
        return
    
    for item in items:
        caption = f"📦 **Mahsulot:** {item[0]}\n💰 **Narxi:** {item[1]:,.0f} so'm"
        bot.send_photo(message.chat.id, item[2], caption=caption, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔍 Qidiruv")
def search_start(message):
    msg = bot.send_message(message.chat.id, "Qidirilayotgan mahsulot nomini yozing:")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text
    cursor.execute("SELECT title, price, photo_id FROM products WHERE title LIKE ?", ('%' + query + '%',))
    results = cursor.fetchall()
    
    if not results:
        bot.send_message(message.chat.id, "Hech narsa topilmadi. ❌")
    else:
        for item in results:
            caption = f"🔍 Topildi:\n📦 **{item[0]}**\n💰 **Narxi:** {item[1]:,.0f} so'm"
            bot.send_photo(message.chat.id, item[2], caption=caption, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 Profil")
def profile(message):
    uid = message.chat.id
    cursor.execute("SELECT COUNT(*) FROM products WHERE added_by = ?", (uid,))
    count = cursor.fetchone()[0]
    bot.send_message(uid, f"👤 **Sizning profilingiz**\n\n🆔 TG ID: `{uid}`\n📦 Siz qo'shgan mahsulotlar: {count} ta", parse_mode="Markdown")

# 7. BOTNI UZLUKSIZ ISHLATISH
if __name__ == "__main__":
    print("--- Bot ishga tushdi ---")
    bot.infinity_polling()

