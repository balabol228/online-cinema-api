from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.schemas.interaction import (
    CommentCreateRequest,
    CommentResponse,
    LikeResponse,
    RatingRequest,
    RatingResponse,
)
from app.services import interaction_service

router = APIRouter(prefix="/movies/{movie_id}", tags=["Likes, Ratings & Comments"])


@router.post(
    "/like",
    response_model=LikeResponse,
    summary="Лайкнути / зняти лайк із фільму",
    description=(
        "Перемикає лайк поточного користувача для фільму: якщо лайку ще не було — додає, "
        "якщо вже є — знімає. Повертає новий стан (`liked`) і загальну кількість лайків фільму."
    ),
)
async def like_movie(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LikeResponse:
    liked, count = await interaction_service.toggle_like(db, current_user, movie_id)
    return LikeResponse(liked=liked, likes_count=count)


@router.post(
    "/rating",
    response_model=RatingResponse,
    summary="Оцінити фільм (1-10)",
    description=(
        "Ставить або оновлює рейтинг поточного користувача для фільму. `score` — ціле число від 1 до 10.\n\n"
        "Повторний виклик перезаписує попередню оцінку користувача (не створює дублікат)."
    ),
)
async def rate_movie(
    movie_id: int,
    payload: RatingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RatingResponse:
    await interaction_service.rate_movie(db, current_user, movie_id, payload.score)
    avg, count, user_score = await interaction_service.get_rating_summary(db, movie_id, current_user)
    return RatingResponse(average_rating=avg, ratings_count=count, user_score=user_score)


@router.get(
    "/rating",
    response_model=RatingResponse,
    summary="Переглянути рейтинг фільму",
    description="Повертає середній рейтинг фільму, кількість оцінок, і оцінку поточного користувача (якщо ставив).",
)
async def get_rating(
    movie_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> RatingResponse:
    avg, count, user_score = await interaction_service.get_rating_summary(db, movie_id, current_user)
    return RatingResponse(average_rating=avg, ratings_count=count, user_score=user_score)


@router.post(
    "/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Додати коментар (або відповідь)",
    description=(
        "Додає коментар до фільму. Якщо передано `parent_id` — створює вкладену відповідь "
        "на інший коментар (nested comments). Повертає 404, якщо `parent_id` не існує."
    ),
)
async def create_comment(
    movie_id: int,
    payload: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    comment = await interaction_service.add_comment(
        db, current_user, movie_id, payload.text, payload.parent_id
    )
    return CommentResponse.model_validate(comment)


@router.get(
    "/comments",
    response_model=list[CommentResponse],
    summary="Переглянути коментарі (публічний)",
    description="Повертає коментарі верхнього рівня до фільму разом із вкладеними відповідями (`replies`).",
)
async def get_comments(movie_id: int, db: AsyncSession = Depends(get_db)) -> list[CommentResponse]:
    comments = await interaction_service.list_comments(db, movie_id)
    return [CommentResponse.model_validate(c) for c in comments]
