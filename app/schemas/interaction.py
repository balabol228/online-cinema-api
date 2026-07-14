from pydantic import BaseModel, Field


class LikeResponse(BaseModel):
    liked: bool
    likes_count: int


class RatingRequest(BaseModel):
    score: int = Field(ge=1, le=10)


class RatingResponse(BaseModel):
    average_rating: float | None
    ratings_count: int
    user_score: int | None


class CommentCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = None


class CommentAuthorResponse(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


class CommentResponse(BaseModel):
    id: int
    text: str
    user: CommentAuthorResponse
    parent_id: int | None
    replies: list["CommentResponse"] = []

    model_config = {"from_attributes": True}


CommentResponse.model_rebuild()
