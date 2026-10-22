import csv
import io
from src.db.models import Booking


def generate_bookings_csv(bookings: list[Booking]) -> bytes:
    """Формирует CSV-отчет по всем записям в памяти (UTF-8 with BOM для Excel)."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID записи",
        "Дата и время визита (UTC)",
        "Клиент",
        "Username",
        "Телефон",
        "Услуга",
        "Стоимость (₽)",
        "Статус",
        "Создано (UTC)",
    ])

    for b in bookings:
        writer.writerow([
            b.id,
            b.slot.start_time.strftime("%Y-%m-%d %H:%M"),
            b.user.full_name,
            f"@{b.user.username}" if b.user.username else "—",
            b.user.phone or "Не указан",
            b.service.title,
            b.service.price_rub,
            b.status,
            b.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    return output.getvalue().encode("utf-8-sig")
