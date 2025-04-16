import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from config import TOKEN
from reminder import schedule_reminder
from database import add_reminder
from database import get_user_reminders
from database import delete_reminder
from reminder import schedule_reminder
from database import get_future_reminders
from datetime import datetime
from database import init_db
from database import mark_done
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_done_reminders
from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

router = Router()




def get_main_keyboard():
    kb = [
        [KeyboardButton(text="📝 Добавить"), KeyboardButton(text="📋 Список")],
        [KeyboardButton(text="✅ История"), KeyboardButton(text="ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)



@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "Привет! Я бот-напоминалка 💡\n\nНажми на кнопку ниже, чтобы начать:",
        reply_markup=get_main_keyboard()
    )

@router.message(lambda msg: msg.text == "ℹ️ Помощь")
async def handle_help(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz")]
    ])

    await message.answer(
        "🔧 Выберите язык для инструкции:",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data.startswith("lang_"))
async def handle_language_selection(callback: CallbackQuery):
        lang = callback.data.split("_")[1]

        if lang == "ru":
            text = (
                "📘 <b>Инструкция по использованию бота:</b>\n\n"
                "📝 /add — Добавить напоминание\n"
                "📋 /list — Список активных задач\n"
                "✅ /history — История завершённых\n"
                "🗑 Удаление — нажми кнопку под задачей\n"
                "⏳ Поддерживается время и дата: <i>в 21:00 16.04</i>\n\n"
                "ℹ️ Можно использовать кнопки внизу!"
            )
        else:
            text = (
                "📘 <b>Ботты пайдалану нұсқаулығы:</b>\n\n"
                "📝 /add — Еске салу қосу\n"
                "📋 /list — Белсенді тапсырмалар тізімі\n"
                "✅ /history — Аяқталғандар тарихы\n"
                "🗑 Жою — Тапсырма астындағы түймені бас\n"
                "⏳ Уақыт пен күнді қолдайды: <i>в 21:00 16.04</i>\n\n"
                "ℹ️ Төмендегі батырмаларды қолдана аласыз!"
            )

        await callback.message.edit_text(text, reply_markup=None)
        await callback.answer()


@router.message(lambda msg: msg.text == "📋 Список")
async def handle_list_button(message: Message):
    await list_command(message)

@router.message(lambda msg: msg.text == "✅ История")
async def handle_history_button(message: Message):
    await history_command(message)

from aiogram.fsm.context import FSMContext
from states import AddReminderState  # если вынес отдельно

@router.message(lambda msg: msg.text == "📝 Добавить")
async def handle_add_button(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Учёба", callback_data="cat_Учёба")],
        [InlineKeyboardButton(text="💼 Работа", callback_data="cat_Работа")],
        [InlineKeyboardButton(text="🏠 Дом", callback_data="cat_Дом")],
        [InlineKeyboardButton(text="💪 Здоровье", callback_data="cat_Здоровье")]
    ])
    await message.answer("🏷 Выбери категорию:", reply_markup=keyboard)
    await state.set_state(AddReminderState.choosing_category)


@router.callback_query(lambda c: c.data.startswith("cat_"))
async def choose_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    await state.update_data(category=category)

    await callback.message.edit_text(f"✅ Категория выбрана: <b>{category}</b>\n\nТеперь напиши задачу:")
    await state.set_state(AddReminderState.waiting_for_text)
    await callback.answer()


