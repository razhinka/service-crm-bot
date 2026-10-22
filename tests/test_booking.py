from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import TimeSlot
from src.db.repositories import BookingRepository


@pytest.mark.asyncio
async def test_book_slot_atomic_already_booked():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)

    # Имитируем, что запрос SELECT ... FOR UPDATE вернул уже занятый слот
    mock_slot = MagicMock(spec=TimeSlot)
    mock_slot.is_booked = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_slot
    mock_session.execute.return_value = mock_result

    repo = BookingRepository(mock_session)

    # Act
    booking = await repo.book_slot_atomic(user_id=1, service_id=1, slot_id=1)

    # Assert
    assert booking is None, "Бронирование должно быть отклонено, если слот уже занят"
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()
