from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models import Booking, Service, TimeSlot, UserRole


def main_menu_kb(role: UserRole) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться на услугу", callback_data="menu:book"))
    builder.row(InlineKeyboardButton(text="🗂 Мои активные записи", callback_data="menu:my_bookings"))
    if role == UserRole.ADMIN:
        builder.row(InlineKeyboardButton(text="⚙️ Панель администратора", callback_data="adm:panel"))
    return builder.as_markup()


def services_kb(services: list[Service]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for srv in services:
        builder.row(
            InlineKeyboardButton(
                text=f"{srv.title} — {srv.price_rub} ₽",
                callback_data=f"srv:{srv.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu:home"))
    return builder.as_markup()


def slots_kb(slots: list[TimeSlot]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        label = slot.start_time.strftime("%d.%m (%H:%M UTC)")
        builder.add(InlineKeyboardButton(text=label, callback_data=f"slot:{slot.id}"))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 Назад к услугам", callback_data="menu:book"))
    return builder.as_markup()


def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить мой контакт", request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_booking_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Оплатить и подтвердить", callback_data="book:confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="menu:home"),
    )
    return builder.as_markup()


def user_bookings_kb(bookings: list[Booking]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in bookings:
        date_str = b.slot.start_time.strftime("%d.%m %H:%M")
        builder.row(
            InlineKeyboardButton(
                text=f"❌ Отменить: {b.service.title} ({date_str})",
                callback_data=f"cancel_bk:{b.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu:home"))
    return builder.as_markup()


def admin_panel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Аналитика и выручка", callback_data="adm:stats"))
    builder.row(InlineKeyboardButton(text="➕ Сгенерировать слоты (+3 дня)", callback_data="adm:gen_slots"))
    builder.row(InlineKeyboardButton(text="📥 Выгрузить базу в CSV (Excel)", callback_data="adm:export_csv"))
    builder.row(InlineKeyboardButton(text="📢 Рассылка клиентам", callback_data="adm:broadcast"))
    builder.row(InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu:home"))
    return builder.as_markup()
