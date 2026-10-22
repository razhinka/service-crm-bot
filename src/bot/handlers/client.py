import re
from datetime import datetime, timezone
from aiogram import Bot, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User
from src.db.repositories import BookingRepository, ServiceRepository, SlotRepository, UserRepository
from src.bot.keyboards.inline import (
    confirm_booking_kb,
    main_menu_kb,
    phone_request_kb,
    services_kb,
    slots_kb,
    user_bookings_kb,
)
from src.bot.states.forms import BookingSG
from src.services.notification_service import notify_admins_new_booking, schedule_booking_reminder

client_router = Router(name="client_router")
PHONE_REGEX = re.compile(r"^\+?[78][\d\-\s\(\)]{9,15}$")


@client_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User) -> None:
    await state.clear()
    await message.answer(
        text=(
            f"👋 Привет, <b>{user.full_name}</b>!\n\n"
            f"Добро пожаловать в систему онлайн-записи. "
            f"Выберите действие в меню ниже:"
        ),
        reply_markup=main_menu_kb(user.role),
    )


@client_router.callback_query(F.data == "menu:home")
async def cb_home(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await callback.message.edit_text(
        text="🏠 <b>Главное меню</b>\nВыберите нужный раздел:",
        reply_markup=main_menu_kb(user.role),
    )
    await callback.answer()


@client_router.callback_query(F.data == "menu:book")
async def cb_choose_service(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    srv_repo = ServiceRepository(session)
    services = await srv_repo.get_active_services()

    if not services:
        await callback.answer("Нет доступных услуг для записи.", show_alert=True)
        return

    await state.set_state(BookingSG.choosing_service)
    await callback.message.edit_text(
        text="🛠 <b>Шаг 1 из 4: Выберите услугу</b>\nОзнакомьтесь с прайсом и нажмите на нужную позицию:",
        reply_markup=services_kb(services),
    )
    await callback.answer()


@client_router.callback_query(BookingSG.choosing_service, F.data.startswith("srv:"))
async def cb_service_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    service_id = int(callback.data.split(":")[1])
    srv_repo = ServiceRepository(session)
    service = await srv_repo.get_by_id(service_id)

    if service is None:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return

    slot_repo = SlotRepository(session)
    slots = await slot_repo.get_available_slots(datetime.now(timezone.utc))
    if not slots:
        await callback.answer("К сожалению, свободных окон сейчас нет.", show_alert=True)
        return

    await state.update_data(
        service_id=service.id,
        service_title=service.title,
        service_price=service.price_rub,
    )
    await state.set_state(BookingSG.choosing_slot)

    await callback.message.edit_text(
        text=(
            f"📌 Выбрана услуга: <b>{service.title}</b>\n"
            f"ℹ️ {service.description}\n"
            f"💳 Стоимость: <b>{service.price_rub} ₽</b>\n\n"
            f"🕒 <b>Шаг 2 из 4: Выберите удобное время визита:</b>"
        ),
        reply_markup=slots_kb(slots),
    )
    await callback.answer()


@client_router.callback_query(BookingSG.choosing_slot, F.data.startswith("slot:"))
async def cb_slot_selected(callback: CallbackQuery, state: FSMContext) -> None:
    slot_id = int(callback.data.split(":")[1])
    await state.update_data(slot_id=slot_id)
    await state.set_state(BookingSG.entering_phone)

    await callback.message.delete()
    await callback.message.answer(
        text=(
            "📞 <b>Шаг 3 из 4: Контактные данные</b>\n\n"
            "Нажмите кнопку <b>«Отправить мой контакт»</b> ниже "
            "или введите номер телефона вручную в формате <code>+79991234567</code>:"
        ),
        reply_markup=phone_request_kb(),
    )
    await callback.answer()


@client_router.message(BookingSG.entering_phone)
async def msg_phone_received(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    if message.contact and message.contact.phone_number:
        phone = message.contact.phone_number
    elif message.text and PHONE_REGEX.match(message.text.strip()):
        phone = message.text.strip()
    else:
        await message.answer(
            "⚠️ Некорректный формат номера. Введите телефон в формате <code>+79991234567</code> "
            "или нажмите кнопку отправки контакта ниже."
        )
        return

    user_repo = UserRepository(session)
    await user_repo.update_phone(user.id, phone)

    data = await state.get_data()
    await state.set_state(BookingSG.confirming)

    await message.answer(
        text="✅ Номер телефона сохранен.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        text=(
            f"🧾 <b>Шаг 4 из 4: Подтверждение и демо-оплата</b>\n\n"
            f"🛠 Услуга: <b>{data['service_title']}</b>\n"
            f"💰 К оплате: <b>{data['service_price']} ₽</b>\n"
            f"📞 Ваш телефон: <code>{phone}</code>\n\n"
            f"Нажмите кнопку ниже для подтверждения бронирования:"
        ),
        reply_markup=confirm_booking_kb(),
    )


@client_router.callback_query(BookingSG.confirming, F.data == "book:confirm")
async def cb_confirm_booking(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    booking_repo = BookingRepository(session)

    booking = await booking_repo.book_slot_atomic(
        user_id=user.id,
        service_id=data["service_id"],
        slot_id=data["slot_id"],
    )
    await state.clear()

    if booking is None:
        await callback.message.edit_text(
            text="⚠️ К сожалению, этот слот только что занял другой клиент. Пожалуйста, выберите другое время.",
            reply_markup=main_menu_kb(user.role),
        )
        await callback.answer()
        return

    schedule_booking_reminder(bot, booking)
    await notify_admins_new_booking(bot, booking)

    time_str = booking.slot.start_time.strftime("%d.%m.%Y в %H:%M UTC")
    await callback.message.edit_text(
        text=(
            f"🎉 <b>Запись #{booking.id} успешно подтверждена!</b>\n\n"
            f"📌 Услуга: <b>{booking.service.title}</b>\n"
            f"🗓 Дата и время: <b>{time_str}</b>\n\n"
            f"Мы автоматически напомним вам о визите за 2 часа до начала."
        ),
        reply_markup=main_menu_kb(user.role),
    )
    await callback.answer()


@client_router.callback_query(F.data == "menu:my_bookings")
@client_router.message(Command("my_bookings"))
async def show_user_bookings(
    event: CallbackQuery | Message,
    session: AsyncSession,
    user: User,
) -> None:
    booking_repo = BookingRepository(session)
    bookings = await booking_repo.get_user_active_bookings(user.id)

    if not bookings:
        text = "🗂 У вас пока нет активных записей."
    else:
        lines = ["🗂 <b>Ваши активные записи:</b>\n"]
        for b in bookings:
            dt = b.slot.start_time.strftime("%d.%m.%Y %H:%M UTC")
            lines.append(f"• <b>#{b.id}</b> — {b.service.title} ({dt})")
        lines.append("\nНажмите на запись ниже, если хотите её отменить:")
        text = "\n".join(lines)

    kb = user_bookings_kb(bookings)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text=text, reply_markup=kb)


@client_router.callback_query(F.data.startswith("cancel_bk:"))
async def cb_cancel_booking(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    booking_id = int(callback.data.split(":")[1])
    booking_repo = BookingRepository(session)
    cancelled = await booking_repo.cancel_booking(booking_id=booking_id, user_id=user.id)

    if cancelled:
        await callback.answer("Запись отменена, слот снова свободен!", show_alert=True)
    else:
        await callback.answer("Не удалось отменить запись.", show_alert=True)

    await show_user_bookings(callback, session, user)
