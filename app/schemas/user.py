from pydantic import BaseModel, EmailStr

from app.models.user import UserGroupEnum


class CurrentUserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_verified: bool
    group: UserGroupEnum

    model_config = {"from_attributes": True}
