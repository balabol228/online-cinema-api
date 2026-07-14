import pytest
from pydantic import ValidationError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import UserRegisterRequest


class TestPasswordHashing:
    def test_hash_password_returns_different_value(self) -> None:
        hashed = hash_password("StrongPass1")
        assert hashed != "StrongPass1"

    def test_verify_password_success(self) -> None:
        hashed = hash_password("StrongPass1")
        assert verify_password("StrongPass1", hashed) is True

    def test_verify_password_failure(self) -> None:
        hashed = hash_password("StrongPass1")
        assert verify_password("WrongPass1", hashed) is False


class TestJWTTokens:
    def test_access_token_decodes_with_correct_type(self) -> None:
        token = create_access_token(user_id=42)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_refresh_token_decodes_with_correct_type(self) -> None:
        token = create_refresh_token(user_id=42)
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_decode_invalid_token_returns_none(self) -> None:
        assert decode_token("not-a-real-token") is None


class TestPasswordValidation:
    @pytest.mark.parametrize(
        "password",
        ["short1A", "alllowercase1", "NODIGITSATALL"],
    )
    def test_weak_passwords_are_rejected(self, password: str) -> None:
        with pytest.raises(ValidationError):
            UserRegisterRequest(email="user@example.com", password=password)

    def test_strong_password_is_accepted(self) -> None:
        req = UserRegisterRequest(email="user@example.com", password="StrongPass1")
        assert req.password == "StrongPass1"
