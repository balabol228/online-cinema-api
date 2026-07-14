import re

from pydantic import BaseModel, EmailStr, field_validator


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """
        Кастомна валідація пароля:
        мінімум 8 символів, хоча б одна цифра і одна літера верхнього регістру.
        """
        if len(value) < 8:
            raise ValueError("Пароль має містити щонайменше 8 символів")
        if not re.search(r"\d", value):
            raise ValueError("Пароль має містити щонайменше одну цифру")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Пароль має містити щонайменше одну літеру верхнього регістру")
        return value


class UserRegisterResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    model_config = {"from_attributes": True}


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
