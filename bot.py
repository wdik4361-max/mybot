import sqlite3
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

BOT_TOKEN = "8524942516:AAFDyzYGWrYwAawyBgb6rIk8B8dALKgQHmU"
ADMIN_ID = 8565249143

class Form(StatesGroup):
    waiting_for_phone = State()

conn = sqlite3.connect('accounts.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, phone TEXT, date TEXT, paid INTEGER DEFAULT 0)')
conn.commit()

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

menu_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton("📱 Сдать аккаунт")]], resize_keyboard=True)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("🔥 СКУПКА АККАУНТОВ MAX\n\n💰 5.6$ за аккаунт\n\nНажми кнопку и отправь номер +79XXXXXXXXX", reply_markup=menu_kb)

@dp.message_handler(lambda message: message.text == "📱 Сдать аккаунт")
async def ask_phone(message: types.Message):
    await Form.waiting_for_phone.set()
    await message.answer("📞 Отправь номер: +79XXXXXXXXX")

@dp.message_handler(state=Form.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not re.match(r'^\+79\d{9}$', phone):
        await message.answer("❌ Ошибка! Формат: +79XXXXXXXXX")
        return
    user_id = message.from_user.id
    username = message.from_user.username or "no_username"
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT * FROM accounts WHERE phone = ?", (phone,))
    if cursor.fetchone():
        await message.answer("❌ Номер уже отправлен")
        await state.finish()
        return
    cursor.execute("INSERT INTO accounts (user_id, username, phone, date) VALUES (?, ?, ?, ?)", (user_id, username, phone, date))
    conn.commit()
    cursor.execute("SELECT id FROM accounts WHERE phone = ?", (phone,))
    record_id = cursor.fetchone()[0]
    await message.answer(f"✅ Принято! ID: {record_id}\nПосле проверки получишь 5.6$")
    await bot.send_message(ADMIN_ID, f"🆕 НОВЫЙ\nID: {record_id}\nЮзер: @{username}\nНомер: {phone}\nДата: {date}\n/pay {record_id}")
    await state.finish()

@dp.message_handler(commands=['stats'])
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total = cursor.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    unpaid = cursor.execute("SELECT COUNT(*) FROM accounts WHERE paid=0").fetchone()[0]
    paid = cursor.execute("SELECT COUNT(*) FROM accounts WHERE paid=1").fetchone()[0]
    await message.answer(f"📊 Всего: {total}\n✅ Оплачено: {paid}\n⏳ Ожидают: {unpaid}")

@dp.message_handler(commands=['list'])
async def list_accounts(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    rows = cursor.execute("SELECT id, username, phone, date, paid FROM accounts ORDER BY id DESC LIMIT 20").fetchall()
    if not rows:
        await message.answer("Нет аккаунтов")
        return
    text = "📋 Последние 20:\n"
    for row in rows:
        status = "✅" if row[4] == 1 else "⏳"
        text += f"{status} ID:{row[0]} | @{row[1]} | {row[2]} | {row[3]}\n"
    await message.answer(text)

@dp.message_handler(commands=['pay'])
async def pay(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        record_id = int(message.text.split()[1])
        row = cursor.execute("SELECT user_id, phone FROM accounts WHERE id=?", (record_id,)).fetchone()
        if not row:
            await message.answer(f"ID {record_id} не найден")
            return
        cursor.execute("UPDATE accounts SET paid=1 WHERE id=?", (record_id,))
        conn.commit()
        try:
            await bot.send_message(row[0], f"✅ Выплата! Аккаунт: {row[1]}\nСумма: 5.6$")
        except:
            pass
        await message.answer(f"✅ ID {record_id} оплачен")
    except:
        await message.answer("Использование: /pay [ID]")

if __name__ == "__main__":
    print("Бот запущен!")
    executor.start_polling(dp, skip_updates=True)
