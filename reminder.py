import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from database import get_reminder_by_id, add_reminder

async def schedule_reminder(bot: Bot, user_id: int, text: str, delay: int, reminder_id: int = None):
    await asyncio.sleep(delay)

    reminder = await get_reminder_by_id(reminder_id)
    if not reminder:
        print(f"❌ Напоминание ID {reminder_id} удалено")
        return
    if reminder["done"]:
        print(f"⏹ Напоминание ID {reminder_id} завершено")
        return
    if datetime.now() > datetime.fromisoformat(reminder["remind_at"]):
        await bot.send_message(user_id, f"⚠️ Ты пропустил задачу: <b>{text}</b>")
        return

    # ✅ Отправка голосового, если есть
    if reminder.get("voice_file_id"):
        await bot.send_voice(user_id, reminder["voice_file_id"], caption=f"🔔 Голосовое напоминание: {text}")
    else:
        await bot.send_message(user_id, f"🔔 Напоминание: {text}")

    # 🔁 Повтор
    repeat = reminder.get("repeat_type")
    if repeat:
        remind_time = datetime.fromisoformat(reminder["remind_at"])
        next_time = None

        if repeat == "daily":
            next_time = remind_time + timedelta(days=1)

        elif repeat == "monday":
            next_time = remind_time
            while next_time.weekday() != 0:
                next_time += timedelta(days=1)

        if next_time:
            new_id = await add_reminder(
                user_id,
                text,
                next_time.isoformat(),
                repeat,
                category=None,  # можно сохранить, если хочешь
                voice_file_id=reminder.get("voice_file_id")
            )
            new_delay = (next_time - datetime.now()).total_seconds()
            asyncio.create_task(schedule_reminder(bot, user_id, text, int(new_delay), new_id))
