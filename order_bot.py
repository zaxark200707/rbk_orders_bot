import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import datetime

TOKEN = "8989910662:AAG-bn11gPpc52YCfH6SxM-iiJ28N2BsYMs"
bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  client_name TEXT,
                  phone TEXT,
                  wood TEXT,
                  length REAL,
                  width REAL,
                  thickness REAL,
                  grade TEXT,
                  quantity INTEGER,
                  price_per_piece REAL,
                  total_price REAL,
                  production_price_per_piece REAL,
                  total_production_price REAL,
                  profit REAL,
                  date TEXT,
                  status TEXT)''')
    conn.commit()
    conn.close()

init_db()

PRICES = {
    "Бук": {
        (260, 990):   {"AB": 180000, "BB": 175000, "BC": 170000},
        (1000, 1990): {"AB": 220000, "BB": 200000, "BC": 190000},
        (2000, 3000): {"AB": 250000, "BB": 175000, "BC": 220000},
    },
    "Дуб": {
        (260, 990):   {"AB": 210000, "BB": 205000, "BC": 200000},
        (1000, 1990): {"AB": 290000, "BB": 270000, "BC": 230000},
        (2000, 3000): {"AB": 330000, "BB": 300000, "BC": 280000},
    },
    "Ясень": {
        (260, 990):   {"AB": 205000, "BB": 200000, "BC": 195000},
        (1000, 1990): {"AB": 280000, "BB": 255000, "BC": 225000},
        (2000, 3000): {"AB": 325000, "BB": 295000, "BC": 275000},
    },
}

user_data = {}

def get_range(length):
    for low, high in [(260, 990), (1000, 1990), (2000, 3000)]:
        if low <= length <= high:
            return (low, high)
    return None

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📋 Новый заказ", callback_data="new_order"))
    markup.add(InlineKeyboardButton("📦 Принятые заказы", callback_data="my_orders"))
    markup.add(InlineKeyboardButton("✅ Выполненные заказы", callback_data="archive"))
    bot.send_message(message.chat.id, "🏢 Заказы РБК\nВыберите действие:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "new_order":
        user_data[chat_id] = {}
        bot.send_message(chat_id, "Введите имя клиента:")
        return

    if data == "my_orders":
        show_orders(chat_id, status="active")
        return

    if data == "archive":
        show_orders(chat_id, status="archived")
        return

    if data == "back_to_menu":
        start(call.message)
        return

    if data.startswith("delete_"):
        try:
            order_id = int(data.split("_")[1])
        except:
            bot.send_message(chat_id, "❌ Ошибка ID заказа.")
            return
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("UPDATE orders SET status='archived' WHERE id=?", (order_id,))
        conn.commit()
        conn.close()
        bot.send_message(chat_id, "✅ Заказ перемещён в выполненные.")
        show_orders(chat_id, status="active")
        return

    if data.startswith("delete_archive_"):
        try:
            order_id = int(data.split("_")[2])
        except:
            bot.send_message(chat_id, "❌ Ошибка ID заказа.")
            return
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("DELETE FROM orders WHERE id=?", (order_id,))
        conn.commit()
        conn.close()
        bot.send_message(chat_id, "🗑 Заказ удалён навсегда.")
        show_orders(chat_id, status="archived")
        return

    if data.startswith("show_"):
        try:
            order_id = int(data.split("_")[1])
        except:
            bot.send_message(chat_id, "❌ Ошибка ID заказа.")
            return
        show_order_details(chat_id, order_id)
        return

    if data.startswith("wood_"):
        wood = data.split("_")[1]
        if chat_id not in user_data:
            user_data[chat_id] = {}
        user_data[chat_id]["wood"] = wood
        bot.send_message(chat_id, "Введите длину (мм):")
        return

    if data.startswith("grade_"):
        grade = data.split("_")[1]
        if chat_id not in user_data:
            user_data[chat_id] = {}
        user_data[chat_id]["grade"] = grade
        bot.send_message(chat_id, "Введите количество щитов:")
        return

    bot.send_message(chat_id, "❌ Неизвестная команда.")

def show_order_details(chat_id, order_id):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT client_name, phone, wood, length, width, thickness, grade, quantity, price_per_piece, total_price, production_price_per_piece, total_production_price, profit, status FROM orders WHERE id=?", (order_id,))
    order = c.fetchone()
    conn.close()

    if not order:
        bot.send_message(chat_id, "❌ Заказ не найден.")
        return

    (name, phone, wood, length, width, thickness, grade, quantity, price_per_piece, total_price, prod_price_per_piece, total_prod_price, profit, status) = order

    status_name = "Принят" if status == "active" else "Выполнен"
    text = (
        f"📋 Заказ #{order_id}\n"
        f"━━━━━━━━━━━━\n"
        f"👤 Клиент: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"🌳 Порода: {wood}\n"
        f"📏 Размер: {int(length)}×{int(width)}×{int(thickness)} мм\n"
        f"🏷️ Сорт: {grade}\n"
        f"📦 Количество: {quantity} шт\n"
        f"📌 Статус: {status_name}\n"
        f"━━━━━━━━━━━━\n"
        f"💰 Цена за 1 шт: {price_per_piece:.2f} руб\n"
        f"🏭 Производственная цена за 1 шт: {prod_price_per_piece:.2f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"💰 Общая сумма: {total_price:.2f} руб\n"
        f"🏭 Общая производственная: {total_prod_price:.2f} руб\n"
        f"💵 Твой доход: {profit:.2f} руб"
    )

    markup = InlineKeyboardMarkup()
    if status == "active":
        markup.add(InlineKeyboardButton("✅ Выполнен", callback_data=f"delete_{order_id}"))
    else:
        markup.add(InlineKeyboardButton("🗑 Удалить навсегда", callback_data=f"delete_archive_{order_id}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    bot.send_message(chat_id, text, reply_markup=markup)

def show_orders(chat_id, status="active"):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT id, client_name, phone, wood, length, width, thickness, grade, quantity, total_price FROM orders WHERE status=?", (status,))
    orders = c.fetchall()
    conn.close()

    if not orders:
        bot.send_message(chat_id, "📭 Заказов нет.")
        return

    markup = InlineKeyboardMarkup()
    for order in orders:
        order_id, name, phone, wood, length, width, thickness, grade, quantity, total_price = order
        text = f"{name} ({phone}) — {wood} {int(length)}×{int(width)}×{int(thickness)} — {quantity} шт — {total_price:.0f} руб"
        markup.add(InlineKeyboardButton(text, callback_data=f"show_{order_id}"))

    status_name = "Принятые" if status == "active" else "Выполненные"
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    bot.send_message(chat_id, f"📦 {status_name} заказы:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id not in user_data:
        start(message)
        return

    data = user_data[chat_id]

    if "client_name" not in data:
        data["client_name"] = text
        bot.send_message(chat_id, "Введите номер телефона клиента:")
        return

    if "phone" not in data:
        data["phone"] = text
        markup = InlineKeyboardMarkup()
        for wood in PRICES.keys():
            markup.add(InlineKeyboardButton(wood, callback_data=f"wood_{wood}"))
        bot.send_message(chat_id, "Выберите породу:", reply_markup=markup)
        return

    if "wood" not in data:
        bot.send_message(chat_id, "❌ Сначала выберите породу через кнопку.")
        return

    if "length" not in data:
        try:
            length = float(text)
            if get_range(length) is None:
                bot.send_message(chat_id, "❌ Длина должна быть от 260 до 3000 мм. Введите заново:")
                return
            data["length"] = length
            bot.send_message(chat_id, "Введите ширину (мм):")
        except:
            bot.send_message(chat_id, "❌ Введите число, например 560")
        return

    if "width" not in data:
        try:
            data["width"] = float(text)
            bot.send_message(chat_id, "Введите толщину (мм):")
        except:
            bot.send_message(chat_id, "❌ Введите число, например 20")
        return

    if "thickness" not in data:
        try:
            data["thickness"] = float(text)
            markup = InlineKeyboardMarkup()
            for grade in ["AB", "BB", "BC"]:
                markup.add(InlineKeyboardButton(grade, callback_data=f"grade_{grade}"))
            bot.send_message(chat_id, "Выберите сорт:", reply_markup=markup)
        except:
            bot.send_message(chat_id, "❌ Введите число")
        return

    if "grade" not in data:
        bot.send_message(chat_id, "❌ Сначала выберите сорт через кнопку.")
        return

    if "quantity" not in data:
        try:
            data["quantity"] = int(text)
            save_order(chat_id)
        except:
            bot.send_message(chat_id, "❌ Введите целое число, например 5")
        return

def save_order(chat_id):
    data = user_data[chat_id]
    wood = data["wood"]
    length = data["length"]
    width = data["width"]
    thickness = data["thickness"]
    grade = data["grade"]
    client_name = data["client_name"]
    phone = data["phone"]
    quantity = data["quantity"]

    range_key = get_range(length)
    if range_key is None:
        bot.send_message(chat_id, "❌ Ошибка диапазона")
        return

    price_per_cube = PRICES[wood][range_key][grade]
    production_price_per_cube = price_per_cube - 30000
    cube_price_with_nds = price_per_cube * 1.22
    production_cube_price_with_nds = production_price_per_cube * 1.22

    volume = (length / 1000) * (width / 1000) * (thickness / 1000)
    price_per_piece = volume * price_per_cube
    production_price_per_piece = volume * production_price_per_cube
    total_price = price_per_piece * quantity
    total_production_price = production_price_per_piece * quantity
    profit = total_price - total_production_price

    response = (
        f"✅ Заказ сохранён!\n"
        f"━━━━━━━━━━━━\n"
        f"👤 Клиент: {client_name}\n"
        f"📞 Телефон: {phone}\n"
        f"🌳 Порода: {wood}\n"
        f"📏 Размер: {int(length)}×{int(width)}×{int(thickness)} мм\n"
        f"🏷️ Сорт: {grade}\n"
        f"📦 Количество: {quantity} шт\n"
        f"━━━━━━━━━━━━\n"
        f"💰 Цена куба (с наценкой, без НДС): {price_per_cube:,.0f} руб\n"
        f"🧾 Цена куба (с наценкой, с НДС 22%): {cube_price_with_nds:,.0f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"🏭 Цена куба (производственная, без НДС): {production_price_per_cube:,.0f} руб\n"
        f"🧾 Цена куба (производственная, с НДС 22%): {production_cube_price_with_nds:,.0f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"💵 Цена за 1 шт: {price_per_piece:.2f} руб\n"
        f"🏭 Производственная цена за 1 шт: {production_price_per_piece:.2f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"💰 Общая цена ({quantity} шт): {total_price:.2f} руб\n"
        f"🏭 Общая производственная цена: {total_production_price:.2f} руб\n"
        f"💵 Твой доход с заказа: {profit:.2f} руб"
    )

    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("""INSERT INTO orders 
                 (client_name, phone, wood, length, width, thickness, grade, quantity, 
                  price_per_piece, total_price, production_price_per_piece, total_production_price, profit, date, status) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (client_name, phone, wood, length, width, thickness, grade, quantity,
               price_per_piece, total_price, production_price_per_piece, total_production_price, profit,
               datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "active"))
    conn.commit()
    conn.close()

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📋 Новый заказ", callback_data="new_order"))
    markup.add(InlineKeyboardButton("📦 Принятые заказы", callback_data="my_orders"))
    bot.send_message(chat_id, response, reply_markup=markup)

print("Бот Заказы РБК запущен...")
bot.polling()
