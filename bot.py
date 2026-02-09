import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# ======================
# НАСТРОЙКИ
# ======================

BOT_TOKEN = "8505195706:AAF6tJXKuK879TkUytXgvA4dOPWr3WCZY5Y"
TELEGRAM_CHAT_ID = -1001943447842  # chat_id группы (бот должен быть админом)

# ======================
# ЛОГИ
# ======================

def log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# ======================
# ИНИЦИАЛИЗАЦИЯ
# ======================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_data = {}  # user_id -> {"photos": [{"file_path":..., "message_id": None}], "sent": False}

log("🚀 Бот инициализирован")

# ======================
# КЛАВИАТУРЫ (только для лички)
# ======================

def keyboard_no_send():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Сбросить")]],
        resize_keyboard=True
    )

def keyboard_with_send():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📨 Отправить"), KeyboardButton(text="❌ Сбросить")]],
        resize_keyboard=True
    )

# ======================
# INLINE КНОПКИ
# ======================

def inline_button_added_inn():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавлен ИНН", callback_data="inn_added")]
        ]
    )

def inline_status_buttons(user_id: int, message_id: int, current_status="❌ Не обработан"):
    statuses = ["Принято в работу", "Партнёр привлечен"]
    buttons = [
        InlineKeyboardButton(
            text=f"{'✅ ' if status==current_status else ''}{status}",
            callback_data=f"status:{status}:{user_id}:{message_id}"
        )
        for status in statuses
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

# ======================
# /start
# ======================

@dp.message(Command(commands=["start"]))
async def start(message: types.Message):
    if message.chat.type != "private":
        return  # игнорируем группы
    user_data[message.from_user.id] = {"photos": [], "sent": False}
    log(f"👤 Пользователь {message.from_user.id} нажал /start")
    await message.answer(
        "👋 Привет! Загрузите фото чеков по одному.\nКогда закончите — нажмите «Отправить».",
        reply_markup=keyboard_no_send()
    )

# ======================
# Получение фото
# ======================

@dp.message(lambda message: message.content_type == "photo")
async def receive_photo(message: types.Message):
    if message.chat.type != "private":
        return  # игнорируем группы
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"photos": [], "sent": False}

    index = len(user_data[user_id]["photos"]) + 1
    photo = message.photo[-1]

    file = await bot.get_file(photo.file_id)
    path = f"receipt_{user_id}_{index}.jpg"
    await bot.download_file(file.file_path, path)

    user_data[user_id]["photos"].append({"file_path": path, "message_id": None})
    user_data[user_id]["sent"] = False

    log(f"📸 Фото №{index} сохранено: {path}")
    await message.answer(
        f"📸 Фото №{index} добавлено",
        reply_markup=keyboard_with_send()
    )

# ======================
# Отправка фото в группу
# ======================

@dp.message(lambda message: message.text == "📨 Отправить")
async def send_photos_command(message: types.Message):
    if message.chat.type != "private":
        return  # игнорируем группы
    user_id = message.from_user.id
    data = user_data.get(user_id)

    if not data or not data["photos"]:
        log("❌ Нет фото для отправки")
        await message.answer("❌ Нет фото для отправки")
        return

    if data.get("sent"):
        log("⏳ Повторная отправка запрещена")
        await message.answer("⏳ Чеки уже отправлены")
        return

    log(f"🚚 Отправка {len(data['photos'])} фото в группу")

    for photo_record in data["photos"]:
        path = photo_record["file_path"]

        caption_base = (
            f"👤 От: {message.from_user.full_name} (@{message.from_user.username or 'без username'})\n"
            f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        msg = await bot.send_photo(
            chat_id=TELEGRAM_CHAT_ID,
            photo=types.FSInputFile(path),
            caption=f"{caption_base}\n",
            reply_markup=inline_status_buttons(user_id, 0)
        )

        photo_record["message_id"] = msg.message_id

    # удаляем локальные файлы
    for photo_record in data["photos"]:
        p = photo_record["file_path"]
        if os.path.exists(p):
            os.remove(p)
            log(f"🗑 Удалён файл {p}")

    user_data[user_id] = {"photos": [], "sent": True}
    log(f"✅ Отправка завершена для пользователя {user_id}")

    await message.answer(
        "✅ Чеки отправлены!",
        reply_markup=keyboard_no_send()
    )

# ======================
# Сброс (только в личке)
# ======================

@dp.message(lambda message: message.text == "❌ Сбросить")
async def reset(message: types.Message):
    if message.chat.type != "private":
        return  # игнорируем группы
    user_id = message.from_user.id
    user_data[user_id] = {"photos": [], "sent": False}
    log(f"🔄 Пользователь {user_id} сбросил данные")
    await message.answer(
        "🔄 Сброшено. Отправьте фото чеков.",
        reply_markup=keyboard_no_send()
    )

# ======================
# Кнопка "Добавлен ИНН"
# ======================

@dp.callback_query(lambda c: c.data == "inn_added")
async def inn_added_callback(callback: types.CallbackQuery):
    caption = callback.message.caption or ""
    if "🟢 ИНН добавлен" not in caption:
        caption += "\n🟢 ИНН добавлен"
    await bot.edit_message_caption(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        caption=caption,
        reply_markup=None
    )
    log(f"🟢 Пользователь {callback.from_user.id} отметил ИНН на сообщении {callback.message.message_id}")

# ======================
# Кнопки статусов
# ======================

@dp.callback_query(lambda c: c.data.startswith("status:"))
async def status_callback(callback: types.CallbackQuery):
    data = callback.data.split(":")
    new_status = data[1]
    user_id = int(data[2])
    msg_id = int(data[3])

    caption = callback.message.caption or ""
    lines = [line for line in caption.split("\n") if not line.startswith("🟢 Статус:")]
    lines.append(f"🟢 Статус: {new_status}")
    new_caption = "\n".join(lines)

    await bot.edit_message_caption(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        caption=new_caption,
        reply_markup=inline_status_buttons(user_id, msg_id, current_status=new_status)
    )

    await callback.answer(f"Статус изменён на: {new_status}")

    # пересылаем фото автору
    try:
        await bot.forward_message(
            chat_id=user_id,
            from_chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
    except Exception as e:
        log(f"❌ Не удалось переслать фото пользователю {user_id}: {e}")

# ======================
# Запуск бота
# ======================

if __name__ == "__main__":
    log("🚀 Бот запущен (polling)")
    asyncio.run(dp.start_polling(bot))