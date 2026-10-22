# Telegram Mini-CRM & Booking System

Высокопроизводительный Telegram-бот для онлайн-записи клиентов, управления расписанием и сбора аналитики. Решение спроектировано для малого бизнеса (сфера услуг, консультации, аренда) и поддерживает полный цикл клиентской воронки.

## 🚀 Ключевые возможности

*   **Клиентский поток (FSM):** Интерактивный выбор услуг, инлайн-календарь свободных слотов, валидация контактов.
*   **Защита расписания:** Атомарное бронирование с пессимистическими блокировками (`SELECT ... FOR UPDATE`) исключает двойную запись на одно время.
*   **Автоматизация:** Интегрированный планировщик (`APScheduler`) отправляет напоминания за 2 часа до визита.
*   **Панель администратора (RBAC):** Управление слотами, массовые рассылки, агрегатная статистика и экспорт базы в CSV (Excel) «в один клик».

## 🛠 Технологический стек

*   **Язык и фреймворк:** Python 3.12, aiogram 3.x
*   **База данных:** PostgreSQL 16, SQLAlchemy 2.0 (asyncpg), Alembic (миграции)
*   **Кэш и состояния:** Redis 7
*   **Инфраструктура:** Docker, Docker Compose, Pydantic-settings
*   **Тестирование:** pytest, pytest-asyncio

## 🗄 Архитектура базы данных

```mermaid
erDiagram
    USERS ||--o{ BOOKINGS : makes
    SERVICES ||--o{ BOOKINGS : includes
    TIME_SLOTS ||--o| BOOKINGS : reserves

    USERS {
        int id PK
        bigint tg_id
        string full_name
        string phone
        string role "client/admin"
    }
    SERVICES {
        int id PK
        string title
        int price_rub
        int duration_minutes
    }
    TIME_SLOTS {
        int id PK
        datetime start_time
        boolean is_booked
    }
    BOOKINGS {
        int id PK
        int user_id FK
        int service_id FK
        int slot_id FK
        string status
    }
