from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.inline import admin_panel_kb
from src.bot.states.forms import AdminSG
from src.db.models import User, UserRole
from src.db.repositories import BookingRepository, SlotRepository, UserRepository
from src.services.csv_service import generate_bookings_csv

admin_router = Router(name="admin_router")


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, user: User) -> None:
    if not _is_admin(user):
        await message.answer("⛔ Доступ запрещен. Требуются права администратора.")
        return
    await message.answer(
        text="⚙️ <b>Панель управления CRM</b>\nВыберите действие:",
        reply_markup=admin_panel_kb(),
    )


@admin_router.callback_query(F.data == "adm:panel")
async def cb_admin_panel(callback: CallbackQuery, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("⛔ Нет прав доступа.", show_alert=True)
        return
    await callback.message.edit_text(
        text="⚙️ <b>Панель управления CRM</b>\nВыберите действие:",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()


async def cb_admin_stats(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    if not _is_admin(user):
        await callback.answer("⛔ Нет прав доступа.", show_alert=True)
        return

    booking_repo = BookingRepository(session)
    stats = await booking_repo.get_analytics_summary()

    await callback.message.edit_text(
        text=(
            f"📊 <b>Сводная аналитика CRM</b>\n\n"
            f"👥 Всего клиентов в базе: <b>{stats['total_users']}</b>\n"
            f"✅ Подтвержденных записей: <b>{stats['active_bookings']}</b>\n"
            f"💰 Суммарная выручка: <b>{stats['total_revenue']} ₽</b>"
        ),
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "adm:gen_slots")
async def cb_admin_gen_slots(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    if not _is_admin(user):
        await callback.answer("⛔ Нет прав доступа.", show_alert=True)
        return

    slot_repo = SlotRepository(session)
    now = datetime.now(timezone.utc)
    total_created = 0
    for day_offset in range(1, 4):
        target_day = now + timedelta(days=day_offset)
        total_created += await slot_repo.generate_slots_for_date(
            target_day, hours=[10, 12, 15, 18]
        )

    await callback.answer(
        f"✅ Сгенерировано новых слотов на ближайшие 3 дня: {total_created} шт.",
        show_alert=True,
    )


@admin_router.callback_query(F.data == "adm:export_csv")
async def cb_admin_export_csv(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    if not _is_admin(user):
        await callback.answer("⛔ Нет прав доступа.", show_alert=True)
        return

    booking_repo = BookingRepository(session)
    bookings = await booking_repo.get_all_bookings_detailed()
    csv_bytes = generate_bookings_csv(bookings)

    filename = f"crm_bookings_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
    file = BufferedInputFile(csv_bytes, filename=filename)

    await callback.message.answer_document(
        document=file,
        caption=f"📥 Выгрузка базы бронирований ({len(bookings)} записей).",
    )
    await callback.answer()


@admin_router.callback_query(F.data == "adm:broadcast")
async def cb_admin_broadcast_start(
    callback: CallbackQuery, state: FSMContext, user: User
) -> None:
async def cb_admin_broadcast_start(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("⛔ Нет прав доступа.", show_alert=True)
        return

    await state.set_state(AdminSG.entering_broadcast_text)
    await callback.message.edit_text(
        text="📢 Введите текст сообщения для рассылки всем пользователям бота (или отправьте /start для отмены):"
    )
    await callback.answer()


@admin_router.message(AdminSG.entering_broadcast_text)
async def msg_admin_broadcast_send(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    if not _is_admin(user):
        return

    await state.clear()
    user_repo = UserRepository(session)
    tg_ids = await user_repo.get_all_client_tg_ids()

    sent_count = 0
    for tg_id in tg_ids:
        try:
            await bot.send_message(chat_id=tg_id, text=message.html_text)
            sent_count += 1
        except Exception:
            continue

    await message.answer(
        text=f"✅ Рассылка завершена! Доставлено сообщений: <b>{sent_count} из {len(tg_ids)}</b>.",
        reply_markup=admin_panel_kb(),
    )
