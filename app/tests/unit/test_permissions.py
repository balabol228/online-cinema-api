import pytest
from fastapi import HTTPException

from app.api.deps import require_role
from app.models.user import User, UserGroupEnum

pytestmark = pytest.mark.asyncio


def _make_user(group: UserGroupEnum) -> User:
    return User(id=1, email="u@example.com", hashed_password="x", is_active=True, group=group)


class TestRequireRole:
    async def test_allows_user_with_matching_role(self) -> None:
        checker = require_role(UserGroupEnum.ADMIN)
        admin = _make_user(UserGroupEnum.ADMIN)
        result = await checker(current_user=admin)
        assert result is admin

    async def test_allows_user_with_one_of_multiple_roles(self) -> None:
        checker = require_role(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR)
        moderator = _make_user(UserGroupEnum.MODERATOR)
        result = await checker(current_user=moderator)
        assert result is moderator

    async def test_rejects_user_without_matching_role(self) -> None:
        checker = require_role(UserGroupEnum.ADMIN)
        regular_user = _make_user(UserGroupEnum.USER)
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=regular_user)
        assert exc_info.value.status_code == 403
