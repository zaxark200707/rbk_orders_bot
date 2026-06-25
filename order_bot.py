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

def delete_previous(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📋 Новый заказ", callback_data="new_order"))
    markup.add(InlineKeyboardButton("📦 Принятые заказы", callback_data="my_orders"))
    markup.add(InlineKeyboardButton("✅ Выполненные заказы", callback_data="archive"))
    markup.add(InlineKeyboardButton("📌 Шаблоны", callback_data="templates"))
    sent = bot.send_message(message.chat.id, "🏢 Заказы РБК\nВыберите действие:", reply_markup=markup)
    user_data[message.chat.id] = {"last_bot_message": sent.message_id}

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    delete_previous(chat_id, call.message.message_id)

    if data == "new_order":
        user_data[chat_id] = {}
        sent = bot.send_message(chat_id, "Введите имя клиента:")
        user_data[chat_id]["last_bot_message"] = sent.message_id
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

    if data == "templates":
        show_templates(chat_id)
        return

    if data == "back_to_templates":
        show_templates(chat_id)
        return

    if data.startswith("template_"):
        template_id = data.split("_", 1)[1]
        send_template(chat_id, template_id)
        return

    if data.startswith("done_"):
        try:
            order_id = int(data.split("_")[1])
        except:
            bot.send_message(chat_id, "Ошибка ID заказа.")
            return
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("UPDATE orders SET status='archived' WHERE id=?", (order_id,))
        conn.commit()
        conn.close()
        sent = bot.send_message(chat_id, "✅ Заказ выполнен и перемещён в архив.")
        user_data[chat_id]["last_bot_message"] = sent.message_id
        show_orders(chat_id, status="active")
        return

    if data.startswith("del_"):
        try:
            order_id = int(data.split("_")[1])
        except:
            bot.send_message(chat_id, "Ошибка ID заказа.")
            return
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("DELETE FROM orders WHERE id=?", (order_id,))
        conn.commit()
        conn.close()
        sent = bot.send_message(chat_id, "🗑 Заказ удалён навсегда.")
        user_data[chat_id]["last_bot_message"] = sent.message_id
        show_orders(chat_id, status="archived")
        return

    if data.startswith("show_"):
        try:
            order_id = int(data.split("_")[1])
        except:
            bot.send_message(chat_id, "Ошибка ID заказа.")
            return
        show_order_details(chat_id, order_id)
        return

    if data.startswith("wood_"):
        wood = data.split("_")[1]
        if chat_id not in user_data:
            user_data[chat_id] = {}
        user_data[chat_id]["wood"] = wood
        sent = bot.send_message(chat_id, "Введите длину (мм):")
        user_data[chat_id]["last_bot_message"] = sent.message_id
        return

    if data.startswith("grade_"):
        grade = data.split("_")[1]
        if chat_id not in user_data:
            user_data[chat_id] = {}
        user_data[chat_id]["grade"] = grade
        sent = bot.send_message(chat_id, "Введите количество щитов:")
        user_data[chat_id]["last_bot_message"] = sent.message_id
        return

    bot.send_message(chat_id, "Неизвестная команда.")

def show_templates(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Цена без данных", callback_data="template_price_no_data"))
    markup.add(InlineKeyboardButton("Размер без породы/сорта", callback_data="template_size_only"))
    markup.add(InlineKeyboardButton("Уточнить сорт", callback_data="template_grade"))
    markup.add(InlineKeyboardButton("Разница между сортами", callback_data="template_grade_diff"))
    markup.add(InlineKeyboardButton("Для фото", callback_data="template_photo"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    sent = bot.send_message(chat_id, "Выберите шаблон:", reply_markup=markup)
    user_data[chat_id]["last_bot_message"] = sent.message_id

def send_template(chat_id, template_id):
    delete_previous(chat_id, user_data[chat_id].get("last_bot_message", 0))
    
    if template_id == "price_no_data":
        text = (
            "Здравствуйте.\n\n"
            "Чтобы я назвал точную цену, напишите, пожалуйста, в одном сообщении:\n\n"
            "- Размеры (пример: 1000×1000×20)\n"
            "- Породу (дуб / бук / ясень)\n"
            "- Сорт (АВ / ВВ / ВС)\n\n"
            "Тогда сразу скажу стоимость."
        )
    elif template_id == "size_only":
        text = (
            "Здравствуйте. Размер понял, но для точной цены нужны ещё порода и сорт.\n\n"
            "Напишите:\n"
            "- породу (дуб/бук/ясень)\n"
            "- сорт (АВ/ВВ/ВС)\n\n"
            "Тогда скажу точную цену."
        )
    elif template_id == "grade":
        text = (
            "Здравствуйте. С размерами и породой всё ясно.\n\n"
            "Уточните сорт. От него зависит цена:\n\n"
            "АВ — без сучков. Цветовая гамма ровная, красивая. Для видимой мебели, фасадов, столешниц, дверей.\n\n"
            "ВВ — мелкие живые сросшиеся сучки. Цветовая гамма хорошая, но есть небольшие сучки. Для корпусной мебели, полок, внутренних деталей.\n\n"
            "ВС — допускаются живые сросшиеся сучки. Цветовая гамма не соблюдается, есть разнотон. Для черновых работ и невидимых частей.\n\n"
            "Трещины и крупные сучки не допускаются ни в одном сорте."
        )
    elif template_id == "grade_diff":
        text = (
            "Коротко о сортах:\n\n"
            "АВ — без сучков. Для видимой мебели, фасадов, столешниц.\n\n"
            "ВВ — мелкие живые сучки. Для корпусной мебели, полок.\n\n"
            "ВС — допускаются живые сучки. Для черновых работ.\n\n"
            "Трещины и крупные сучки не допускаются ни в одном сорте."
        )
    elif template_id == "photo":
        text = (
            "Фото могу скинуть.\n\n"
            "Напишите, пожалуйста:\n"
            "- породу\n"
            "- сорт\n\n"
            "Чтобы я показал именно то, что вам нужно."
        )
    else:
        text = "Шаблон не найден."

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Назад к шаблонам", callback_data="back_to_templates"))
    sent = bot.send_message(chat_id, text, reply_markup=markup)
    user_data[chat_id]["last_bot_message"] = sent.message_id

def show_order_details(chat_id, order_id):
    delete_previous(chat_id, user_data[chat_id].get("last_bot_message", 0))
    
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT client_name, phone, wood, length, width, thickness, grade, quantity, price_per_piece, total_price, production_price_per_piece, total_production_price, profit, status FROM orders WHERE id=?", (order_id,))
    order = c.fetchone()
    conn.close()

    if not order:
        bot.send_message(chat_id, "Заказ не найден.")
        return

    (name, phone, wood, length, width, thickness, grade, quantity, price_per_piece, total_price, prod_price_per_piece, total_prod_price, profit, status) = order

    range_key = get_range(length)
    if range_key is None:
        bot.send_message(chat_id, "Ошибка диапазона")
        return

    price_per_cube = PRICES[wood][range_key][grade]
    production_price_per_cube = price_per_cube - 30000

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
        f"💰 Цена куба (с наценкой, без НДС): {price_per_cube:,.0f} руб\n"
        f"🧾 Цена куба (с наценкой, с НДС 22%): {price_per_cube * 1.22:,.0f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"🏭 Цена куба (производственная, без НДС): {production_price_per_cube:,.0f} руб\n"
        f"🧾 Цена куба (производственная, с НДС 22%): {production_price_per_cube * 1.22:,.0f} руб\n"
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
        markup.add(InlineKeyboardButton("✅ Выполнен", callback_data=f"done_{order_id}"))
    else:
        markup.add(InlineKeyboardButton("🗑 Удалить навсегда", callback_data=f"del_{order_id}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    sent = bot.send_message(chat_id, text, reply_markup=markup)
    user_data[chat_id]["last_bot_message"] = sent.message_id

def show_orders(chat_id, status="active"):
    delete_previous(chat_id, user_data[chat_id].get("last_bot_message", 0))
    
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT id, client_name, phone, wood, length, width, thickness, grade, quantity, total_price FROM orders WHERE status=?", (status,))
    orders = c.fetchall()
    conn.close()

    status_name = "Принятые" if status == "active" else "Выполненные"
    markup = InlineKeyboardMarkup()
    
    if not orders:
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
        sent = bot.send_message(chat_id, f"📭 {status_name} заказов нет.", reply_markup=markup)
        user_data[chat_id]["last_bot_message"] = sent.message_id
        return

    for order in orders:
        order_id, name, phone, wood, length, width, thickness, grade, quantity, total_price = order
        text = f"{name} ({phone}) — {wood} {int(length)}×{int(width)}×{int(thickness)} — {quantity} шт — {total_price:.0f} руб"
        markup.add(InlineKeyboardButton(text, callback_data=f"show_{order_id}"))

    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    sent = bot.send_message(chat_id, f"📦 {status_name} заказы:", reply_markup=markup)
    user_data[chat_id]["last_bot_message"] = sent.message_id

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # Удаляем сообщение пользователя
    delete_previous(chat_id, message.message_id)
    # Удаляем предыдущее сообщение бота
    delete_previous(chat_id, user_data.get(chat_id, {}).get("last_bot_message", 0))

    if chat_id not in user_data:
        start(message)
        return

    data = user_data[chat_id]

    if "client_name" not in data:
        data["client_name"] = text
        sent = bot.send_message(chat_id, "Введите номер телефона клиента:")
        user_data[chat_id]["last_bot_message"] = sent.message_id
        return

    if "phone" not in data:
        data["phone"] = text
        markup = InlineKeyboardMarkup()
        for wood in PRICES.keys():
            markup.add(InlineKeyboardButton(wood, callback_data=f"wood_{wood}"))
        sent = bot.send_message(chat_id, "Выберите породу:", reply_markup=markup)
        user_data[chat_id]["last_bot_message"] = sent.message_id
        return

    if "wood" not in data:
        bot.send_message(chat_id, "Сначала выберите породу через кнопку.")
        return

    if "length" not in data:
        try:
            length = float(text)
            if get_range(length) is None:
                sent = bot.send_message(chat_id, "Длина должна быть от 260 до 3000 мм. Введите заново:")
                user_data[chat_id]["last_bot_message"] = sent.message_id
                return
            data["length"] = length
            sent = bot.send_message(chat_id, "Введите ширину (мм):")
            user_data[chat_id]["last_bot_message"] = sent.message_id
        except:
            sent = bot.send_message(chat_id, "Введите число, например 560")
            user_data[chat_id]["last_bot_message"] = sent.message_id
        return

    if "width" not in data:
        try:
            data["width"] = float(text)
            sent = bot.send_message(chat_id, "Введите толщину (мм):")
            user_data[chat_id]["last_bot_message"] = sent.message_id
        except:
            sent = bot.send_message(chat_id, "Введите число, например 20")
            user_data[chat_id]["last_bot_message"] = sent.message_id
        return

    if "thickness" not in data:
        try:
            data["thickness"] = float(text)
            markup = InlineKeyboardMarkup()
            for grade in ["AB", "BB", "BC"]:
                markup.add(InlineKeyboardButton(grade, callback_data=f"grade_{grade}"))
            sent = bot.send_message(chat_id, "Выберите сорт:", reply_markup=markup)
            user_data[chat_id]["last_bot_message"] = sent.message_id
        except:
            sent = bot.send_message(chat_id, "Введите число")
            user_data[chat_id]["last_bot_message"] = sent.message_id
        return

    if "grade" not in data:
        bot.send_message(chat_id, "Сначала выберите сорт через кнопку.")
        return

    if "quantity" not in data:
        try:
            data["quantity"] = int(text)
            save_order(chat_id)
        except:
            sent = bot.send_message(chat_id, "Введите целое число, например 5")
            user_data[chat_id]["last_bot_message"] = sent.message_id
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
        bot.send_message(chat_id, "Ошибка диапазона")
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
        f"💰 С НАЦЕНКОЙ (твоя цена)\n"
        f"Цена куба: {price_per_cube:,.0f} руб\n"
        f"Цена куба с НДС 22%: {cube_price_with_nds:,.0f} руб\n"
        f"Цена за 1 шт: {price_per_piece:.2f} руб\n"
        f"Общая цена ({quantity} шт): {total_price:.2f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"🏭 БЕЗ НАЦЕНКИ (производственная)\n"
        f"Цена куба: {production_price_per_cube:,.0f} руб\n"
        f"Цена куба с НДС 22%: {production_cube_price_with_nds:,.0f} руб\n"
        f"Цена за 1 шт: {production_price_per_piece:.2f} руб\n"
        f"Общая цена ({quantity} шт): {total_production_price:.2f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"💵 ТВОЙ ДОХОД\n"
        f"Доход с заказа: {profit:.2f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"🏦 СКОЛЬКО ПРОИЗВОДСТВУ\n"
        f"Сумма: {total_production_price:.2f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"📩 ДЛЯ КЛИЕНТА (вставить в Авито)\n"
        f"Щит: {wood}, сорт {grade}\n"
        f"Размер: {int(length)}×{int(width)}×{int(thickness)} мм\n"
        f"Количество: {quantity} шт\n"
        f"Цена: {total_price:.2f} руб\n"
        f"━━━━━━━━━━━━\n"
        f"🏗 ПРОИЗВОДСТВЕННОЕ ЗАДАНИЕ\n"
        f"Порода: {wood}\n"
        f"Размер: {int(length)}×{int(width)}×{int(thickness)} мм\n"
        f"Сорт: {grade}\n"
        f"Количество: {quantity} шт"
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
    sent = bot.send_message(chat_id, response, reply_markup=markup)
    user_data[chat_id]["last_bot_message"] = sent.message_id

print("Бот Заказы РБК запущен...")
bot.polling()