@router.message(AddReminderState.waiting_for_text)
async def fsm_add_reminder(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        category = data.get("category")

        args = message.text
        if not args or " в " not in args:
            await message.answer("❌ Формат: Текст в 22:00 или 22:00 17.04")
            return

        text, time_part = args.rsplit(" в ", 1)
        text = text.strip()
        time_part = time_part.strip()

        repeat_type = None
        if "каждый день" in time_part.lower():
            repeat_type = "daily"
            time_part = time_part.lower().replace("каждый день", "").strip()

        elif "по понедельникам" in time_part.lower():
            repeat_type = "monday"
            time_part = time_part.lower().replace("по понедельникам", "").strip()

        now = datetime.now()
        try:
            time_str, date_str = time_part.split(" ")
            remind_datetime = datetime.strptime(f"{date_str} {time_str}", "%d.%m %H:%M")
        except ValueError:
            try:
                remind_time = datetime.strptime(time_part, "%H:%M").time()
                remind_datetime = datetime.combine(now.date(), remind_time)
                if remind_datetime < now:
                    remind_datetime += timedelta(days=1)
            except ValueError:
                await message.answer("❌ Неверный формат времени.\nПример: 22:00 или 22:00 17.04")
                return

        delay = (remind_datetime - now).total_seconds()


        voice_file_id = None
        if message.voice:
            voice_file_id = message.voice.file_id

        reminder_id = await add_reminder(
            message.chat.id,
            text,
            remind_datetime.isoformat(),
            repeat_type,
            category,
            voice_file_id
        )

        await message.answer(
            f"✅ Задача добавлена:\n<b>{text}</b>\n🕒 {remind_datetime.strftime('%H:%M %d.%m')}\n🏷 Категория: {category}"
        )

        asyncio.create_task(schedule_reminder(message.bot, message.chat.id, text, int(delay), reminder_id=reminder_id))
        await state.clear()

    except Exception as e:
        print("Ошибка в FSM добавлении:", e)
        await message.answer("⚠️ Ошибка при добавлении. Убедись в формате.")
        await state.clear()





@router.callback_query(lambda c: c.data.startswith("done_"))
async def inline_done_callback(callback: CallbackQuery):
    reminder_id = int(callback.data.split("_")[1])
    await mark_done(reminder_id)
    await callback.message.edit_text("✅ Помечено как выполненное.")
    await callback.answer("Готово!")







@router.message(Command("list"))
async def list_command(message: Message, command: CommandObject = None):
    category = None
    if command and command.args:
        category = command.args.strip().capitalize()

    reminders = await get_user_reminders(message.chat.id, category)

    if not reminders:
        await message.answer("📭 У тебя пока нет напоминаний.")
        return

    for rid, content, when, cat, voice in reminders:
        time_str = datetime.fromisoformat(when).strftime("%d.%m %H:%M")

        category_info = f"\n🏷 Категория: <i>{cat}</i>" if cat else ""
        voice_info = "\n🎙 <i>Голосовое прикреплено</i>" if voice else ""

        text = f"🔹 <b>{content}</b>\n🕒 <i>{time_str}</i>{category_info}{voice_info}"

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Завершить", callback_data=f"done_{rid}")
        builder.button(text="🗑 Удалить", callback_data=f"delete_{rid}")

        await message.answer(text, reply_markup=builder.as_markup())

@router.message(Command("delete"))
async def delete_command(message: Message, command: CommandObject):
    args = command.args

    if not args:
        await message.answer("❌ Напиши ID задачи, которую хочешь удалить. Пример: /delete 1")
        return

    if not args.strip().isdigit():
        await message.answer("❌ ID должен быть числом. Пример: /delete 2")
        return

    reminder_id = int(args.strip())

    try:
        await delete_reminder(reminder_id)
        await message.answer(f"✅ Напоминание с ID {reminder_id} удалено!")
    except Exception as e:
        print(f"Ошибка при удалении: {e}")
        await message.answer("⚠️ Не удалось удалить напоминание.")


@router.message(Command("add"))
async def add_command(message: Message, command: CommandObject):
    try:
        args = command.args
        if not args or " в " not in args:
            await message.answer("❌ Формат: /add Текст в 22:00 или 22:00 17.04")
            return

        # --- Парсим текст задачи и часть с временем
        text, time_part = args.rsplit(" в ", 1)
        text = text.strip()
        time_part = time_part.strip()

        # --- Выделим повторы в отдельной переменной и удалим их из time_part
        repeat_type = None

        if "каждый день" in time_part.lower():
            repeat_type = "daily"
            time_part = time_part.lower().replace("каждый день", "").strip()

        elif "по понедельникам" in time_part.lower():
            repeat_type = "monday"
            time_part = time_part.lower().replace("по понедельникам", "").strip()

        # --- Определяем дату и время
        now = datetime.now()

        try:
            # Попытка разобрать как время + дата
            time_str, date_str = time_part.split(" ")
            remind_datetime = datetime.strptime(f"{date_str} {time_str}", "%d.%m %H:%M")
        except ValueError:
            # Иначе — просто время на сегодня/завтра
            try:
                remind_time = datetime.strptime(time_part, "%H:%M").time()
                remind_datetime = datetime.combine(now.date(), remind_time)
                if remind_datetime < now:
                    remind_datetime += timedelta(days=1)
            except ValueError:
                await message.answer("❌ Неверный формат времени.\nПример: 22:00 или 22:00 17.04")
                return

        delay = (remind_datetime - now).total_seconds()

        # Ищем категорию: "категория:Учёба"
        category = None
        if "категория:" in text.lower():
            parts = text.rsplit("категория:", 1)
            text = parts[0].strip()
            category = parts[1].strip().capitalize()


        # Добавляем в БД
        reminder_id = await add_reminder(message.chat.id, text, remind_datetime.isoformat(), repeat_type, category)


        await message.answer(f"✅ Напоминание установлено: <b>{text}</b>\n🕒 {remind_datetime.strftime('%H:%M %d.%m')}")

        # Запускаем таймер
        asyncio.create_task(schedule_reminder(message.bot, message.chat.id, text, int(delay), reminder_id=reminder_id))

    except Exception as e:
        print("Ошибка в add_command:", e)
        await message.answer("⚠️ Ошибка при добавлении. Убедись в формате команды.")



async def main():
    await init_db()  # ← инициализируем БД

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    # Загружаем задачи из базы
    reminders = await get_future_reminders()
    for reminder in reminders:
        reminder_id, user_id, text, remind_at = reminder
        remind_time = datetime.fromisoformat(remind_at)
        delay = (remind_time - datetime.now()).total_seconds()

        if delay > 0:
            print(f"⏳ Запущено напоминание ID {reminder_id} через {int(delay)} сек.")
            # Даже если delay < 0, запускаем — чтобы обработать просроченные
            asyncio.create_task(schedule_reminder(bot, user_id, text, max(int(delay), 0), reminder_id=reminder_id))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)



@router.message(Command("history"))
async def history_command(message: Message):
    reminders = await get_done_reminders(message.chat.id)

    if not reminders:
        await message.answer("📭 У тебя пока нет завершённых задач.")
        return

    text = "📖 Завершённые напоминания:\n\n"
    for content, when in reminders:
        time_str = datetime.fromisoformat(when).strftime("%d.%m %H:%M")
        text += f"✅ <b>{content}</b>\n🕒 <i>{time_str}</i>\n\n"

    await message.answer(text)

@router.callback_query(lambda c: c.data.startswith("delete_"))
async def inline_delete_callback(callback: CallbackQuery):
    reminder_id = int(callback.data.split("_")[1])

    await delete_reminder(reminder_id)
    await callback.message.edit_text("❌ Напоминание удалено.")
    await callback.answer("Удалено!")


if __name__ == "__main__":
    asyncio.run(main())


