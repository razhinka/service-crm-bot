import logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.db.models import Booking

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")


async def _send_client_reminder(bot: Bot, tg_id: int, service_title: str, start_time_str: str) -> None:
    try:
        await bot.send_message(
            chat_id=tg_id,
            text=(
                f"⏰ <b>Напоминание о записи!</b>\n\n"
                f"Через 2 часа у вас запланирован визит:\n"
                f"📌 Услуга: <b>{service_title}</b>\n"
                f"🕒 Время: <b>{start_time_str} UTC</b>\n\n"
                f"Ждем вас!"
            ),
        )
    except Exception as exc:
        logger.warning("Не удалось отправить напоминание пользователю %s: %s", tg_id, exc)


def schedule_booking_reminder(bot: Bot, booking: Booking) -> None:
    """Планирует напоминание клиенту за 2 часа до начала визита."""
    remind_at = booking.slot.start_time - timedelta(hours=2)
    now = datetime.now(timezone.utc)

    if remind_at > now:
        time_str = booking.slot.start_time.strftime("%d.%m.%Y %H:%M")
        scheduler.add_job(
            _send_client_reminder,
            trigger="date",
            run_date=remind_at,
            kwargs={
                "bot": bot,
                "tg_id": booking.user.tg_id,
                "service_title": booking.service.title,
                "start_time_str": time_str,
            },
            id=f"reminder_booking_{booking.id}",
            replace_existing=True,
        )


async def notify_admins_new_booking(bot: Bot, booking: Booking) -> None:
    """Отправляет мгновенное уведомление администраторам о новой заявке."""
    time_str = booking.slot.start_time.strftime("%d.%m.%Y %H:%M")
    text = (
        f"🔔 <b>Новая запись #{booking.id}</b>\n\n"
        f"👤 Клиент: {booking.user.full_name} (@{booking.user.username or 'нет'})\n"
        f"📞 Телефон: <code>{booking.user.phone}</code>\n"
        f"🛠 Услуга: <b>{booking.service.title}</b> ({booking.service.price_rub} ₽)\n"
        f"🗓 Время слота: <b>{time_str} UTC</b>"
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as exc:
            logger.warning("Не удалось уведомить админа %s: %s", admin_id, exc)
